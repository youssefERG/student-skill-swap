from flask import render_template


def register_home_routes(app):
    """Register the home page."""

    @app.route("/")
    def home():
        return render_template("index.html")