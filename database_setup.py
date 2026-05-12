"""
CerviScan — SQLite Database Setup & CRUD Helpers
------------------------------------------------
Run ONCE to create tables and seed default admin:
    python database_setup.py

Then import helpers into your Streamlit pages:
    from database_setup import authenticate_admin, save_patient, ...
"""

import sqlite3
import hashlib
import os
from datetime import datetime

# Path to the SQLite database file (created in the same folder as this script)
DB_PATH = "cervican.db"


# ─────────────────────────────────────────────────────────────────────────────
#  CONNECTION
# ─────────────────────────────────────────────────────────────────────────────

def get_connection():
    """Open and return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row           # access columns by name
    conn.execute("PRAGMA foreign_keys = ON") # enforce foreign key constraints
    return conn


# ─────────────────────────────────────────────────────────────────────────────
#  CREATE TABLES
# ─────────────────────────────────────────────────────────────────────────────

def create_tables():
    conn = get_connection()
    cur  = conn.cursor()

    # ── 1. ADMINS ─────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_uid     TEXT    NOT NULL UNIQUE,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            role          TEXT    NOT NULL DEFAULT 'admin',
            created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # ── 2. PATIENTS ───────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name        TEXT    NOT NULL,
            age              INTEGER NOT NULL CHECK(age >= 10 AND age <= 120),
            phone            TEXT    NOT NULL UNIQUE,
            emergency_phone  TEXT    NOT NULL,
            email            TEXT,
            image_filename   TEXT,
            recorded_by      TEXT    NOT NULL,
            recorded_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (recorded_by) REFERENCES admins(username)
        )
    """)

    # ── 3. PREDICTIONS ────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id       INTEGER NOT NULL,
            risk_label       TEXT    NOT NULL CHECK(risk_label IN ('Low Risk','Medium Risk','High Risk')),
            confidence_score REAL    NOT NULL,
            score_low        REAL,
            score_medium     REAL,
            score_high       REAL,
            model_version    TEXT    DEFAULT 'v1.0',
            analysed_by      TEXT    NOT NULL,
            analysed_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (patient_id)  REFERENCES patients(id),
            FOREIGN KEY (analysed_by) REFERENCES admins(username)
        )
    """)

    # ── 4. REPORTS ────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id       INTEGER NOT NULL,
            prediction_id    INTEGER NOT NULL,
            pdf_filename     TEXT,
            sent_to_email    TEXT,
            sent_at          TEXT,
            generated_by     TEXT    NOT NULL,
            generated_at     TEXT    NOT NULL DEFAULT (datetime('now')),
            notes            TEXT,
            FOREIGN KEY (patient_id)    REFERENCES patients(id),
            FOREIGN KEY (prediction_id) REFERENCES predictions(id),
            FOREIGN KEY (generated_by)  REFERENCES admins(username)
        )
    """)

    conn.commit()
    conn.close()
    print("✅  All tables created successfully.")


# ─────────────────────────────────────────────────────────────────────────────
#  SEED DEFAULT ADMIN
# ─────────────────────────────────────────────────────────────────────────────

def seed_default_admin():
    """Insert default admin account if it does not already exist."""
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("SELECT id FROM admins WHERE username = 'admin'")
    if cur.fetchone() is None:
        pw_hash = hashlib.sha256("admin123".encode()).hexdigest()
        cur.execute("""
            INSERT INTO admins (admin_uid, username, password_hash, role)
            VALUES (?, ?, ?, ?)
        """, ("ADM-0001", "admin", pw_hash, "admin"))
        conn.commit()
        print("✅  Default admin created  →  username: admin  |  password: admin123")
    else:
        print("ℹ️   Default admin already exists — skipping.")

    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  ADMIN HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def admin_exists(username: str) -> bool:
    """Return True if a username exists in the admins table."""
    conn = get_connection()
    row  = conn.execute(
        "SELECT id FROM admins WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return row is not None


def authenticate_admin(username: str, password: str) -> bool:
    """Return True if username + password match a record in the database."""
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    conn    = get_connection()
    row     = conn.execute(
        "SELECT id FROM admins WHERE username = ? AND password_hash = ?",
        (username, pw_hash)
    ).fetchone()
    conn.close()
    return row is not None


def register_admin(username: str, password: str):
    """
    Register a new admin account.
    Returns (True, admin_uid) on success or (False, error_message) on failure.
    """
    if admin_exists(username):
        return False, "Username already exists. Please choose a different one."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."

    conn  = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
    uid   = "ADM-{:04d}".format(count + 1)
    pw_hash = hashlib.sha256(password.encode()).hexdigest()

    conn.execute(
        "INSERT INTO admins (admin_uid, username, password_hash, role) VALUES (?,?,?,?)",
        (uid, username, pw_hash, "admin")
    )
    conn.commit()
    conn.close()
    return True, uid


def get_all_admins():
    """Return a list of all admin accounts (excluding password hashes)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, admin_uid, username, role, created_at FROM admins ORDER BY created_at"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
#  PATIENT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def save_patient(data: dict) -> int:
    """
    Insert a new patient or update an existing one matched by phone number.
    Returns the patient's database ID (integer).

    Required keys in data:
        name, age, phone, emergency_phone, recorded_by
    Optional keys:
        email, image_filename
    """
    conn     = get_connection()
    existing = conn.execute(
        "SELECT id FROM patients WHERE phone = ?", (data["phone"],)
    ).fetchone()

    if existing:
        patient_id = existing["id"]
        conn.execute("""
            UPDATE patients
            SET full_name        = ?,
                age              = ?,
                emergency_phone  = ?,
                email            = ?,
                image_filename   = ?,
                recorded_by      = ?,
                recorded_at      = datetime('now')
            WHERE id = ?
        """, (
            data["name"],
            data["age"],
            data["emergency_phone"],
            data.get("email", ""),
            data.get("image_filename", ""),
            data["recorded_by"],
            patient_id
        ))
    else:
        cur = conn.execute("""
            INSERT INTO patients
                (full_name, age, phone, emergency_phone, email, image_filename, recorded_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data["name"],
            data["age"],
            data["phone"],
            data["emergency_phone"],
            data.get("email", ""),
            data.get("image_filename", ""),
            data["recorded_by"]
        ))
        patient_id = cur.lastrowid

    conn.commit()
    conn.close()
    return patient_id


