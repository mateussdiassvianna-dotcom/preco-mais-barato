from flask import Flask
from flask_mail import Mail
from models import db

mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config")  # carrega configurações do config.py

    # Inicializa extensões
    db.init_app(app)
    mail.init_app(app)

    # Importa rotas (ajuste o nome do arquivo se não for routes.py)
    with app.app_context():
        import routes  

        # Cria tabelas se não existirem
        db.create_all()

    return app
