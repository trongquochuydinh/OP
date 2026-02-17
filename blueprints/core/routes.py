from flask import (
    render_template
)

from . import core_bp
from config import CHART_TYPES

@core_bp.route("/", methods=['GET'])
def init_main():
    return render_template(
        "main_template.html",
        chart_types=CHART_TYPES
    )