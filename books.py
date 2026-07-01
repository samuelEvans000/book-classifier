import os
import math
import pymysql
import pandas as pd

# Database configuration
conn = pymysql.connect(
    host="127.0.0.1",
    port=3307,
    user="root",
    password="root",  
    database="libgen",
    charset="utf8mb4"
)

OUTPUT_DIR = "english_books_csv"
CHUNK_SIZE = 5000

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Get total rows
with conn.cursor() as cursor:
    cursor.execute("SELECT COUNT(*) FROM english_books")
    total_rows = cursor.fetchone()[0]

total_files = math.ceil(total_rows / CHUNK_SIZE)

print(f"Total rows: {total_rows}")
print(f"Generating {total_files} CSV files...")

for i in range(total_files):
    offset = i * CHUNK_SIZE

    query = f"""
    SELECT
        MD5,
        Title,
        Author
    FROM english_books
    LIMIT {CHUNK_SIZE} OFFSET {offset}
    """

    df = pd.read_sql(query, conn)

    filename = os.path.join(
        OUTPUT_DIR,
        f"books_{i+1:04d}.csv"
    )

    df.to_csv(filename, index=False)

    print(f"Saved {filename} ({len(df)} rows)")

conn.close()

print("Done!")