def get_patient_by_id(patient_id: int):
    """Return a single patient record by ID, or None if not found."""
    conn = get_connection()
    row  = conn.execute(
        "SELECT * FROM patients WHERE id = ?", (patient_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_patient_by_phone(phone: str):
    """Return a single patient record by phone number, or None if not found."""
    conn = get_connection()
    row  = conn.execute(
        "SELECT * FROM patients WHERE phone = ?", (phone,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_patients():
    """Return all patient records ordered by most recent first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM patients ORDER BY recorded_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_patient(patient_id: int) -> bool:
    """
    Delete a patient and all their related predictions and reports.
    Returns True if deleted successfully, False otherwise.
    """
    try:
        conn = get_connection()
        # Delete related reports first (foreign key)
        conn.execute("DELETE FROM reports WHERE patient_id = ?", (patient_id,))
        # Delete related predictions
        conn.execute("DELETE FROM predictions WHERE patient_id = ?", (patient_id,))
        # Delete patient
        conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  PREDICTION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def save_prediction(patient_id: int, result: dict, admin_username: str) -> int:
    """
    Save an AI prediction result to the database.
    Returns the prediction's database ID (integer).

    result dict must contain:
        label      — e.g. "High Risk"
        confidence — e.g. 87.5
        scores     — dict with keys "Low Risk", "Medium Risk", "High Risk"
    """
    conn = get_connection()
    cur  = conn.execute("""
        INSERT INTO predictions
            (patient_id, risk_label, confidence_score,
             score_low, score_medium, score_high, analysed_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        patient_id,
        result["label"],
        result["confidence"],
        result["scores"].get("Low Risk",    0.0),
        result["scores"].get("Medium Risk", 0.0),
        result["scores"].get("High Risk",   0.0),
        admin_username
    ))
    pred_id = cur.lastrowid
    conn.commit()
    conn.close()
    return pred_id


def get_latest_prediction(patient_id: int):
    """Return the most recent prediction for a given patient, or None."""
    conn = get_connection()
    row  = conn.execute("""
        SELECT * FROM predictions
        WHERE patient_id = ?
        ORDER BY analysed_at DESC
        LIMIT 1
    """, (patient_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_predictions():
    """Return all predictions joined with patient name and phone."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT pr.*, pt.full_name, pt.phone
        FROM   predictions pr
        JOIN   patients    pt ON pr.patient_id = pt.id
        ORDER  BY pr.analysed_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
#  REPORT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def save_report(
    patient_id: int,
    prediction_id: int,
    admin_username: str,
    sent_to: str = "",
    pdf_filename: str = "",
    notes: str = ""
) -> int:
    """
    Log a generated/sent report to the database.
    Returns the report's database ID (integer).
    """
    conn = get_connection()
    cur  = conn.execute("""
        INSERT INTO reports
            (patient_id, prediction_id, pdf_filename,
             sent_to_email, sent_at, generated_by, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        patient_id,
        prediction_id,
        pdf_filename,
        sent_to,
        datetime.now().isoformat() if sent_to else None,
        admin_username,
        notes
    ))
    report_id = cur.lastrowid
    conn.commit()
    conn.close()
    return report_id


def get_reports_for_patient(patient_id: int):
    """Return all reports for a specific patient."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT r.*, p.risk_label, p.confidence_score
        FROM   reports     r
        JOIN   predictions p ON r.prediction_id = p.id
        WHERE  r.patient_id = ?
        ORDER  BY r.generated_at DESC
    """, (patient_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_reports():
    """Return all reports joined with patient and prediction details."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT r.*, pt.full_name, pt.phone, pr.risk_label, pr.confidence_score
        FROM   reports     r
        JOIN   patients    pt ON r.patient_id    = pt.id
        JOIN   predictions pr ON r.prediction_id = pr.id
        ORDER  BY r.generated_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
#  RUN DIRECTLY TO INITIALISE DATABASE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🌸  CerviScan — Database Initialisation")
    print("=" * 45)
    print(f"📁  Database: {os.path.abspath(DB_PATH)}\n")
    create_tables()
    seed_default_admin()
    print("\n" + "=" * 45)
    print("✅  Setup complete! Now run:  streamlit run app.py")
    print("=" * 45 + "\n")
