import sqlite3


conn = sqlite3.connect("v2_points.db")
cursor = conn.cursor()

command = """CREATE TABLE points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_filename TEXT NOT NULL,
    frame_filename TEXT NOT NULL,
    process_datetime DATETIME NOT NULL,
    timestamp_ms INTEGER,
    abs_time DATETIME,
    width INTEGER,
    height INTEGER,
    fps REAL,
    lat REAL,
    lon REAL,
    analysis TEXT)"""
    
    
new_command = """CREATE TABLE items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_filename TEXT NOT NULL,
    process_datetime DATETIME NOT NULL,
    metadata TEXT,
    analysis TEXT
)
"""

cursor.execute(new_command)


