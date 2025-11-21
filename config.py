import os

# ------------------------
# Diretórios Base
# ------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Banco de dados SQLite (se não tiver DATABASE_URL)
DB_DIR = os.path.join(BASE_DIR, "db")
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(DB_DIR, "database.sqlite")
SQLALCHEMY_TRACK_MODIFICATIONS = False

# ------------------------
# Segurança
# ------------------------
# Chave secreta da aplicação (troque em produção)
SECRET_KEY = os.environ.get("SECRET_KEY", "troque_para_uma_chave_secreta_em_producao")

# Senha do admin do painel
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# ------------------------
# Uploads
# ------------------------
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

# ------------------------
# Limite de upload (16 MB)
# ------------------------
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# ------------------------
# E-mail (SMTP com Gmail)
# ------------------------
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USE_SSL = False

# ⚠️ Configure seu Gmail e senha de aplicativo
MAIL_USERNAME = "mateussdiassvianna@gmail.com"  
MAIL_PASSWORD = "bxbj kzpv htya yrlyI"  # <- senha de app, NÃO a senha normal
MAIL_DEFAULT_SENDER = MAIL_USERNAME
