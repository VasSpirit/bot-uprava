from fastapi import Request
from itsdangerous import URLSafeSerializer
import sqlite3
from passlib.hash import bcrypt

SECRET = "SUPER_SECRET_KEY"
serializer = URLSafeSerializer(SECRET)

def create_user_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
    conn.commit()
    conn.close()

def register_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, bcrypt.hash(password)))
    conn.commit()
    conn.close()

def verify_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    return row and bcrypt.verify(password, row[0])

def user_exists(username):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    return row is not None

def get_current_user(request: Request):
    token = request.cookies.get("session")
    if not token:
        return None
    try:
        username = serializer.loads(token)
        return username
    except:
        return None

def login_user(response, username):
    token = serializer.dumps(username)
    response.set_cookie("session", token)

def logout_user(response):
    response.delete_cookie("session")
