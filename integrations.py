# integrations.py
import os, subprocess, io, json
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import mysql.connector

# ------- Config (move to env variables in production) -------
GDRIVE_SERVICE_ACCOUNT_FILE = os.getenv('GDRIVE_SERVICE_ACCOUNT_FILE', 'service-account.json')
GDRIVE_FOLDER_ID = os.getenv('GDRIVE_FOLDER_ID', None)  # optional: folder to upload in Drive
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DB = os.getenv('MYSQL_DB', 'school_laptops')

# ------- Google Drive helper -------
def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        GDRIVE_SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
    )
    service = build('drive', 'v3', credentials=creds)
    return service

def upload_bytes_to_drive(bytes_io, filename, mime_type='application/sql'):
    service = get_drive_service()
    file_metadata = {'name': filename}
    if GDRIVE_FOLDER_ID:
        file_metadata['parents'] = [GDRIVE_FOLDER_ID]
    media = MediaIoBaseUpload(bytes_io, mimetype=mime_type, resumable=True)
    uploaded = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return uploaded.get('id')

# ------- DB dump (mysqldump) -------
def create_mysql_dump():
    """
    Creates a mysqldump bytes buffer. Requires mysqldump available on the system.
    Returns io.BytesIO containing SQL dump.
    """
    dump_filename = f"dump_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.sql"
    cmd = [
        "mysqldump",
        "-h", MYSQL_HOST,
        "-u", MYSQL_USER,
        f"-p{MYSQL_PASSWORD}",
        MYSQL_DB
    ]
    # Execute and capture output
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(f"mysqldump failed: {err.decode()}")
    buf = io.BytesIO(out)
    buf.seek(0)
    return buf, dump_filename

# ------- Alternative: CSV export of logs (SQL-based) -------
def create_logs_csv():
    conn = mysql.connector.connect(host=MYSQL_HOST,user=MYSQL_USER,password=MYSQL_PASSWORD,database=MYSQL_DB)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT logs.id, logs.laptop_serial, l.make, l.model, s.studentID, s.name, logs.status, logs.timestamp
        FROM logs
        LEFT JOIN laptops l ON logs.laptop_serial = l.serial_number
        LEFT JOIN students s ON l.student_id = s.id
        ORDER BY logs.timestamp DESC
    """)
    rows = cursor.fetchall()
    header = ['id','laptop_serial','make','model','studentID','student_name','status','timestamp']
    import csv
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    b = io.BytesIO(buf.getvalue().encode())
    b.seek(0)
    filename = f"logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return b, filename

# ------- Upload dump to Drive (wrapper) -------
def backup_database_to_drive(use_csv=False):
    if use_csv:
        buf, filename = create_logs_csv()
        mime = 'text/csv'
    else:
        buf, filename = create_mysql_dump()
        mime = 'application/sql'
    file_id = upload_bytes_to_drive(buf, filename, mime_type=mime)
    return file_id