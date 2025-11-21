from flask import Blueprint, render_template, request, jsonify, current_app
from datetime import datetime
import math
import unicodedata

# -----------------------------
# Blueprint Consumidor
# -----------------------------
consumidor_bp = Blueprint(
    'consumidor',
    __name__,
    template_folder='../templates/consumidor'
)

# ---------------- Normalização de strings ----------------
def normaliza(texto):
    return unicodedata.normalize('NFKD', texto or '').encode('ASCII', 'ignore').decode('utf-8').lower().strip()

# ---------------- Tratamento seguro de latitude/longitude ----------------
def try_float(v):
    if v is None:
        return None
    if isinstance(v, (float, int)):
        return float(v)
    s = str(v).strip().replace(",", ".")
    try:
        return float(s)
    except:
        return None

# ---------------- Haversine (linha reta precisa, km) ----------------
def distancia_haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    R = 6372.795477598  # km
    return R * c

# ---------------- Estimativa de custo de deslocamento ----------------
def custo_deslocamento(distancia_km, consumo_km_l=10, preco_litro=6.0):
    if distancia_km is None:
        return 0.0
    litros_necessarios = distancia_km / consumo_km_l
    return litros_necessarios * preco_litro

# ---------------- Correção automática conservadora de coordenadas ----------------
def melhor_distancia_user_comerciante(lat_user, lon_user, raw_lat, raw_lon):
    """
    Retorna (lat, lon, motivo) escolhendo a interpretação mais plausível
    entre (orig, swap, sinais invertidos). Se tudo inválido -> (None, None, motivo).
    """
    lat_c = try_float(raw_lat)
    lon_c = try_float(raw_lon)

    if lat_c is None and lon_c is None:
        return None, None, "missing"

    combos = [
        (lat_c, lon_c, "orig"),
        (lon_c, lat_c, "swap"),
        (-lat_c if lat_c is not None else None, lon_c, "neg_lat"),
        (lat_c, -lon_c if lon_c is not None else None, "neg_lon"),
        (-lat_c if lat_c is not None else None, -lon_c if lon_c is not None else None, "neg_both"),
    ]

    combos_validos = []
    for lat_try, lon_try, tag in combos:
        if lat_try is None or lon_try is None:
            continue
        if -90 <= lat_try <= 90 and -180 <= lon_try <= 180:
            combos_validos.append((lat_try, lon_try, tag))

    if not combos_validos:
        return None, None, "invalid_range"

    melhor = None
    melhor_tag = None
    menor_dist = None

    for lat_try, lon_try, tag in combos_validos:
        try:
            d = distancia_haversine(lat_user, lon_user, lat_try, lon_try)
        except Exception:
            continue
        if menor_dist is None or d < menor_dist:
            menor_dist = d
            melhor = (lat_try, lon_try)
            melhor_tag = tag

    if menor_dist is None:
        return None, None, "calc_error"

    # sanity check: se estiver absurdamente longe, considera inválido
    if menor_dist > 2000:
        return None, None, "absurdo"

    # se a melhor interpretação não for a original, logue (print) para auditoria
    if melhor_tag != "orig":
        print(f"[WARN] Coordenada do comerciante ajustada ({melhor_tag}). raw=({raw_lat},{raw_lon}) -> used=({melhor[0]},{melhor[1]}) dist_km={menor_dist:.3f}")

    return melhor[0], melhor[1], melhor_tag

