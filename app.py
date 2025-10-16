# app.py

from flask import (
    Flask, render_template, request, redirect, session, jsonify,
    url_for, flash, send_file
)
from db import get_db, log_action  # your existing db helper; must provide get_db()
import bcrypt
from datetime import datetime
import io

app = Flask(__name__)
# Replace with a secure secret in production (env var recommended)
app.secret_key = "replace-with-secure-secret"

# -------------------------
# Helpers
# -------------------------
def current_user():
    return session.get('user') or {}

def login_user_from_row(row):
    session['user'] = {
        'id': row['id'],
        'staffID': row.get('staffID'),
        'role': row.get('role')
    }

def require_login():
    u = current_user()
    if not u:
        flash("Please log in.")
        return False
    return True

def require_admin():
    u = current_user()
    if not u or u.get('role') != 'admin':
        flash("Admin access required.")
        return False
    return True

# -------------------------
# Auth
# -------------------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        staffID = request.form.get('staffID','').strip()
        password = request.form.get('password','')
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM staff WHERE staffID=%s", (staffID,))
        row = cur.fetchone()
        conn.close()
        if not row:
            flash("Invalid credentials.")
            return redirect(url_for('login'))
        try:
            stored = row['password'].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), stored):
                login_user_from_row(row)
                return redirect(url_for('home'))
            else:
                flash("Invalid credentials.")
                return redirect(url_for('login'))
        except Exception:
            flash("Login error.")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out.")
    return redirect(url_for('login'))

# -------------------------
# Landing & Dashboards
# -------------------------
@app.route('/')
def home():
    u = current_user()
    if not u:
        return redirect(url_for('login'))
    if u.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('staff_dashboard'))

@app.route('/admin')
def admin_dashboard():
    if not require_admin():
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM laptops")
    laptops = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM students")
    students = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM staff")
    staff = cur.fetchone()[0]
    conn.close()
    return render_template('admin_dashboard.html', stats={'laptops': laptops, 'students': students, 'staff': staff})

@app.route('/staff_dashboard')
def staff_dashboard():
    if not require_login():
        return redirect(url_for('login'))
    return render_template('staff_dashboard.html')

# -------------------------
# Staff management (admin)
# -------------------------
@app.route('/staff', methods=['GET'])
def manage_staff():
    if not require_admin():
        return redirect(url_for('home'))
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, staffID, phone, role, ts_created FROM staff ORDER BY id")
    staff = cur.fetchall()
    conn.close()
    return render_template('staff.html', staff=staff)

@app.route('/staff/add', methods=['POST'])
def add_staff():
    if not require_admin():
        return redirect(url_for('home'))
    staffID = request.form.get('staffID','').strip()
    phone = request.form.get('phone','').strip()
    password = request.form.get('password','').strip()
    role = request.form.get('role','staff')
    if not staffID or not password:
        flash("staffID and password required.")
        return redirect(url_for('manage_staff'))
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO staff (staffID, password, phone, role) VALUES (%s,%s,%s,%s)",
                    (staffID, hashed, phone, role))
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash("DB error: " + str(e))
    finally:
        conn.close()
    return redirect(url_for('manage_staff'))

@app.route('/staff/edit', methods=['POST'])
def edit_staff():
    if not require_admin():
        return redirect(url_for('home'))
    sid = request.form.get('id')
    phone = request.form.get('phone','').strip()
    role = request.form.get('role','staff')
    if not sid:
        flash("Missing staff id.")
        return redirect(url_for('manage_staff'))
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE staff SET phone=%s, role=%s WHERE id=%s", (phone, role, sid))
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash("DB error: " + str(e))
    finally:
        conn.close()
    return redirect(url_for('manage_staff'))

