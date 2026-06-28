import sqlite3

db = r"C:\Users\84337\.gemini\antigravity-ide\conversations\0e81af1e-56f1-4650-b2fc-48dd48f72504.db"

conn = sqlite3.connect(db)

blob = conn.execute("""
SELECT step_payload
FROM steps
WHERE step_payload IS NOT NULL
ORDER BY idx DESC
LIMIT 1
""").fetchone()[0]

print(type(blob))
print("Length:", len(blob))
print("First 100 bytes:")
print(blob[:100])
try:
    print(blob.decode("utf-8")[:1000])
except Exception as e:
    print("decode failed:", e)