from flask import Blueprint

core_bp = Blueprint(
    'core_bp',
    __name__,
    template_folder='../../templates'
)

from . import routes