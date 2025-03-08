import configparser
import cx_Oracle  # For Oracle databases
import psycopg2   # For PostgreSQL
import pymysql    # For MySQL/MariaDB
import sqlite3    # For SQLite
import pandas as pd
import os
import datetime

CONFIG_FILE = "databases.ini"
EXPORT_DIR = "query_results"

# Load database configurations
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

DB_SERVERS = {section: dict(config[section]) for section in config.sections() if section.startswith("db_")}
QUERIES = dict(config["Queries"]) if "Queries" in config else {}

# Ensure export directory exists
os.makedirs(EXPORT_DIR, exist_ok=True)

current_db = None


def connect_to_db(db_config):
    """Establish a database connection based on the database type."""
    db_type = db_config["type"].lower()

    try:
        if db_type == "oracle":
            dsn = cx_Oracle.makedsn(db_config["host"], db_config["port"], service_name=db_config["service"])
            connection = cx_Oracle.connect(db_config["username"], db_config["password"], dsn)
        elif db_type == "postgresql":
            connection = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["username"],
                password=db_config["password"]
            )
        elif db_type == "mysql":
            connection = pymysql.connect(
                host=db_config["host"],
                port=int(db_config["port"]),
                database=db_config["database"],
                user=db_config["username"],
                password=db_config["password"]
            )
        elif db_type == "sqlite":
            connection = sqlite3.connect(db_config["database"])
        else:
            print(f"❌ Unsupported database type: {db_type}")
            return None
        
        return connection
    except Exception as e:
        print(f"❌ Failed to connect to {db_config['database']} ({db_config['type']}): {e}")
        return None


def execute_query(db_config, query, export=False):
    """Execute a query, display results, and optionally export them to CSV."""
    connection = connect_to_db(db_config)
    if not connection:
        return

    try:
        cursor = connection.cursor()
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        # Convert CLOB/BLOB to readable format
        processed_rows = []
        for row in rows:
            processed_row = []
            for value in row:
                if isinstance(value, cx_Oracle.LOB):
                    processed_row.append(value.read())  # Read CLOB/BLOB
                else:
                    processed_row.append(value)
            processed_rows.append(processed_row)

        # Display results in formatted table
        df = pd.DataFrame(processed_rows, columns=columns)
        print(df.to_markdown(index=False))

        # Export results to CSV
        if export:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(EXPORT_DIR, f"{db_config['database']}_{timestamp}.csv")
            df.to_csv(filename, index=False)
            print(f"✅ Results exported to: {filename}")

    except Exception as e:
        print(f"❌ Error executing query: {e}")
    finally:
        cursor.close()
        connection.close()


def main():
    """Main function to handle user interaction."""
    global current_db

    print("\n🌍 Multi-Country Database Analysis Tool (with CSV Export)\n")
    print("Available markets:", ", ".join(DB_SERVERS.keys()))

    while True:
        cmd = input("\nEnter command (or 'switch <market>', 'run <query>', 'export <query>', 'exit'): ").strip().lower()

        if cmd == "exit":
            print("Exiting...")
            break

        elif cmd.startswith("switch "):
            market = cmd.split(" ")[1]
            if market in DB_SERVERS:
                current_db = DB_SERVERS[market]
                print(f"✅ Switched to {market.upper()} database: {current_db['database']} ({current_db['type']})")
            else:
                print(f"❌ Invalid market! Available: {', '.join(DB_SERVERS.keys())}")

        elif cmd.startswith("run "):
            query_name = cmd.split(" ")[1]
            query = QUERIES.get(query_name)
            if query:
                if current_db:
                    print(f"\nExecuting query '{query_name}' on {current_db['database']}...\n")
                    execute_query(current_db, query)
                else:
                    print("⚠️ No database selected! Use 'switch <market>' first.")
            else:
                print(f"❌ Query '{query_name}' not found in configuration.")

        elif cmd.startswith("export "):
            query_name = cmd.split(" ")[1]
            query = QUERIES.get(query_name)
            if query:
                if current_db:
                    print(f"\nExecuting query '{query_name}' and exporting results...\n")
                    execute_query(current_db, query, export=True)
                else:
                    print("⚠️ No database selected! Use 'switch <market>' first.")
            else:
                print(f"❌ Query '{query_name}' not found in configuration.")

        else:
            print("⚠️ Invalid command! Use 'switch <market>', 'run <query>', or 'export <query>'.")


if __name__ == "__main__":
    main()
