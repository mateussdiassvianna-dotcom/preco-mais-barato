from . import db
from datetime import datetime

class Pesquisa(db.Model):
    __tablename__ = "pesquisas"
    id = db.Column(db.Integer, primary_key=True)
    termo = db.Column(db.String(200), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow) 

    def __repr__(self):
        return f"<Pesquisa {self.termo}>"
