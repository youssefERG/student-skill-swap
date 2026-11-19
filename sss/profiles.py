from flask import (
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .auth import current_user, login_required
from .database import get_db
from .skills import (
    get_catalog,
    get_selected_skill_ids,
    save_user_skills,
    selected_skill_ids,
)


def get_profile_details(user_id):
    """Get a student's skills and reviews for display."""
    database = get_db()

    offers = database.execute(
        """
        SELECT skills.name
        FROM skills
        JOIN user_skills ON user_skills.skill_id = skills.id
        WHERE user_skills.user_id = ? AND user_skills.kind = 'offer'
        ORDER BY skills.name COLLATE NOCASE
        """,
        (user_id,),
    ).fetchall()

    wants = database.execute(
        """
        SELECT skills.name
        FROM skills
        JOIN user_skills ON user_skills.skill_id = skills.id
        WHERE user_skills.user_id = ? AND user_skills.kind = 'want'
        ORDER BY skills.name COLLATE NOCASE
        """,
        (user_id,),
    ).fetchall()

    reviews = database.execute(
        """
        SELECT reviews.rating, reviews.comment,
               reviews.message_count, reviews.created_at,
               reviewer.name AS reviewer_name
        FROM reviews
        JOIN users AS reviewer ON reviewer.id = reviews.reviewer_id
        WHERE reviews.reviewed_user_id = ?
        ORDER BY reviews.created_at DESC, reviews.id DESC
        """,
        (user_id,),
    ).fetchall()

    return offers, wants, reviews


def register_profile_routes(app):
    """Register profile display and editing pages."""

    @app.route("/profile")
    @login_required
    def profile():
        user = current_user()
        if user is None:
            session.clear()
            return redirect(url_for("login"))

        offers, wants, reviews = get_profile_details(user["id"])

        return render_template(
            "student.html",
            student=user,
            offers=offers,
            wants=wants,
            reviews=reviews,
            is_own_profile=True,
        )

    @app.route("/profile/edit", methods=("GET", "POST"))
    @login_required
    def profile_edit():
        user = current_user()
        if user is None:
            session.clear()
            return redirect(url_for("login"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            bio = request.form.get("bio", "").strip()

            if not name:
                flash("Your name cannot be empty.")
                return redirect(url_for("profile_edit"))

            offers = selected_skill_ids("offers")
            wants = selected_skill_ids("wants")

            database = get_db()
            database.execute(
                "UPDATE users SET name = ?, bio = ? WHERE id = ?",
                (name, bio, user["id"]),
            )
            save_user_skills(user["id"], "offer", offers)
            save_user_skills(user["id"], "want", wants)
            database.commit()

            flash("Your profile has been updated.")
            return redirect(url_for("profile"))

        return render_template(
            "profile.html",
            user=user,
            catalog=get_catalog(),
            selected_offers=get_selected_skill_ids(user["id"], "offer"),
            selected_wants=get_selected_skill_ids(user["id"], "want"),
        )

    @app.route("/students/<int:user_id>")
    @login_required
    def student_profile(user_id):
        user = get_db().execute(
            "SELECT id, name, bio FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if user is None:
            abort(404)

        offers, wants, reviews = get_profile_details(user_id)

        return render_template(
            "student.html",
            student=user,
            offers=offers,
            wants=wants,
            reviews=reviews,
            is_own_profile=(user_id == session["user_id"]),
        )