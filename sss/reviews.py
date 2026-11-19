from flask import (
    abort,
    flash,
    redirect,
    request,
    session,
    url_for,
)

from .auth import login_required
from .database import get_db


def register_review_routes(app):
    """Register review submission for accepted exchanges."""

    @app.route("/reviews/<int:request_id>", methods=("POST",))
    @login_required
    def submit_review(request_id):
        database = get_db()

        exchange = database.execute(
            """
            SELECT conversations.id AS conversation_id,
                   exchange_requests.sender_id,
                   exchange_requests.receiver_id
            FROM exchange_requests
            JOIN conversations
                ON conversations.request_id = exchange_requests.id
            WHERE exchange_requests.id = ?
              AND exchange_requests.status = 'accepted'
            """,
            (request_id,),
        ).fetchone()

        if exchange is None:
            abort(404)

        reviewer_id = session["user_id"]
        if reviewer_id not in (exchange["sender_id"], exchange["receiver_id"]):
            abort(403)

        try:
            rating = int(request.form.get("rating", ""))
        except ValueError:
            rating = 0

        comment = request.form.get("comment", "").strip()

        if rating < 1 or rating > 5:
            flash("Choose a rating from 1 to 5 stars.")
            return redirect(
                url_for(
                    "conversation",
                    conversation_id=exchange["conversation_id"],
                )
            )

        if not comment:
            flash("Write a comment with your rating.")
            return redirect(
                url_for(
                    "conversation",
                    conversation_id=exchange["conversation_id"],
                )
            )

        comment = comment[:1000]

        existing_review = database.execute(
            """
            SELECT id FROM reviews
            WHERE request_id = ? AND reviewer_id = ?
            """,
            (request_id, reviewer_id),
        ).fetchone()

        if existing_review:
            flash("You have already reviewed this exchange.")
            return redirect(
                url_for(
                    "conversation",
                    conversation_id=exchange["conversation_id"],
                )
            )

        if reviewer_id == exchange["sender_id"]:
            reviewed_user_id = exchange["receiver_id"]
        else:
            reviewed_user_id = exchange["sender_id"]

        message_count = database.execute(
            "SELECT COUNT(*) AS total FROM messages WHERE conversation_id = ?",
            (exchange["conversation_id"],),
        ).fetchone()["total"]

        database.execute(
            """
            INSERT INTO reviews (
                request_id,
                reviewer_id,
                reviewed_user_id,
                rating,
                comment,
                message_count
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                reviewer_id,
                reviewed_user_id,
                rating,
                comment,
                message_count,
            ),
        )
        database.commit()

        flash("Your rating and comment have been added.")
        return redirect(
            url_for(
                "conversation",
                conversation_id=exchange["conversation_id"],
            )
        )