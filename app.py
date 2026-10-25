import os
import sqlite3
import jwt
from flask import Flask, g, jsonify, request
from security_utils import hash_password, verify_password, DUMMY_HASH
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

JWT_SECRET = os.environ.get("JWT_SECRET")
if JWT_SECRET is None:
    raise RuntimeError("JWT_SECRET environment variable is not set")
DATABASE = "recipes.db"
RECIPE_FIELDS_ERROR = (
    "Title and ingredients must be non-empty strings; "
    "instructions must be a string"
)

app = Flask(__name__)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def recipe_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "ingredients": row["ingredients"],
        "instructions": row["instructions"],
        "is_public": bool(row["is_public"]),
    }


@app.get("/")
def hello():
    return jsonify({"message": "Recipe Box API", "recipes": "/recipes"})


@app.get("/recipes")
def list_recipes():
    rows = get_db().execute("SELECT * FROM recipes ORDER BY id").fetchall()
    return jsonify([recipe_to_dict(r) for r in rows])


@app.get("/recipes/<int:recipe_id>")
def get_recipe(recipe_id):
    row = get_db().execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "Recipe not found"}), 404
    return jsonify(recipe_to_dict(row))


@app.post("/recipes")
def create_recipe():
    data = request.get_json(silent=True)
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("title"), str)
        or not isinstance(data.get("ingredients"), str)
        or not isinstance(data.get("instructions", ""), str)
        or not data["title"]
        or not data["ingredients"]
    ):
        return jsonify({"error": RECIPE_FIELDS_ERROR}), 400
    db = get_db()
    try:
        cursor = db.execute(
            """
            INSERT INTO recipes (title, ingredients, instructions, is_public)
            VALUES (?, ?, ?, ?)
            """,
            (
                data["title"],
                data["ingredients"],
                data.get("instructions", ""),
                1 if data.get("is_public", True) else 0,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
                return jsonify({
            "error": "A recipe with that title already exists"
        }), 409
    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return jsonify(recipe_to_dict(row)), 201


@app.patch("/recipes/<int:recipe_id>")
def update_recipe(recipe_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "A JSON body is required"}), 400
    fields, values = [], []
    for column in ("title", "ingredients", "instructions"):
        if column in data:
            value = data[column]
            if not isinstance(value, str) or (
                column != "instructions" and not value
            ):
                return jsonify({"error": RECIPE_FIELDS_ERROR}), 400
            fields.append(f"{column} = ?")
            values.append(value)
    if "is_public" in data:
        fields.append("is_public = ?")
        values.append(1 if data["is_public"] else 0)
    if not fields:
        return jsonify({"error": "Nothing to update"}), 400
    values.append(recipe_id)
    db = get_db()
    try:
        cursor = db.execute(
            f"UPDATE recipes SET {', '.join(fields)} WHERE id = ?", values
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({
            "error": "A recipe with that title already exists"
        }), 409
    if cursor.rowcount == 0:
        return jsonify({"error": "Recipe not found"}), 404
    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    return jsonify(recipe_to_dict(row))


@app.delete("/recipes/<int:recipe_id>")
def delete_recipe(recipe_id):
    db = get_db()
    cursor = db.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    db.commit()
    if cursor.rowcount == 0:
        return jsonify({"error": "Recipe not found"}), 404
    return "", 204


@app.post("/register")
def register_user():
    data = request.get_json(silent=True)

    if (
        not isinstance(data, dict)
        or not isinstance(data.get("username"), str)
        or not isinstance(data.get("email"), str)
        or not isinstance(data.get("password"), str)
        or not data["username"]
        or not data["email"]
        or not data["password"]
    ):
        return jsonify({
            "error": "Username, email, and password are required"
        }), 400
    db = get_db()

    username = data["username"]
    email = data["email"]
    password = data["password"]

    password_hash = hash_password(password)

    try:
        cursor = db.execute(
            """
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (username, email, password_hash),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username or email already exists"}), 409

    new_user_id = cursor.lastrowid

    return jsonify({
        "id": new_user_id,
        "username": username,
        "email": email,
    }), 201


@app.post("/login")
def login():
    data = request.get_json(silent=True)
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("username"), str)
        or not isinstance(data.get("password"), str)
        or not data["username"]
        or not data["password"]
    ):
        return jsonify({"error": "Username and password are required"}), 400
    username = data["username"]
    password = data["password"]
    db = get_db()
    user = db.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if user:
        stored_hash = user["password_hash"]
    else:
        stored_hash = DUMMY_HASH

    password_ok = verify_password(stored_hash, password)

    if not user or not password_ok:
        return jsonify({"error": "Invalid username or password"}), 401

    payload = {
        "sub": str(user["id"]),
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    return jsonify({
        "id": user["id"],
        "username": user["username"],
        "token": token,
    }), 200


if __name__ == "__main__":
    app.run(debug=True)
