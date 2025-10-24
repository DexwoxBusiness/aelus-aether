import psycopg2

# Test with 127.0.0.1 (IPv4) to template1
try:
    conn = psycopg2.connect(
        host="127.0.0.1", port=5433, user="aelus", password="aelus_password", database="template1"
    )
    print("✅ psycopg2 connected to template1 with 127.0.0.1!")
    conn.close()
except Exception as e:
    print(f"❌ psycopg2 connection to template1 with 127.0.0.1 failed: {e}")
