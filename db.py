# db.py
import mysql.connector
from config import DB_CONFIG

def get_db():
    """Create and return a new database connection."""
    return mysql.connector.connect(**DB_CONFIG)

def log_action(device_id, action, gate_id=None, meta=None):
    """
    Log a student laptop action (sign in / sign out) to the 'logs' table.
    """
    conn = get_db()
    cursor = conn.cursor()
    sql = "INSERT INTO logs (device_id, action, gate_id, meta) VALUES (%s, %s, %s, %s)"
    cursor.execute(sql, (device_id, action, gate_id, meta))
    conn.commit()
    conn.close()
    print(f"[DB] Logged {action} for {device_id}")

def get_logs(limit=50):
    """
    Get the most recent sign-in/sign-out logs.
    """
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM logs ORDER BY ts DESC LIMIT %s", (limit,))
    results = cursor.fetchall()
    conn.close()
    return results