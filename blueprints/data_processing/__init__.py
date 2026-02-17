from flask import Blueprint

date_processing_bp = Blueprint(
    'date_processing_bp',
    __name__,
    template_folder='../../templates'
)

from . import routes
from . import normalizer
from . import parser
from . import schema

