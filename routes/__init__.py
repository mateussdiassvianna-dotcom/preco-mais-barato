from flask import Flask

# -----------------------------
# Importa todos os Blueprints
# -----------------------------
from .index import index_bp
from .admin import admin_bp
from .consumidor import consumidor_bp
from .comerciante import comerciante_bp

def register_routes(app: Flask):
    """
    Registra todos os blueprints da aplicação Flask.
    """

    # Rota principal
    app.register_blueprint(index_bp)

    # Área administrativa
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Consumidor (público)
    app.register_blueprint(consumidor_bp, url_prefix="/consumidor")

    # Comerciante
    app.register_blueprint(comerciante_bp, url_prefix="/comerciante")
