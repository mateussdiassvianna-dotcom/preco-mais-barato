from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from datetime import datetime
import traceback

from extensions import db
from models import Comerciante

# -----------------------------
# Blueprint Admin
# -----------------------------
admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')

# ⚙️ Admin padrão (apenas para ambiente de testes)
ADMIN_USER = {
    "email": "admin@teste.com",
    "senha": "123456"  # ⚠️ Use senha criptografada em produção!
}

# 🔒 Verifica login
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logado"):
            flash("Você precisa estar logado para acessar essa página.", "danger")
            return redirect(url_for("admin.admin_login"))
        return f(*args, **kwargs)
    return decorated_function

# ---------------- LOGIN ----------------
@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        if email == ADMIN_USER['email'] and senha == ADMIN_USER['senha']:
            session['admin_logged_in'] = True
            session['admin_email'] = email
            flash("✅ Login realizado com sucesso!", "success")
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash("❌ Email ou senha incorretos.", "danger")
    return render_template('admin_login.html')

# ---------------- LOGOUT ----------------
@admin_bp.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_email', None)
    flash("🚪 Logout realizado com sucesso.", "info")
    return redirect(url_for('admin.admin_login'))

# ---------------- DECORATOR LOGIN ----------------
def login_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("⚠️ Faça login primeiro.", "warning")
            return redirect(url_for('admin.admin_login'))
        return func(*args, **kwargs)
    return wrapper

# ---------------- DASHBOARD ----------------
@admin_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    supabase = current_app.config["supabase"]
    try:
        total_comerciantes = len(supabase.table("comerciantes").select("id").execute().data or [])
        aprovados = len(supabase.table("comerciantes").select("id").eq("status", "ativo").execute().data or [])
        bloqueados = len(supabase.table("comerciantes").select("id").eq("status", "bloqueado").execute().data or [])
        pendentes = len(supabase.table("comerciantes_pendentes").select("id").execute().data or [])
        total_produtos = len(supabase.table("produtos").select("id").execute().data or [])
        total_pesquisas = len(supabase.table("pesquisas").select("id").execute().data or [])
        total_acessos = len(supabase.table("historico_comerciantes").select("id").execute().data or [])

        pendentes_list = supabase.table("comerciantes_pendentes").select("*").execute().data or []

        stats = {
            'total_comerciantes': total_comerciantes,
            'aprovados': aprovados,
            'bloqueados': bloqueados,
            'pendentes': pendentes,
            'total_produtos': total_produtos,
            'total_pesquisas': total_pesquisas,
            'total_acessos': total_acessos
        }

        return render_template('admin_dashboard.html', stats=stats, pendentes=pendentes_list)
    except Exception as e:
        print("❌ ERRO AO CARREGAR DASHBOARD:", traceback.format_exc())
        flash(f"Erro ao carregar o painel: {e}", "danger")
        return redirect(url_for('admin.admin_login'))

# ---------------- LISTAR COMERCIANTES ----------------
@admin_bp.route('/admin/comerciantes')
@login_required
def admin_comerciantes():
    supabase = current_app.config["supabase"]
    try:
        comerciantes = supabase.table("comerciantes").select("*").order("nome", desc=False).execute().data or []
        for c in comerciantes:
            cid = c.get("id")
            produtos = supabase.table("produtos").select("*").eq("comerciante_id", cid).order("nome", desc=False).execute().data or []
            for p in produtos:
                if not p.get("imagem"):
                    p["imagem"] = "/static/img/sem-produto.jpg"
            c["produtos"] = produtos
            c["quantidade_produtos"] = len(produtos)

            historico = supabase.table("historico_comerciantes").select("*").eq("comerciante_id", cid).order("data_hora", desc=True).limit(20).execute().data or []
            for h in historico:
                if h.get("data_hora"):
                    try:
                        dt = datetime.fromisoformat(h["data_hora"].replace("Z", "+00:00"))
                        h["data_hora"] = dt.strftime("%d/%m/%Y %H:%M")
                    except:
                        pass
            c["historico"] = historico
        return render_template('admin_comerciantes.html', comerciantes=comerciantes)
    except Exception as e:
        print("❌ ERRO AO LISTAR COMERCIANTES:", traceback.format_exc())
        flash(f"Erro ao carregar comerciantes: {e}", "danger")
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route("/bloquear/<id>")
@login_required
def admin_bloquear_comerciante(id):
    supabase = current_app.config["supabase"]
    try:
        # Verifica se o comerciante existe
        comerciante = supabase.table("comerciantes").select("*").eq("id", id).execute().data
        if not comerciante:
            flash("❌ Comerciante não encontrado.", "danger")
            return redirect(url_for("admin.admin_comerciantes"))

        # Atualiza o status para bloqueado
        supabase.table("comerciantes").update({"status": "bloqueado"}).eq("id", id).execute()
        flash("🚫 Comerciante bloqueado com sucesso!", "success")

    except Exception as e:
        print("❌ ERRO AO BLOQUEAR:", e)
        flash(f"Erro ao bloquear comerciante: {e}", "danger")

    return redirect(url_for("admin.admin_comerciantes"))


