from flask import (
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .auth import login_required
from .database import get_db


def get_accessible_conversation(database, conversation_id, user_id):
    """Return a conversation only if this user belongs to its accepted exchange."""
    return database.execute(
        """
        SELECT conversations.id,
               exchange_requests.id AS request_id,
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
        (user_id, conversation_id, user_id, user_id),
    ).fetchone()


def get_message_count(database, conversation_id):
    """Return the total number of messages in a conversation."""
    result = database.execute(
        """
        SELECT COUNT(*) AS total
        FROM messages
        WHERE conversation_id = ?
        """,
        (conversation_id,),
    ).fetchone()

    return result["total"]


def register_message_routes(app):
    """Register the conversation list and private messaging routes."""

    @app.route("/messages")
    @login_required
    def messages():
        user_id = session["user_id"]

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
            (user_id, user_id, user_id),
        ).fetchall()

        return render_template(
            "messages.html",
            conversations=conversations,
            active=None,
            messages=[],
            message_count=0,
            last_message_id=0,
            my_review=None,
            user_id=user_id,
        )

    @app.route("/messages/<int:conversation_id>", methods=("GET", "POST"))
    @login_required
    def conversation(conversation_id):
        database = get_db()
        user_id = session["user_id"]

        active = get_accessible_conversation(
            database,
            conversation_id,
            user_id,
        )

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
                    (conversation_id, user_id, body[:2000]),
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

        last_message_id = (
            message_rows[-1]["id"] if message_rows else 0
        )

        my_review = database.execute(
            """
            SELECT rating, comment, message_count, created_at
            FROM reviews
            WHERE request_id = ? AND reviewer_id = ?
            """,
            (active["request_id"], user_id),
        ).fetchone()

        return render_template(
            "messages.html",
            conversations=[],
            active=active,
            messages=message_rows,
            message_count=get_message_count(database, conversation_id),
            last_message_id=last_message_id,
            my_review=my_review,
            user_id=user_id,
        )

    @app.route(
        "/messages/<int:conversation_id>/updates",
        methods=("GET",),
    )
    @login_required
    def conversation_updates(conversation_id):
        database = get_db()
        user_id = session["user_id"]

        active = get_accessible_conversation(
            database,
            conversation_id,
            user_id,
        )

        if active is None:
            abort(403)

        after_id = request.args.get("after_id", default=0, type=int)
        if after_id is None or after_id < 0:
            after_id = 0

        new_messages = database.execute(
            """
            SELECT messages.id,
                   messages.sender_id,
                   messages.body,
                   messages.created_at,
                   users.name AS sender_name
            FROM messages
            JOIN users ON users.id = messages.sender_id
            WHERE messages.conversation_id = ?
              AND messages.id > ?
            ORDER BY messages.created_at, messages.id
            """,
            (conversation_id, after_id),
        ).fetchall()

        return jsonify(
            {
                "messages": [
                    {
                        "id": message["id"],
                        "sender_id": message["sender_id"],
                        "sender_name": message["sender_name"],
                        "body": message["body"],
                        "created_at": message["created_at"],
                    }
                    for message in new_messages
                ],
                "message_count": get_message_count(
                    database,
                    conversation_id,
                ),
            }
        )