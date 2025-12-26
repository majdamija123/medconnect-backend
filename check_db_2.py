
import sqlite3

try:
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(app_patientprofile)")
    columns = [row[1] for row in cursor.fetchall()]
    print("Columns in app_patientprofile:", columns)
    
    conn.close()
except Exception as e:
    print("Error:", e)
