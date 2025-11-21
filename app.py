from flask import Flask
from supabase import create_client
from flask_mail import Mail
from extensions import db
from dotenv import load_dotenv
import os

# === BLUEPRINTS ===
from routes.index import index_bp
from routes.admin import admin_bp
from routes.consumidor import consumidor_bp
from routes.comerciante import comerciante_bp

# === Carrega variáveis do .env ===
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Cria app Flask ===
app = Flask(__name__)
# ... suas outras configs, blueprints e inicializações


def create_app():
    app = Flask(__name__)
    app.secret_key = "uma_chave_secreta_para_sessao"

    # === CONFIGURAÇÕES DO BANCO LOCAL (caso use SQLAlchemy também) ===
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///meupreco.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    # === DISPONIBILIZA SUPABASE ===
    app.config["supabase"] = supabase

    # === FLASK MAIL ===
    app.config["MAIL_SERVER"] = "smtp.seuservidoremail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = "seuemail@dominio.com"
    app.config["MAIL_PASSWORD"] = "suasenha"

    mail = Mail(app)
    app.extensions["mail"] = mail

    # === BLUEPRINTS ===
    app.register_blueprint(index_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(comerciante_bp, url_prefix="/comerciante")
    app.register_blueprint(consumidor_bp, url_prefix="/consumidor")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
