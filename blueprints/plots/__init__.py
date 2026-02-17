from flask import Blueprint

plots_bp = Blueprint(
    'plots_bp',
    __name__,
    template_folder='../../templates'
)

from . import routes
from . import builder