@admin_bp.route("/desbloquear/<id>")
@login_required
def admin_desbloquear_comerciante(id):
    supabase = current_app.config["supabase"]
    try:
        # Verifica se o comerciante existe
        comerciante = supabase.table("comerciantes").select("*").eq("id", id).execute().data
        if not comerciante:
            flash("❌ Comerciante não encontrado.", "danger")
            return redirect(url_for("admin.admin_comerciantes"))

        # Atualiza o status para ativo
        supabase.table("comerciantes").update({"status": "ativo"}).eq("id", id).execute()
        flash("✅ Comerciante desbloqueado com sucesso!", "success")

    except Exception as e:
        print("❌ ERRO AO DESBLOQUEAR:", e)
        flash(f"Erro ao desbloquear comerciante: {e}", "danger")

    return redirect(url_for("admin.admin_comerciantes"))



# ---------------- APAGAR COMERCIANTE ----------------
@admin_bp.route('/admin/apagar/<id>')
@login_required
def admin_apagar_comerciante(id):
    supabase = current_app.config["supabase"]
    try:
        supabase.table("produtos").delete().eq("comerciante_id", id).execute()
        supabase.table("historico_comerciantes").delete().eq("comerciante_id", id).execute()
        supabase.table("comerciantes").delete().eq("id", id).execute()
        flash("🗑️ Comerciante e todos os dados relacionados foram apagados!", "danger")
    except Exception as e:
        print("❌ ERRO AO APAGAR:", traceback.format_exc())
        flash(f"Erro ao apagar comerciante: {e}", "danger")
    return redirect(url_for('admin.admin_comerciantes'))

# ---------------- LISTA DE ACESSOS ----------------
@admin_bp.route('/admin/acessos')
@login_required
def admin_acessos():
    supabase = current_app.config["supabase"]
    try:
        acessos = supabase.table("historico_comerciantes").select("*").order("data_hora", desc=True).execute().data or []
        for a in acessos:
            comerciante = supabase.table("comerciantes").select("*").eq("id", a['comerciante_id']).execute().data
            if comerciante:
                a['nome'] = comerciante[0]['nome']
                a['cidade'] = comerciante[0].get('cidade', '')
                a['estado'] = comerciante[0].get('estado', '')
        return render_template('admin_acessos.html', acessos=acessos)
    except Exception as e:
        print("❌ ERRO AO CARREGAR ACESSOS:", traceback.format_exc())
        flash(f"Erro ao carregar acessos: {e}", "danger")
        return redirect(url_for('admin.admin_dashboard'))

# ---------------- LISTA DE PRODUTOS ----------------
@admin_bp.route('/admin/produtos')
@login_required
def admin_produtos():
    supabase = current_app.config["supabase"]
    try:
        produtos = supabase.table("produtos").select("*").order("nome", desc=False).execute().data or []
        produtos_data = []
        for p in produtos:
            comerciante_nome = "Desconhecido"
            comerciante_id = p.get("comerciante_id")
            if comerciante_id:
                comerciante = supabase.table("comerciantes").select("nome").eq("id", comerciante_id).execute().data
                if comerciante:
                    comerciante_nome = comerciante[0].get("nome", "Desconhecido")
            produtos_data.append({
                "id": p.get("id"),
                "nome": p.get("nome"),
                "preco": p.get("preco"),
                "imagem": p.get("imagem") or "img/sem-produto.jpg",
                "comerciante": comerciante_nome
            })
        return render_template('admin_produtos.html', produtos=produtos_data)
    except Exception as e:
        print("❌ ERRO AO LISTAR PRODUTOS:", traceback.format_exc())
        flash(f"Erro ao carregar produtos: {e}", "danger")
        return redirect(url_for('admin.admin_dashboard'))

