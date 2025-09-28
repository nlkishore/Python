import mysql.connector

print("Validating database schema...")
def validate_schema(host, port, user, password, database):
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        print("after conn object...")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_NAME, ORDINAL_POSITION
        """, (database,))
        print("after conn object1...")
        current_table = None
        for table, column, dtype in cursor.fetchall():
            if table != current_table:
                print(f"\n📁 Table: {table}")
                current_table = table
            print(f"   - {column}: {dtype}")
        
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"❌ Error: {err}")

# Example usage
validate_schema(
    host="127.0.0.1",
    port=3306,
    user="kishore",
    password="Kish1381@",
    database="helloworld"
)