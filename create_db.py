import sqlite3

# Specify the path where you want to create the database file
db_path = 'data/unavailabilities.db'

# Connect to the SQLite database (it will create the file if it doesn't exist)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    date TEXT,
    start_time TEXT,
    end_time TEXT,
    service TEXT,
    price INTEGER,
    UNIQUE(date, start_time)
)''')
cursor.execute('''
        CREATE TABLE IF NOT EXISTS unavailabilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            start_time TEXT,
            end_time TEXT
        )
    ''')

# Commit the changes and close the connection
conn.commit()
conn.close()

print(f"Database created successfully at {db_path}")