# ---------------- DETALHES DO PRODUTO ----------------
@admin_bp.route('/admin/produto/<int:id>')
@login_required
def admin_produto_detalhes(id):
    supabase = current_app.config['supabase']
    try:
        produto = supabase.table("produtos").select("*").eq("id", id).execute().data
        if not produto:
            flash("❌ Produto não encontrado.", "warning")
            return redirect(url_for('admin.admin_produtos'))
        p = produto[0]
        comerciante = supabase.table("comerciantes").select("*").eq("id", p["comerciante_id"]).execute().data
        p["comerciante_nome"] = comerciante[0]["nome"] if comerciante else "Desconhecido"
        return render_template("admin_produto_detalhes.html", produto=p)
    except Exception as e:
        print("❌ ERRO AO CARREGAR DETALHES:", traceback.format_exc())
        flash(f"Erro ao carregar detalhes do produto: {e}", "danger")
        return redirect(url_for('admin.admin_produtos'))

# ---------------- EDITAR PRODUTO ----------------
@admin_bp.route('/admin/produto/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_produto_editar(id):
    supabase = current_app.config['supabase']
    try:
        produto = supabase.table("produtos").select("*").eq("id", id).execute().data
        if not produto:
            flash("❌ Produto não encontrado.", "warning")
            return redirect(url_for('admin.admin_produtos'))
        if request.method == "POST":
            nome = request.form.get("nome")
            preco = float(request.form.get("preco", 0))
            imagem = request.form.get("imagem")
            supabase.table("produtos").update({
                "nome": nome,
                "preco": preco,
                "imagem": imagem
            }).eq("id", id).execute()
            flash("✅ Produto atualizado com sucesso!", "success")
            return redirect(url_for('admin.admin_produtos'))
        p = produto[0]
        return render_template("admin_produto_editar.html", produto=p)
    except Exception as e:
        print("❌ ERRO AO EDITAR PRODUTO:", traceback.format_exc())
        flash(f"Erro ao editar produto: {e}", "danger")
        return redirect(url_for('admin.admin_produtos'))

# ---------------- EXCLUIR PRODUTO ----------------
@admin_bp.route('/admin/produto/excluir/<int:id>', methods=['POST'])
@login_required
def admin_produto_excluir(id):
    supabase = current_app.config['supabase']
    try:
        supabase.table("produtos").delete().eq("id", id).execute()
        flash("🗑️ Produto excluído com sucesso!", "danger")
    except Exception as e:
        print("❌ ERRO AO EXCLUIR PRODUTO:", traceback.format_exc())
        flash(f"Erro ao excluir produto: {e}", "danger")
    return redirect(url_for('admin.admin_produtos'))


# ---------------- LISTA DE PESQUISAS ----------------
@admin_bp.route('/admin/pesquisas')
@login_required
def admin_pesquisas():
    """Exibe todas as pesquisas, estatísticas e métricas detalhadas."""
    supabase = current_app.config["supabase"]
    try:
        # 🔹 Busca todas as pesquisas
        pesquisas = supabase.table("pesquisas").select("*").order("criado_em", desc=True).execute().data or []

        # ---------------- Estatísticas detalhadas ----------------
        detalhes = []
        produtos_count = {}
        clicados_count = {}
        comerciantes_count = {}
        termos_count = {}

        for p in pesquisas:
            produto_nome = p.get("produto_nome", "Desconhecido")
            comerciante_nome = p.get("comerciante_nome", "Desconhecido")
            qtd_pesquisas = p.get("qtd_pesquisas", 0)
            qtd_cliques = p.get("qtd_cliques", 0)
            ultima_pesquisa = p.get("ultima_pesquisa", "")

            detalhes.append({
                "produto_nome": produto_nome,
                "comerciante_nome": comerciante_nome,
                "qtd_pesquisas": qtd_pesquisas,
                "qtd_cliques": qtd_cliques,
                "ultima_pesquisa": ultima_pesquisa
            })

            # 🔹 Estatísticas para gráficos
            produtos_count[produto_nome] = produtos_count.get(produto_nome, 0) + qtd_pesquisas
            clicados_count[produto_nome] = clicados_count.get(produto_nome, 0) + qtd_cliques
            comerciantes_count[comerciante_nome] = comerciantes_count.get(comerciante_nome, 0) + qtd_pesquisas

            termo = p.get("termo")
            if termo:
                termos_count[termo] = termos_count.get(termo, 0) + 1

        # 🔹 Top produtos pesquisados
        top_produtos_pesquisados = sorted(
            [{"nome": k, "count": v} for k, v in produtos_count.items()],
            key=lambda x: x["count"], reverse=True
        )[:10]

        # 🔹 Top produtos clicados
        top_produtos_clicados = sorted(
            [{"nome": k, "count": v} for k, v in clicados_count.items()],
            key=lambda x: x["count"], reverse=True
        )[:10]

        # 🔹 Comerciante mais pesquisado
        comerciante_mais_pesquisado = max(
            [{"nome": k, "count": v} for k, v in comerciantes_count.items()],
            key=lambda x: x["count"], default={"nome": "N/A", "count": 0}
        )

        # 🔹 Produto mais pesquisado e clicado
        produto_mais_pesquisado = top_produtos_pesquisados[0] if top_produtos_pesquisados else {"nome": "N/A", "count": 0}
        produto_mais_clicado = top_produtos_clicados[0] if top_produtos_clicados else {"nome": "N/A", "count": 0}

        total_pesquisas = sum([d['qtd_pesquisas'] for d in detalhes])

        # 🔹 Top termos pesquisados
        top_termos = sorted(termos_count.items(), key=lambda x: x[1], reverse=True)[:10]

        # 🔹 Lista de comerciantes para filtro
        comerciantes = supabase.table("comerciantes").select("nome").execute().data or []

        # 🔹 Renderiza template
        return render_template(
            'admin_pesquisas.html',
            pesquisas=detalhes,
            total_pesquisas=total_pesquisas,
            produto_mais_pesquisado=produto_mais_pesquisado,
            produto_mais_clicado=produto_mais_clicado,
            comerciante_mais_pesquisado=comerciante_mais_pesquisado,
            top_produtos_pesquisados=top_produtos_pesquisados,
            top_produtos_clicados=top_produtos_clicados,
            top_termos=top_termos,
            comerciantes=comerciantes
        )

    except Exception as e:
        print("❌ ERRO AO CARREGAR PESQUISAS:", traceback.format_exc())
        flash(f"Erro ao carregar pesquisas: {e}", "danger")
        return redirect(url_for('admin.admin_dashboard'))

# ---------------- APROVAR COMERCIANTE (AJAX) ----------------
@admin_bp.route("/admin/aprovar_comerciante/<id>", methods=["POST"])
@login_required
def aprovar_comerciante(id):
    supabase = current_app.config["supabase"]
    try:
        data = request.get_json() or {}
        aprovado = data.get("aprovado", True)

        # Busca comerciante pendente
        pendente = supabase.table("comerciantes_pendentes").select("*").eq("id", id).execute().data
        if not pendente:
            return jsonify({"sucesso": False, "erro": "Comerciante pendente não encontrado"}), 404
        
        c = pendente[0]

        if aprovado:
            # Insere na tabela comerciantes
            supabase.table("comerciantes").insert({
                "nome": c["nome"],
                "email": c["email"],
                "auth_user_id": c.get("auth_user_id"),
                "cidade": c.get("cidade"),
                "estado": c.get("estado"),
                "whatsapp": c.get("whatsapp"),
                "foto_perfil": c.get("foto_perfil"),
                "faz_entrega": c.get("faz_entrega", False),
                "endereco_logradouro": c.get("endereco_logradouro"),
                "endereco_numero": c.get("endereco_numero"),
                "endereco_complemento": c.get("endereco_complemento"),
                "latitude": c.get("latitude"),
                "longitude": c.get("longitude"),
                "aprovado": True,
                "status": "ativo",
                "data_cadastro": c.get("data_cadastro"),
                "criado_em": datetime.utcnow().isoformat(),
                "atualizado_em": datetime.utcnow().isoformat()
            }).execute()

        # Remove da tabela de pendentes
        supabase.table("comerciantes_pendentes").delete().eq("id", id).execute()

        return jsonify({"sucesso": True})
    
    except Exception as e:
        print("❌ ERRO AO APROVAR COMERCIANTE:", traceback.format_exc())
        return jsonify({"sucesso": False, "erro": str(e)}), 500