@app.route('/staff/delete', methods=['POST'])
def delete_staff():
    if not require_admin():
        return redirect(url_for('home'))
    sid = request.form.get('id')
    if not sid:
        flash("Missing id.")
        return redirect(url_for('manage_staff'))
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT staffID FROM staff WHERE id=%s", (sid,))
    row = cur.fetchone()
    if not row:
        conn.close()
        flash("Staff not found.")
        return redirect(url_for('manage_staff'))
    if row['staffID'] == current_user().get('staffID'):
        conn.close()
        flash("You cannot delete yourself.")
        return redirect(url_for('manage_staff'))
    try:
        cur2 = conn.cursor()
        cur2.execute("DELETE FROM staff WHERE id=%s", (sid,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash("DB error: " + str(e))
    finally:
        conn.close()
    return redirect(url_for('manage_staff'))

# -------------------------
# Students (staff can register)
# -------------------------
@app.route('/students', methods=['GET'])
def students_page():
    if not require_login():
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, studentID, name, phone, ts_created FROM students ORDER BY ts_created DESC")
    students = cur.fetchall()
    conn.close()
    return render_template('students_admin.html', students=students)

@app.route('/students/register', methods=['POST'])
def staff_register_student():
    if not require_login():
        return redirect(url_for('login'))
    user = current_user()
    if user.get('role') not in ('staff','admin'):
        flash("Permission denied.")
        return redirect(url_for('home'))
    studentID = request.form.get('studentID','').strip()
    name = request.form.get('name','').strip()
    phone = request.form.get('phone','').strip()
    if not studentID or not name:
        flash("studentID and name required.")
        return redirect(url_for('students_page'))
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO students (studentID, name, phone) VALUES (%s,%s,%s)", (studentID, name, phone))
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash("DB error: " + str(e))
    finally:
        conn.close()
    return redirect(url_for('students_page'))






@app.route('/students/edit', methods=['POST'])
def edit_student():
    if not require_login():
        return redirect(url_for('login'))
    sid = request.form.get('id')
    studentID = request.form.get('studentID', '').strip()
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    if not sid or not studentID or not name:
        flash("All fields except phone are required.")
        return redirect(url_for('students_page'))
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE students SET studentID=%s, name=%s, phone=%s WHERE id=%s",
                    (studentID, name, phone, sid))
        conn.commit()
        flash("Student updated successfully.")
    except Exception as e:
        conn.rollback()
        flash("DB error: " + str(e))
    finally:
        conn.close()
    return redirect(url_for('students_page'))

# -------------------------
# Laptops (combined table)
# Admin: create/edit/delete
# Staff: view + sign in/out
# -------------------------
@app.route('/laptops', methods=['GET'])
def laptops_page():
    if not require_login():
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM laptops ORDER BY ts_updated DESC")
    laptops = cur.fetchall()
    cur.execute("SELECT id, studentID, name FROM students ORDER BY name")
    students = cur.fetchall()
    conn.close()
    return render_template('laptops_admin.html', laptops=laptops, students=students)

@app.route('/laptops/save', methods=['POST'])
def save_laptop():
    if not require_admin():
        return redirect(url_for('home'))
    rec_id = request.form.get('id')
    name = request.form.get('name','').strip()
    studentID = request.form.get('studentID','').strip()
    phone = request.form.get('phone','').strip()
    serial = request.form.get('serial_number','').strip()
    make = request.form.get('make','').strip()
    model = request.form.get('model','').strip()
    if not name or not studentID or not serial:
        flash("name, studentID and serial_number are required.")
        return redirect(url_for('laptops_page'))
    conn = get_db()
    cur = conn.cursor()
    try:
        if rec_id:
            cur.execute("""UPDATE laptops
                           SET name=%s, studentID=%s, phone=%s, serial_number=%s, make=%s, model=%s
                           WHERE id=%s""", (name, studentID, phone, serial, make, model, rec_id))
        else:
            cur.execute("SELECT id FROM laptops WHERE serial_number=%s", (serial,))
            if cur.fetchone():
                flash("Laptop with that serial number already exists.")
                conn.close()
                return redirect(url_for('laptops_page'))
            cur.execute("""INSERT INTO laptops (name, studentID, phone, serial_number, make, model)
                           VALUES (%s,%s,%s,%s,%s,%s)""", (name, studentID, phone, serial, make, model))
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash("DB error: " + str(e))
    finally:
        conn.close()
    return redirect(url_for('laptops_page'))

@app.route('/laptops/delete', methods=['POST'])
def delete_laptop_route():
    if not require_admin():
        return redirect(url_for('home'))
    rec_id = request.form.get('id')
    if not rec_id:
        flash("Missing id.")
        return redirect(url_for('laptops_page'))
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM laptops WHERE id=%s", (rec_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash("DB error: " + str(e))
    finally:
        conn.close()
    return redirect(url_for('laptops_page'))

# -------------------------
# Search
# -------------------------
@app.route('/search', methods=['GET'])
def search():
    q = (request.args.get('q') or "").strip()
    laptop_results = []
    student_results = []

    if q:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        likeq = f"%{q}%"

        # Search in laptops
        cur.execute("""
            SELECT id, name, studentID, phone, serial_number, make, model, signed_in, ts_updated
            FROM laptops
            WHERE serial_number LIKE %s OR studentID LIKE %s OR name LIKE %s
            ORDER BY ts_updated DESC
            LIMIT 200
        """, (likeq, likeq, likeq))
        laptop_results = cur.fetchall()

        # Search in students (even those without laptops)
        cur.execute("""
            SELECT id, studentID, name, phone, ts_created
            FROM students
            WHERE studentID LIKE %s OR name LIKE %s OR phone LIKE %s
            ORDER BY ts_created DESC
            LIMIT 200
        """, (likeq, likeq, likeq))
        student_results = cur.fetchall()

        conn.close()

    if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
        return jsonify({'laptops': laptop_results, 'students': student_results})

    return render_template('search.html', laptops=laptop_results, students=student_results, q=q)


# -------------------------
# Sign in / Sign out
# -------------------------
@app.route('/search_student')
def search_student():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify([])
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    likeq = f"%{q}%"
    cur.execute("""
        SELECT id, studentID AS student_id, name, phone
        FROM students
        WHERE name LIKE %s OR phone LIKE %s OR studentID LIKE %s
        ORDER BY name
        LIMIT 20
    """, (likeq, likeq, likeq))
    rows = cur.fetchall()
    conn.close()
    # normalize: ensure keys match what the frontend expects
    out = []
    for r in rows:
        out.append({
            'id': r.get('id'),
            'student_id': r.get('student_id'),
            'name': r.get('name'),
            'phone': r.get('phone')
        })
    return jsonify(out)

# -------------------------
# Sign in / Sign out
# -------------------------
@app.route('/sign_action', methods=['POST'])
def sign_action():
    if not require_login():
        return redirect(url_for('login'))
    rec_id = request.form.get('id')
    action = request.form.get('action')
    if not rec_id or action not in ('signin', 'signout'):
        flash("Invalid request.")
        return redirect(request.referrer or url_for('home'))

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, signed_in, serial_number FROM laptops WHERE id=%s", (rec_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        flash("Record not found.")
        return redirect(request.referrer or url_for('home'))

    if action == 'signin' and row['signed_in']:
        conn.close()
        flash("Already signed in.")
        return redirect(request.referrer or url_for('home'))
    if action == 'signout' and not row['signed_in']:
        conn.close()
        flash("Already signed out.")
        return redirect(request.referrer or url_for('home'))

    try:
        new_state = 1 if action == 'signin' else 0
        cur2 = conn.cursor()
        cur2.execute("UPDATE laptops SET signed_in=%s WHERE id=%s", (new_state, rec_id))
        cur2.execute("INSERT INTO logs (device_id, action, gate_id, meta) VALUES (%s,%s,%s,%s)",
                     (row['serial_number'], action, None, f"by:{current_user().get('staffID') or current_user().get('id')}"))
        conn.commit()

        # ✅ Always redirect — never return JSON
        flash(f"Laptop {action} successful.")
        return redirect(request.referrer or url_for('laptops_page'))

    except Exception as e:
        conn.rollback()
        flash("DB error: " + str(e))
        return redirect(request.referrer or url_for('home'))
    finally:
        conn.close()



# -------------------------
# Reports
# -------------------------
@app.route('/reports')
def reports():
    if not require_login():
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM logs ORDER BY ts DESC LIMIT 500")
    logs = cur.fetchall()
    conn.close()
    return render_template('reports.html', logs=logs)

@app.route('/reports/export')
def export_logs():
    if not require_admin():
        return redirect(url_for('reports'))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, device_id, action, gate_id, meta, ts FROM logs ORDER BY ts DESC")
    rows = cur.fetchall()
    conn.close()
    mem = io.StringIO()
    mem.write("id,device_id,action,gate_id,meta,ts\n")
    for r in rows:
        line = ",".join(['"{}"'.format(str(x).replace('"','""')) if x is not None else '""' for x in r])
        mem.write(line + "\n")
    mem.seek(0)
    return send_file(io.BytesIO(mem.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='logs.csv')





# -------------------------
# Run
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)
