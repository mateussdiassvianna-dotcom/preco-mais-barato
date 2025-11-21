from flask import Blueprint, render_template

# Cria o Blueprint do index
index_bp = Blueprint('index', __name__, template_folder='../templates')

# Rota principal
@index_bp.route('/')
def index():
    """
    Página inicial do sistema.
    Contém links para Admin, Consumidor e Comerciante.
    """
    return render_template('index.html')
