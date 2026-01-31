from src.db import get_conn
from src.security import verify_password

def check_user(username, password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT username, role, password_hash FROM users WHERE username=%s",
        (username,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    db_username, db_role, db_hash = row

    if verify_password(password, db_hash):
        return (db_username, db_role)

    return None
