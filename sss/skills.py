from flask import request

from .database import get_db
from .skill_catalog import ALL_SKILLS, ALLOWED_SKILLS, SKILL_GROUPS


def get_catalog():
    """Return the approved skills grouped for the profile page."""
    database = get_db()
    grouped_skills = []

    for group_name, skill_names in SKILL_GROUPS.items():
        placeholders = ",".join("?" for _ in skill_names)
        rows = database.execute(
            f"""
            SELECT id, name
            FROM skills
            WHERE name IN ({placeholders})
            ORDER BY name COLLATE NOCASE
            """,
            skill_names,
        ).fetchall()
        grouped_skills.append((group_name, rows))

    return grouped_skills


def selected_skill_ids(form_field):
    """Accept only IDs belonging to the predefined skill catalogue."""
    raw_ids = request.form.getlist(form_field)
    placeholders = ",".join("?" for _ in ALL_SKILLS)
    rows = get_db().execute(
        f"SELECT id FROM skills WHERE name IN ({placeholders})",
        ALL_SKILLS,
    ).fetchall()
    allowed_ids = {str(row["id"]) for row in rows}

    return {
        int(skill_id)
        for skill_id in raw_ids
        if skill_id in allowed_ids
    }


def save_user_skills(user_id, kind, skill_ids):
    """Replace a user's selected offered or wanted skills."""
    database = get_db()
    database.execute(
        "DELETE FROM user_skills WHERE user_id = ? AND kind = ?",
        (user_id, kind),
    )

    for skill_id in skill_ids:
        database.execute(
            """
            INSERT OR IGNORE INTO user_skills (user_id, skill_id, kind)
            VALUES (?, ?, ?)
            """,
            (user_id, skill_id, kind),
        )


def get_selected_skill_ids(user_id, kind):
    """Return a set of skill IDs selected by a user."""
    rows = get_db().execute(
        """
        SELECT skill_id
        FROM user_skills
        WHERE user_id = ? AND kind = ?
        """,
        (user_id, kind),
    ).fetchall()

    return {row["skill_id"] for row in rows}