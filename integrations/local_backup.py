# integrations/local_backup.py
import os
import subprocess
from datetime import datetime

# Config — change these if needed
MYSQLDUMP_PATH = os.getenv('MYSQLDUMP_PATH', r"C:\xampp\mysql\bin\mysqldump.exe")
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DB = os.getenv('MYSQL_DB', 'school_laptops')
BACKUP_DIR = os.getenv('BACKUP_DIR', 'backups')

def ensure_backup_dir():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

def create_local_backup():
    ensure_backup_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{MYSQL_DB}_dump_{ts}.sql"
    out_path = os.path.join(BACKUP_DIR, filename)

    if not os.path.exists(MYSQLDUMP_PATH):
        # If mysqldump not available, raise
        raise FileNotFoundError(f"mysqldump not found at {MYSQLDUMP_PATH}")

    cmd = [
        MYSQLDUMP_PATH,
        "-h", MYSQL_HOST,
        "-u", MYSQL_USER,
        f"-p{MYSQL_PASSWORD}",
        MYSQL_DB
    ]
    with open(out_path, "wb") as f:
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.PIPE)
        _, err = p.communicate()
    if p.returncode != 0:
        # remove incomplete file
        try:
            os.remove(out_path)
        except Exception:
            pass
        raise RuntimeError(f"mysqldump failed: {err.decode(errors='ignore')}")
    return out_path
