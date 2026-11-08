import os

from flask import Flask

from .auth import register_auth_routes
from .database import BASE_DIR, close_db, init_db
from .exchange_requests import register_exchange_request_routes
from .home import register_home_routes
from .messages import register_message_routes
from .profiles import register_profile_routes
from .search import register_search_routes


def create_app():
    """Create the Flask app and connect its feature routes."""
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )

    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "local-development-key-change-before-deployment",
    )

    app.teardown_appcontext(close_db)
    init_db()

    register_home_routes(app)
    register_auth_routes(app)
    register_profile_routes(app)
    register_search_routes(app)
    register_exchange_request_routes(app)
    register_message_routes(app)

    return app