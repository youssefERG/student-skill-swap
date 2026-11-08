from flask import (
    flash,
    render_template,
    request,
    session,
)

from .auth import login_required
from .database import get_db
from .skills import ALLOWED_SKILLS, ALL_SKILLS


def register_search_routes(app):
    """Register the student skill search page."""

    @app.route("/search", methods=("GET", "POST"))
    @login_required
    def search():
        chosen_skill = ""

        if request.method == "POST":
            submitted_skill = request.form.get("skill", "")
            if submitted_skill in ALLOWED_SKILLS:
                chosen_skill = submitted_skill
            else:
                flash("Choose a skill from the list.")
        else:
            submitted_skill = request.args.get("skill", "")
            if submitted_skill in ALLOWED_SKILLS:
                chosen_skill = submitted_skill

        results = []
        if chosen_skill:
            results = get_db().execute(
                """
                SELECT users.id, users.name, users.bio,
                       GROUP_CONCAT(skills.name, ', ') AS matching_skills
                FROM users
                JOIN user_skills ON user_skills.user_id = users.id
                JOIN skills ON skills.id = user_skills.skill_id
                WHERE user_skills.kind = 'offer'
                  AND skills.name = ? COLLATE NOCASE
                  AND users.id != ?
                GROUP BY users.id, users.name, users.bio
                ORDER BY users.name COLLATE NOCASE
                """,
                (chosen_skill, session["user_id"]),
            ).fetchall()

        return render_template(
            "search.html",
            skill=chosen_skill,
            results=results,
            all_skills=ALL_SKILLS,
        )