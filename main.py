import os
import logging
from flask import (
    Flask, g, session, render_template
)

FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')

app = Flask(__name__)

app.config.update(
    SECRET_KEY=FLASK_SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False
)

@app.route("/")
def init_home():
    return render_template("main_template.html")

if __name__ == "__main__":
    port_app = os.environ.get("PORT_APP", 8080)
    logging.info("Trying to run on http://0.0.0.0:%s", port_app)
    app.run(port=port_app, host="0.0.0.0")