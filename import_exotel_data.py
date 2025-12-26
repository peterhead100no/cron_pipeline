import json
import os
from dotenv import load_dotenv
import psycopg2
from database import get_db_connection

# Load environment variables
load_dotenv()

# Read call_details.json
with open('call_details.json', 'r') as f:
    data = json.load(f)

calls = data.get('calls', [])


# Create new PostgreSQL table if not exists
conn = get_db_connection()
if conn is None:
    print('Failed to connect to PostgreSQL database.')
    exit(1)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS exotel_data (
        Sid TEXT PRIMARY KEY,
        "To" TEXT,
        "From" TEXT,
        Status TEXT,
        Duration TEXT,
        RecordingUrl TEXT,
        StartTime TEXT,
        EndTime TEXT
    )
''')

# Insert call details

for call in calls:
    values = (
        call.get('Sid'),
        call.get('To'),
        call.get('From'),
        call.get('Status'),
        call.get('Duration'),
        call.get('RecordingUrl'),
        call.get('StartTime'),
        call.get('EndTime')
    )
    cursor.execute('''
        INSERT INTO exotel_data (Sid, "To", "From", Status, Duration, RecordingUrl, StartTime, EndTime)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (Sid) DO NOTHING
    ''', values)

conn.commit()
cursor.close()
conn.close()
print('Data inserted into exotel_data table in PostgreSQL database')
