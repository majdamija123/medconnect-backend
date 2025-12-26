
import sqlite3

try:
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(app_medicaldocument)")
    columns = [row[1] for row in cursor.fetchall()]
    print("Columns in app_medicaldocument:", columns)
    
    if 'uploaded_by' in columns:
        print("uploaded_by exists")
    else:
        print("uploaded_by MISSING")
        
    conn.close()
except Exception as e:
    print("Error:", e)
