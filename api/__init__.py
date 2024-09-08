from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)

    CORS(app, origins=["https://app.przedmiar.pl", "https://app-stage.przedmiar.pl"])

    from .v1 import v1_blueprint
    app.register_blueprint(v1_blueprint, url_prefix='/v1')

    # Create a new instance of the blueprint for the latest prefix
    # and register it with the app
    latest_blueprint = v1_blueprint
    latest_blueprint.name = 'latest'
    app.register_blueprint(latest_blueprint, url_prefix='/latest')

    return app