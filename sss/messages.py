from flask import (
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .auth import login_required
from .database import get_db


def register_message_routes(app):
    """Register the conversation list and private messaging routes."""

    @app.route("/messages")
    @login_required
    def messages():
        conversations = get_db().execute(
            """
            SELECT conversations.id AS conversation_id,
                   other_user.name AS other_name
            FROM conversations
            JOIN exchange_requests
                ON exchange_requests.id = conversations.request_id
            JOIN users AS other_user
                ON other_user.id = CASE
                    WHEN exchange_requests.sender_id = ?
                        THEN exchange_requests.receiver_id
                    ELSE exchange_requests.sender_id
                END
            WHERE exchange_requests.status = 'accepted'
              AND (exchange_requests.sender_id = ?
                   OR exchange_requests.receiver_id = ?)
            ORDER BY conversations.id DESC
            """,
            (session["user_id"], session["user_id"], session["user_id"]),
        ).fetchall()

        return render_template(
            "messages.html",
            conversations=conversations,
            active=None,
            messages=[],
            user_id=session["user_id"],
        )

    @app.route("/messages/<int:conversation_id>", methods=("GET", "POST"))
    @login_required
    def conversation(conversation_id):
        database = get_db()
        active = database.execute(
            """
            SELECT conversations.id,
                   exchange_requests.sender_id,
                   exchange_requests.receiver_id,
                   CASE
                       WHEN exchange_requests.sender_id = ?
                           THEN receiver.name
                       ELSE sender.name
                   END AS other_name
            FROM conversations
            JOIN exchange_requests
                ON exchange_requests.id = conversations.request_id
            JOIN users AS sender
                ON sender.id = exchange_requests.sender_id
            JOIN users AS receiver
                ON receiver.id = exchange_requests.receiver_id
            WHERE conversations.id = ?
              AND exchange_requests.status = 'accepted'
              AND (exchange_requests.sender_id = ?
                   OR exchange_requests.receiver_id = ?)
            """,
            (
                session["user_id"],
                conversation_id,
                session["user_id"],
                session["user_id"],
            ),
        ).fetchone()

        if active is None:
            abort(403)

        if request.method == "POST":
            body = request.form.get("body", "").strip()
            if body:
                database.execute(
                    """
                    INSERT INTO messages (conversation_id, sender_id, body)
                    VALUES (?, ?, ?)
                    """,
                    (conversation_id, session["user_id"], body[:2000]),
                )
                database.commit()

            return redirect(
                url_for("conversation", conversation_id=conversation_id)
            )

        message_rows = database.execute(
            """
            SELECT messages.*, users.name AS sender_name
            FROM messages
            JOIN users ON users.id = messages.sender_id
            WHERE messages.conversation_id = ?
            ORDER BY messages.created_at, messages.id
            """,
            (conversation_id,),
        ).fetchall()

        return render_template(
            "messages.html",
            conversations=[],
            active=active,
            messages=message_rows,
            user_id=session["user_id"],
        )