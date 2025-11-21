from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Importa os modelos
from .comerciante import Comerciante, ComerciantePendente
from .produto import Produto
from .pesquisa import Pesquisa  # agora existe
