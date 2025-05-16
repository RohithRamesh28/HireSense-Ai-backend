import sqlite3
import os
from typing import Optional, Dict

DB_FILE = "resume_metadata.db"

# feilds of db 
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resumes (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            phone TEXT,
            resume_path TEXT,
            fingerprint TEXT UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

def add_resume_metadata(resume_id: str, metadata: Dict):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO resumes (id, name, email, phone, resume_path, fingerprint)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        resume_id,
        metadata.get("name"),
        metadata.get("email"),
        metadata.get("phone"),
        metadata.get("resume_path"),
        metadata.get("fingerprint")  #hasing is used here mdsha , when duplicates arise this will go cehck the entire db and upload if its not existeitng in db. 
    ))
    conn.commit()
    conn.close()

def get_resume_metadata(resume_id: str) -> Optional[Dict]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM resumes WHERE id = ?', (resume_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "phone": row[3],
            "resume_path": row[4],
            "fingerprint": row[5]
        }
    return None

def get_resume_by_fingerprint(fingerprint: str) -> Optional[Dict]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM resumes WHERE fingerprint = ?', (fingerprint,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "phone": row[3],
            "resume_path": row[4],
            "fingerprint": row[5]
        }
    return None
