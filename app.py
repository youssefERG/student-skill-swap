import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)
DATABASE = INSTANCE_DIR / "student_skill_swap.db"

# These are the only skills users can select. Keep this list focused on IT.
SKILL_GROUPS = {
    "Programming languages": [
        "Python",
        "JavaScript",
        "TypeScript",
        "Java",
        "C",
        "C++",
        "C#",
        "PHP",
        "Ruby",
        "Go",
        "Rust",
        "Bash",
    ],
    "Web development": [
        "HTML",
        "CSS",
        "Flask",
        "Django",
        "React",
        "Node.js",
        "REST APIs",
    ],
    "Data and AI": [
        "SQL",
        "Data analysis",
        "Machine learning",
    ],
    "IT and tools": [
        "Git and GitHub",
        "Linux",
        "Cybersecurity basics",
        "Computer networking",
        "Docker",
        "Cloud computing",
        "UI/UX for software",
    ],
}

ALL_SKILLS = [
    skill
    for skills_in_group in SKILL_GROUPS.values()
    for skill in skills_in_group
]
ALLOWED_SKILLS = set(ALL_SKILLS)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "local-development-key-change-before-deployment",
)


def get_db():
    """Get one SQLite connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    database = g.pop("db", None)
    if database is not None:
        database.close()


def init_db():
    """Create the database tables and insert the allowed skill list."""
    database = sqlite3.connect(DATABASE)
    database.execute("PRAGMA foreign_keys = ON")
    database.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            bio TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE
        );

        CREATE TABLE IF NOT EXISTS user_skills (
            user_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            kind TEXT NOT NULL CHECK (kind IN ('offer', 'want')),
            PRIMARY KEY (user_id, skill_id, kind),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS exchange_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'accepted', 'declined')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL UNIQUE,
            FOREIGN KEY (request_id)
                REFERENCES exchange_requests(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id)
                REFERENCES conversations(id) ON DELETE CASCADE,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )

    for skill_name in ALL_SKILLS:
        database.execute(
            "INSERT OR IGNORE INTO skills (name) VALUES (?)",
            (skill_name,),
        )

    database.commit()
    database.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if session.get("user_id") is None:
            flash("Please log in first.")
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None

    return get_db().execute(
        "SELECT id, name, email, bio FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()


def get_catalog():
    """Return predefined skills grouped for the profile page."""
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
    database = get_db()
    allowed_ids = {
        str(row["id"])
        for row in database.execute(
            "SELECT id FROM skills WHERE name IN ({})".format(
                ",".join("?" for _ in ALL_SKILLS)
            ),
            ALL_SKILLS,
        ).fetchall()
    }

    return {
        int(skill_id)
        for skill_id in raw_ids
        if skill_id in allowed_ids
    }


def save_user_skills(user_id, kind, skill_ids):
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
    rows = get_db().execute(
        """
        SELECT skill_id
        FROM user_skills
        WHERE user_id = ? AND kind = ?
        """,
        (user_id, kind),
    ).fetchall()
    return {row["skill_id"] for row in rows}


@app.route("/")
def home():
    return render_template("index.html")


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


init_db()


if __name__ == "__main__":
    app.run(debug=True)