# ---------------- ROTA DO CONSUMIDOR (com tudo integrado) ----------------
@consumidor_bp.route('/')
def consumidor_home():
    supabase = current_app.config["supabase"]

    # ---------------- parâmetros ----------------
    busca = normaliza(request.args.get('busca', ''))
    estado = normaliza(request.args.get('estado', ''))
    cidade = normaliza(request.args.get('cidade', ''))
    filtro_entrega = request.args.get('entrega', '').lower() == 'true'
    filtro_proximos = request.args.get('proximos', '').lower() == 'true'
    filtro_custo = request.args.get('custo', '').lower() == 'true'
    ordenar_novos = request.args.get('novos', '').lower() == 'true'
    lat_user = request.args.get('lat', type=float)
    lon_user = request.args.get('lon', type=float)

    # ---------------- busca produtos ----------------
    produtos_resp = supabase.table("produtos").select("*, comerciante:comerciante_id(*)").execute()
    produtos = produtos_resp.data or []

    filtrados = []
    distancias_por_comerciante = {}

    for p in produtos:
        c = p.get("comerciante", {})
        comerci_id = c.get("id")

        # filtros básicos
        if c.get("status") != "ativo":
            continue
        if estado and normaliza(c.get("estado")) != estado:
            continue
        if cidade and normaliza(c.get("cidade")) != cidade:
            continue
        if filtro_entrega and not c.get("faz_entrega", False):
            continue
        if busca and busca not in normaliza(p.get("nome")):
            continue

        # calcular distância uma vez só por comerciante
        if comerci_id not in distancias_por_comerciante:
            dist = None
            custo_viagem = 0.0

            if lat_user is not None and lon_user is not None and (c.get("latitude") or c.get("longitude")):
                # tenta escolher a melhor interpretação das coordenadas do comerciante
                lat_corr, lon_corr, motivo = melhor_distancia_user_comerciante(
                    lat_user, lon_user,
                    c.get("latitude"),
                    c.get("longitude")
                )

                if lat_corr is not None and lon_corr is not None:
                    try:
                        dist = distancia_haversine(lat_user, lon_user, lat_corr, lon_corr)
                        custo_viagem = custo_deslocamento(dist)
                    except Exception as e:
                        print(f"[ERROR] erro ao calcular distancia para comerciante {comerci_id}: {e}")
                        dist = None
                        custo_viagem = 0.0
                else:
                    # sem coordenada válida interpretada
                    dist = None
                    custo_viagem = 0.0
                    print(f"[INFO] comerciante {comerci_id} sem coordenada válida (motivo: {motivo}). raw=({c.get('latitude')},{c.get('longitude')})")

            distancias_por_comerciante[comerci_id] = {
                "distancia": dist,
                "custo_viagem": custo_viagem
            }

        info_com = distancias_por_comerciante[comerci_id]

        # mantém o valor numérico em km para uso interno
        p["distancia"] = info_com["distancia"]

        # adiciona versão arredondada (float) com 2 casas decimais
        if info_com["distancia"] is not None:
            p["distancia_km"] = round(float(info_com["distancia"]), 2)
            # string pronta pra exibir no card no formato brasileiro "12,34 km"
            p["distancia_display"] = f"{p['distancia_km']:.2f}".replace('.', ',') + " km"
        else:
            p["distancia_km"] = None
            p["distancia_display"] = None

        # custo_total do produto = preco produto + custo_viagem do comerciante (único)
        p["custo_total"] = float(p.get("preco") or 0) + (info_com["custo_viagem"] or 0.0)

        filtrados.append(p)

        # ---------------- REGISTRA PESQUISA ----------------
        if busca:
            try:
                existente = (
                    supabase.table("pesquisas")
                    .select("*")
                    .eq("termo", busca)
                    .eq("produto_id", p["id"])
                    .execute()
                    .data
                )

                if existente:
                    supabase.table("pesquisas").update({
                        "qtd_pesquisas": existente[0]["qtd_pesquisas"] + 1,
                        "ultima_pesquisa": datetime.utcnow().isoformat()
                    }).eq("id", existente[0]["id"]).execute()
                else:
                    supabase.table("pesquisas").insert({
                        "termo": busca,
                        "produto_id": p["id"],
                        "produto_nome": p.get("nome"),
                        "comerciante_id": p.get("comerciante_id"),
                        "comerciante_nome": c.get("nome", "Desconhecido"),
                        "cidade": c.get("cidade"),
                        "estado": c.get("estado"),
                        "tipo": "pesquisa",
                        "qtd_pesquisas": 1,
                        "qtd_cliques": 0,
                        "criado_em": datetime.utcnow().isoformat()
                    }).execute()
            except Exception as e:
                print("❌ ERRO AO REGISTRAR PESQUISA:", e)

    # ---------------- ordenação ----------------
    if ordenar_novos:
        filtrados.sort(
            key=lambda x: x.get("criado_em") or datetime.utcnow().isoformat(),
            reverse=True
        )
    elif filtro_custo:
        filtrados.sort(key=lambda x: x.get("custo_total", float('inf')))
    elif filtro_proximos and lat_user is not None and lon_user is not None:
        # ordena pela distância numérica (em km)
        filtrados.sort(
            key=lambda x: x.get("distancia") if x.get("distancia") is not None else 9999
        )
    else:
        filtrados.sort(key=lambda x: float(x.get("preco") or 0))

    return render_template("consumidor.html", produtos=filtrados, filtros={
        "proximos": filtro_proximos,
        "custo": filtro_custo,
        "entrega": filtro_entrega,
        "novos": ordenar_novos,
        "busca": busca,
        "estado": estado,
        "cidade": cidade,
        "lat": lat_user,
        "lon": lon_user
    })




