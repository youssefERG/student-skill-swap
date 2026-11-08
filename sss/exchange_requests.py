from flask import (
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .auth import login_required
from .database import get_db


def register_exchange_request_routes(app):
    """Register exchange request pages and actions."""

    @app.route("/requests")
    @login_required
    def requests_page():
        database = get_db()

        received = database.execute(
            """
            SELECT exchange_requests.*, users.name AS other_name
            FROM exchange_requests
            JOIN users ON users.id = exchange_requests.sender_id
            WHERE exchange_requests.receiver_id = ?
            ORDER BY exchange_requests.created_at DESC
            """,
            (session["user_id"],),
        ).fetchall()

        sent = database.execute(
            """
            SELECT exchange_requests.*, users.name AS other_name
            FROM exchange_requests
            JOIN users ON users.id = exchange_requests.receiver_id
            WHERE exchange_requests.sender_id = ?
            ORDER BY exchange_requests.created_at DESC
            """,
            (session["user_id"],),
        ).fetchall()

        return render_template(
            "requests.html",
            received=received,
            sent=sent,
        )

    @app.route("/requests/send/<int:user_id>", methods=("POST",))
    @login_required
    def send_request(user_id):
        if user_id == session["user_id"]:
            abort(400)

        database = get_db()
        recipient = database.execute(
            "SELECT id FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if recipient is None:
            abort(404)

        existing = database.execute(
            """
            SELECT id FROM exchange_requests
            WHERE sender_id = ? AND receiver_id = ? AND status = 'pending'
            """,
            (session["user_id"], user_id),
        ).fetchone()

        if existing:
            flash("You already have a pending request with this student.")
        else:
            message = request.form.get("message", "").strip()[:500]
            database.execute(
                """
                INSERT INTO exchange_requests (sender_id, receiver_id, message)
                VALUES (?, ?, ?)
                """,
                (session["user_id"], user_id, message),
            )
            database.commit()
            flash("Your exchange request was sent.")

        return redirect(url_for("requests_page"))

    @app.route("/requests/<int:request_id>/<action>", methods=("POST",))
    @login_required
    def update_request(request_id, action):
        if action not in ("accept", "decline"):
            abort(404)

        database = get_db()
        exchange = database.execute(
            "SELECT * FROM exchange_requests WHERE id = ?",
            (request_id,),
        ).fetchone()

        if exchange is None:
            abort(404)

        if exchange["receiver_id"] != session["user_id"]:
            abort(403)

        if exchange["status"] != "pending":
            flash("That request has already been handled.")
            return redirect(url_for("requests_page"))

        new_status = "accepted" if action == "accept" else "declined"
        database.execute(
            "UPDATE exchange_requests SET status = ? WHERE id = ?",
            (new_status, request_id),
        )

        if action == "accept":
            database.execute(
                "INSERT OR IGNORE INTO conversations (request_id) VALUES (?)",
                (request_id,),
            )

        database.commit()
        flash(f"Request {new_status}.")
        return redirect(url_for("requests_page"))