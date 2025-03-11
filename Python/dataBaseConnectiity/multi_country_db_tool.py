import cx_Oracle
import configparser
import pandas as pd
import os

CONFIG_FILE = "databases.ini"
QUERIES_FILE = "queries.ini"

# Load database configurations
config = configparser.ConfigParser()
config.read(CONFIG_FILE)
DATABASES = {section: dict(config[section]) for section in config.sections() if section.startswith("database_")}

# Load predefined queries
queries_config = configparser.ConfigParser()
queries_config.read(QUERIES_FILE)
QUERIES = {section: dict(queries_config[section]) for section in queries_config.sections()}

current_db = None


def connect_to_database(db_config):
    """Establish connection to the Oracle database."""
    try:
        dsn = cx_Oracle.makedsn(db_config["host"], db_config["port"], service_name=db_config["service_name"])
        connection = cx_Oracle.connect(user=db_config["username"], password=db_config["password"], dsn=dsn)
        return connection
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None


def handle_clob_blob(row):
    """Convert CLOB and BLOB data into readable format."""
    new_row = []
    for col in row:
        if isinstance(col, cx_Oracle.LOB):
            new_row.append(col.read())  # Convert LOB to readable text
        else:
            new_row.append(col)
    return new_row


def execute_query(db_config, query, export_csv=False):
    """Execute a SQL query and display results in a formatted table."""
    connection = connect_to_database(db_config)
    if not connection:
        return

    try:
        cursor = connection.cursor()
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        rows = [handle_clob_blob(row) for row in cursor.fetchall()]

        # Display results in a formatted table
        df = pd.DataFrame(rows, columns=columns)
        print(df.to_string(index=False))

        # Export to CSV if required
        if export_csv:
            csv_file = "query_results.csv"
            df.to_csv(csv_file, index=False)
            print(f"✅ Results exported to {csv_file}")

    except Exception as e:
        print(f"❌ Query execution failed: {e}")

    finally:
        cursor.close()
        connection.close()


def main():
    """Main function to handle user interaction."""
    global current_db

    print("\n🗄️ Multi-Country Database Tool (SG, MY, OV, HK, ID, TH, CN)\n")
    print("Available databases:", ", ".join(DATABASES.keys()))

    while True:
        cmd = input("\nEnter command ('switch <country>', 'run <query_name>', 'export <query_name>', 'exit'): ").strip().lower()

        if cmd == "exit":
            print("Exiting...")
            break

        elif cmd.startswith("switch "):
            country = cmd.split(" ")[1]
            if country in DATABASES:
                current_db = country
                print(f"✅ Switched to {current_db.upper()} database: {DATABASES[current_db]['host']}")
            else:
                print(f"❌ Invalid country! Available: {', '.join(DATABASES.keys())}")

        elif cmd.startswith("run "):
            if not current_db:
                print("⚠️ No database selected! Use 'switch <country>' first.")
                continue

            query_name = cmd[len("run "):]
            if query_name in QUERIES:
                sql_query = QUERIES[query_name]["query"]
                execute_query(DATABASES[current_db], sql_query)
            else:
                print(f"⚠️ Query '{query_name}' not found in {QUERIES_FILE}!")

        elif cmd.startswith("export "):
            if not current_db:
                print("⚠️ No database selected! Use 'switch <country>' first.")
                continue

            query_name = cmd[len("export "):]
            if query_name in QUERIES:
                sql_query = QUERIES[query_name]["query"]
                execute_query(DATABASES[current_db], sql_query, export_csv=True)
            else:
                print(f"⚠️ Query '{query_name}' not found in {QUERIES_FILE}!")

        else:
            print("⚠️ Invalid command! Use 'switch <country>', 'run <query_name>', 'export <query_name>', 'exit'.")


if __name__ == "__main__":
    main()
