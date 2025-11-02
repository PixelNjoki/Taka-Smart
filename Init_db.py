import sqlite3

# Connect to (or create) the database file
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Create users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
''')

# Create reports table
cursor.execute('''
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    description TEXT NOT NULL,
    image_path TEXT,
    status TEXT DEFAULT 'Pending'
)
''')

print("✅ Database and tables created successfully!")

conn.commit()
conn.close()
