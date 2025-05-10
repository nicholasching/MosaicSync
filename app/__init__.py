from flask import Flask
from config import Config
import logging

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure logging to match the level in other modules
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    app.logger.setLevel(logging.INFO)

    # Ensure the instance folder exists (if using instance-relative config later)
    # try:
    #     os.makedirs(app.instance_path)
    # except OSError:
    #     pass

    with app.app_context():
        from .routes import main_bp  # Import routes
        app.register_blueprint(main_bp)

    app.logger.info("Flask app created and configured.")
    return app