# ---------------- DETALHE DO PRODUTO ----------------
@consumidor_bp.route('/produto/<id>')
def produto(id):
    supabase = current_app.config["supabase"]

    resp = supabase.table("produtos").select("*, comerciante:comerciante_id(*)").eq("id", id).execute()
    produto = resp.data[0] if resp.data else None
    if not produto:
        return "Produto não encontrado", 404

    c = produto.get("comerciante") or {}

    # Converte data de cadastro
    data_cadastro = c.get('data_cadastro')
    if data_cadastro:
        try:
            c['data_cadastro'] = datetime.fromisoformat(data_cadastro)
        except ValueError:
            c['data_cadastro'] = None

    # Registra clique
    try:
        existente = supabase.table("pesquisas").select("*").eq("produto_id", produto["id"]).execute().data
        if existente:
            supabase.table("pesquisas").update({
                "qtd_cliques": existente[0]["qtd_cliques"] + 1,
                "ultima_pesquisa": datetime.utcnow().isoformat()
            }).eq("id", existente[0]["id"]).execute()
        else:
            supabase.table("pesquisas").insert({
                "termo": produto['nome'],
                "produto_id": produto['id'],
                "produto_nome": produto['nome'],
                "comerciante_id": produto.get("comerciante_id"),
                "comerciante_nome": c.get("nome", "Desconhecido"),
                "cidade": c.get("cidade"),
                "estado": c.get("estado"),
                "tipo": "clique",
                "qtd_pesquisas": 0,
                "qtd_cliques": 1,
                "criado_em": datetime.utcnow().isoformat()
            }).execute()
    except Exception as e:
        print("❌ ERRO AO REGISTRAR CLIQUE NO PRODUTO:", e)

    # Calcula status da loja
    agora = datetime.now()
    dias = ['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']
    hoje = dias[agora.weekday()]

    horario = c.get('horario_funcionamento') or {}
    info = horario.get(hoje) or {}

    fechado = info.get('fechado', False)
    inicio_str = info.get('inicio', '')
    fim_str = info.get('fim', '')

    loja_status = 'sem_horario'
    alerta_fechamento = False
    tempo_restante = None

    if not fechado and inicio_str and fim_str:
        try:
            inicio = datetime.strptime(inicio_str, "%H:%M").time()
            fim = datetime.strptime(fim_str, "%H:%M").time()
            hora_atual = agora.time()

            if inicio <= fim:
                if inicio <= hora_atual <= fim:
                    loja_status = 'aberto'
                    fim_datetime = datetime.combine(agora.date(), fim)
                    tempo_restante = fim_datetime - agora
                else:
                    loja_status = 'fechado'
            else:
                if hora_atual >= inicio or hora_atual <= fim:
                    loja_status = 'aberto'
                    fim_datetime = datetime.combine(agora.date(), fim)
                    if hora_atual >= inicio:
                        fim_datetime += timedelta(days=1)
                    tempo_restante = fim_datetime - agora
                else:
                    loja_status = 'fechado'

            alerta_fechamento = loja_status == 'aberto' and tempo_restante and tempo_restante <= timedelta(hours=1, minutes=30)
        except Exception as e:
            print("❌ ERRO AO CALCULAR HORÁRIO:", e)
            loja_status = 'sem_horario'
            alerta_fechamento = False
            tempo_restante = None

    return render_template(
        'produto.html',
        produto=produto,
        comerciante=c,
        loja_status=loja_status,
        alerta_fechamento=alerta_fechamento,
        tempo_restante=tempo_restante
    )

