# create_admin.py

import bcrypt
from db import get_db

def create_admin():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    staffID = "admin001"
    password = "admin123"  # You can change this later

    # Hash the password securely with bcrypt
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Check if admin exists
    cursor.execute("SELECT id FROM staff WHERE staffID = %s", (staffID,))
    existing = cursor.fetchone()
    if existing:
        print(" Admin already exists.")
        conn.close()
        return

    # Create new admin
    sql = """
    INSERT INTO staff (staffID, password, phone, role)
    VALUES (%s, %s, %s, %s)
    """
    cursor.execute(sql, (staffID, hashed, "0700000000", "admin"))
    conn.commit()
    conn.close()

    print(f" Admin '{staffID}' created successfully with password '{password}'.")

if __name__ == "__main__":
    create_admin()
