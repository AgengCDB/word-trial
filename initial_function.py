import os
import sqlite3

def init_db():
    os.makedirs("data", exist_ok=True)  # make sure folder exists
    conn = sqlite3.connect("data/data.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "runs" (
            "id"	            INTEGER UNIQUE,
            "turn_count"	    INTEGER,
            "total_plus_score"	INTEGER,
            "total_minus_score"	INTEGER,
            PRIMARY KEY("id" AUTOINCREMENT)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "saves" (
            "id"	        INTEGER UNIQUE,
            "run_id"	    INTEGER UNIQUE,
            "last_saved"	TEXT,
            PRIMARY KEY("id" AUTOINCREMENT),
            FOREIGN KEY("run_id") REFERENCES "runs"("id")
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "turns" (
            "run_id"	    INTEGER,
            "id"            INTEGER,
            "word_to_match"	TEXT,
            "user_input"	TEXT,
            "plus_score"	INTEGER,
            "minus_score"	INTEGER,
            FOREIGN KEY("run_id") REFERENCES "runs"("id")
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "scores" (
            "run_id"	        INTEGER,
            "total_word"	    INTEGER,
            "total_letter"	    INTEGER,
            "total_plus_score"	INTEGER,
            "total_minus_score"	INTEGER,
            "total_score"	    INTEGER, 
            "run_finished"	    TEXT
        );
    """)


    
    
    # Initialize 10 rows in saves if table is empty
    cursor.execute("SELECT COUNT(*) FROM saves")
    count = cursor.fetchone()[0]
    if count < 10:
        for _ in range(10 - count):
            cursor.execute("INSERT INTO saves (run_id) VALUES (NULL)")

    conn.commit()
    conn.close()

def conn_db():
    conn = sqlite3.connect("data/data.db")
    return conn

if __name__ == "__main__":
    # Directory of this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(current_dir)
    print(sqlite3.sqlite_version)