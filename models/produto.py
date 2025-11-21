from . import db  # IMPORTANTE: precisa vir primeiro
from flask import url_for
from datetime import datetime

class Produto(db.Model):
    __tablename__ = "produtos"
    id = db.Column(db.Integer, primary_key=True)

    # RELAÇÃO COM COMERCIANTE
    comerciante_id = db.Column(db.Integer, db.ForeignKey("comerciantes.id"), nullable=False)

    nome = db.Column(db.String(150), nullable=False)
    marca = db.Column(db.String(100), default="")
    preco = db.Column(db.Float, nullable=False)
    unidade_medida = db.Column(db.String(50), default="unidade")
    categoria = db.Column(db.String(100), default="")
    descricao = db.Column(db.String(500), default="")
    imagem = db.Column(db.String(300), default="")

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ⚠️ REMOVIDO: backref daqui! Vai ficar só no Comerciante
    # comerciante = db.relationship("Comerciante", backref="produtos")

    def imagem_url(self):
        if not self.imagem or self.imagem.strip() == "":
            return url_for("static", filename="img/sem-imagem.png")
        return self.imagem

    def preco_formatado(self):
        return f"R$ {self.preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def to_dict(self):
        return {
            "id": self.id,
            "comerciante_id": self.comerciante_id,
            "nome": self.nome or "",
            "marca": self.marca or "",
            "preco": float(self.preco) if self.preco else 0.0,
            "unidade_medida": self.unidade_medida or "unidade",
            "categoria": self.categoria or "",
            "descricao": self.descricao or "",
            "imagem": self.imagem_url(),
            "criado_em": getattr(self, 'criado_em', None).isoformat() if getattr(self, 'criado_em', None) else None,
            "atualizado_em": getattr(self, 'atualizado_em', None).isoformat() if getattr(self, 'atualizado_em', None) else None,
            "comerciante": {
                "id": self.comerciante.id if self.comerciante else None,
                "nome": getattr(self.comerciante, "nome", ""),
                "cidade": getattr(self.comerciante, "cidade", ""),
                "estado": getattr(self.comerciante, "estado", ""),
                "faz_entrega": getattr(self.comerciante, "faz_entrega", False),
            }
        }

    def __repr__(self):
        return f"<Produto {self.nome} ({self.unidade_medida}) - {self.preco_formatado()}>"