# ---------------- API PRODUTOS ----------------
@consumidor_bp.route('/api/produtos')
def api_produtos():
    supabase = current_app.config["supabase"]

    # ---------------- parâmetros ----------------
    busca = normaliza(request.args.get('busca', ''))
    estado = normaliza(request.args.get('estado', ''))
    cidade = normaliza(request.args.get('cidade', ''))
    filtro_entrega = request.args.get('entrega', '').lower() == 'true'
    filtro_proximos = request.args.get('proximos', '').lower() == 'true'
    filtro_custo = request.args.get('custo', '').lower() == 'true'
    ordenar_novos = request.args.get('novos', '').lower() == 'true'
    lat_user = request.args.get('lat', type=float)
    lon_user = request.args.get('lon', type=float)

    # ---------------- busca produtos ----------------
    produtos_resp = supabase.table("produtos").select("*, comerciante:comerciante_id(*)").execute()
    produtos = produtos_resp.data or []

    filtrados = []
    # MAP para comerciantes (calcular apenas 1 vez)
    distancias_por_comerciante = {}

    agora = datetime.now()
    dias = ['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']
    hoje = dias[agora.weekday()]

    for p in produtos:
        c = p.get("comerciante", {})
        comerci_id = c.get("id")
        if c.get("status") != "ativo":
            continue
        if estado and normaliza(c.get("estado")) != estado:
            continue
        if cidade and normaliza(c.get("cidade")) != cidade:
            continue
        if filtro_entrega and not c.get("faz_entrega", False):
            continue
        if busca and busca not in normaliza(p.get("nome")):
            continue

        # ---------------- calcula distância por comerciante (uma vez)
        if comerci_id not in distancias_por_comerciante:
            dist = None
            custo_viagem = 0.0
            if lat_user is not None and lon_user is not None and c.get("latitude") and c.get("longitude"):
                try:
                    dist = distancia(lat_user, lon_user, float(c["latitude"]), float(c["longitude"]))
                    custo_viagem = custo_deslocamento(dist)
                except Exception:
                    dist = None
                    custo_viagem = 0.0
            distancias_por_comerciante[comerci_id] = {"distancia": dist, "custo_viagem": custo_viagem}

        info_com = distancias_por_comerciante[comerci_id]
        p["distancia"] = info_com["distancia"]
        p["custo_total"] = float(p.get("preco") or 0) + (info_com["custo_viagem"] or 0.0)

        # ---------------- status da loja (independente da entrega) ----------------
        horario = c.get('horario_funcionamento') or {}
        info = horario.get(hoje) or {}

        loja_status = 'sem_horario'  # padrão se não houver dados
        try:
            fechado = bool(info.get('fechado', False))
            inicio_str = info.get('inicio', '').strip()
            fim_str = info.get('fim', '').strip()

            if fechado:
                loja_status = 'fechado'
            elif inicio_str and fim_str:
                inicio = datetime.strptime(inicio_str, "%H:%M").time()
                fim = datetime.strptime(fim_str, "%H:%M").time()
                hora_atual = agora.time()

                # Verifica se o horário passa da meia-noite
                if inicio <= fim:
                    loja_status = 'aberto' if inicio <= hora_atual <= fim else 'fechado'
                else:
                    loja_status = 'aberto' if hora_atual >= inicio or hora_atual <= fim else 'fechado'
            elif not fechado and (inicio_str or fim_str):
                loja_status = 'sem_horario'
            else:
                loja_status = 'sem_horario'
        except Exception:
            loja_status = 'sem_horario'

        c["loja_status"] = loja_status
        p["comerciante"] = c
        filtrados.append(p)

    # ---------------- ordenação ----------------
    if ordenar_novos:
        filtrados.sort(key=lambda x: x.get("criado_em") or datetime.utcnow().isoformat(), reverse=True)
    elif filtro_custo:
        filtrados.sort(key=lambda x: x.get("custo_total", float('inf')))
    elif filtro_proximos and lat_user is not None and lon_user is not None:
        filtrados.sort(key=lambda x: x.get("distancia") if x.get("distancia") is not None else 9999)
    else:
        filtrados.sort(key=lambda x: float(x.get("preco") or 0))

    # ---------------- JSON final ----------------
    produtos_json = []
    for p in filtrados:
        c = p.get("comerciante", {})
        produtos_json.append({
            "id": p.get("id"),
            "nome": p.get("nome"),
            "marca": p.get("marca", ""),
            "preco": float(p.get("preco") or 0),
            "categoria": p.get("categoria", ""),
            "descricao": p.get("descricao", ""),
            "imagem": p.get("imagem") or "/static/img/sem-imagem.png",
            "criado_em": p.get("criado_em"),
            "atualizado_em": p.get("atualizado_em"),
            "distancia": p.get("distancia"),
            "custo_total": p.get("custo_total"),
            "comerciante": {
                "id": c.get("id"),
                "nome": c.get("nome"),
                "cidade": c.get("cidade"),
                "estado": c.get("estado"),
                "faz_entrega": c.get("faz_entrega", False),
                "loja_status": c.get("loja_status", "sem_horario"),
                "horario_funcionamento": c.get("horario_funcionamento"),
                "latitude": c.get("latitude"),
                "longitude": c.get("longitude")
            }
        })

    return jsonify(produtos_json)