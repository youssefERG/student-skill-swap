from flask import flash, redirect, render_template, request, session, url_for

from .auth import current_user, login_required
from .database import get_db
from .skills import (
    get_catalog,
    get_selected_skill_ids,
    save_user_skills,
    selected_skill_ids,
)


def register_profile_routes(app):
    """Register the profile page."""

    @app.route("/profile", methods=("GET", "POST"))
    @login_required
    def profile():
        user = current_user()
        if user is None:
            session.clear()
            return redirect(url_for("login"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            bio = request.form.get("bio", "").strip()

            if not name:
                flash("Your name cannot be empty.")
                return redirect(url_for("profile"))

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

            flash("Your profile has been saved.")
            return redirect(url_for("profile"))

        return render_template(
            "profile.html",
            user=user,
            catalog=get_catalog(),
            selected_offers=get_selected_skill_ids(user["id"], "offer"),
            selected_wants=get_selected_skill_ids(user["id"], "want"),
        )