from functools import wraps

from flask import (
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .database import get_db


def login_required(view):
    """Redirect visitors to login when they are not authenticated."""
    @wraps(view)
    def wrapped_view(**kwargs):
        if session.get("user_id") is None:
            flash("Please log in first.")
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


def current_user():
    """Return the currently logged-in user, if one exists."""
    user_id = session.get("user_id")
    if user_id is None:
        return None

    return get_db().execute(
        "SELECT id, name, email, bio FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()


def register_auth_routes(app):
    """Register account and session routes."""

    @app.route("/register", methods=("GET", "POST"))
    def register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not name or not email or not password:
                flash("Please fill in your name, email, and password.")
                return render_template("register.html")

            if len(password) < 8:
                flash("Your password must be at least 8 characters.")
                return render_template("register.html")

            database = get_db()
            existing_user = database.execute(
                "SELECT id FROM users WHERE email = ?",
                (email,),
            ).fetchone()

            if existing_user:
                flash("That email address is already registered.")
                return render_template("register.html")

            cursor = database.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (name, email, generate_password_hash(password)),
            )
            database.commit()

            session.clear()
            session["user_id"] = cursor.lastrowid
            flash("Your account is ready. Choose your skills on your profile.")
            return redirect(url_for("profile"))

        return render_template("register.html")

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = get_db().execute(
                "SELECT * FROM users WHERE email = ?",
                (email,),
            ).fetchone()

            if user is None or not check_password_hash(
                user["password_hash"], password
            ):
                flash("The email or password is incorrect.")
                return render_template("login.html")

            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("profile"))

        return render_template("login.html")

    @app.route("/logout", methods=("POST",))
    def logout():
        session.clear()
        flash("You are logged out.")
        return redirect(url_for("home"))