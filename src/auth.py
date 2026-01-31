from src.db import get_conn

def check_user(username, password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT username, role FROM users WHERE username=%s AND password=%s",
        (username, password)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row  # None or (username, role)
