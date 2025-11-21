from . import db  # precisa vir antes das classes
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import sqlalchemy.dialects.postgresql as pg

class ComerciantePendente(db.Model):
    __tablename__ = 'comerciantes_pendentes'

    id = db.Column(pg.UUID(as_uuid=True), primary_key=True)  # UUID agora
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=True)  # agora opcional
    cidade = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(50), nullable=False)
    whatsapp = db.Column(db.String(20), nullable=True)
    foto_perfil = db.Column(db.String(300))
    faz_entrega = db.Column(db.Boolean, default=False)
    endereco_logradouro = db.Column(db.String(200))
    endereco_numero = db.Column(db.String(50))
    endereco_complemento = db.Column(db.String(100))
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="pendente")  # pendente, aprovado, bloqueado
    auth_user_id = db.Column(pg.UUID(as_uuid=True), nullable=True)

    reset_token_hash = db.Column(db.String(64), nullable=True)
    reset_requested_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.senha_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.senha_hash, password)


class Comerciante(db.Model):
    __tablename__ = 'comerciantes'

    id = db.Column(pg.UUID(as_uuid=True), primary_key=True)  # UUID
    user_id = db.Column(pg.UUID(as_uuid=True), nullable=True)  # auth_user_id do Supabase
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=True)  # opcional
    cidade = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(50), nullable=False)
    whatsapp = db.Column(db.String(20), nullable=True)
    foto_perfil = db.Column(db.String(300))
    faz_entrega = db.Column(db.Boolean, default=False)
    endereco_logradouro = db.Column(db.String(200))
    endereco_numero = db.Column(db.String(50))
    endereco_complemento = db.Column(db.String(100))
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    aprovado = db.Column(db.Boolean, default=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="ativo")  # ativo, bloqueado

    produtos = db.relationship(
        "Produto",
        backref="comerciante",
        lazy=True,
        cascade="all, delete-orphan"
    )

    reset_token_hash = db.Column(db.String(64), nullable=True)
    reset_requested_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.senha_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.senha_hash, password)
