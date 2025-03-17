import cx_Oracle

def search_data_in_tables(connection, search_value):
    cursor = connection.cursor()
    
    # Get all table names in the schema
    cursor.execute("""
        SELECT table_name
        FROM all_tables
        WHERE owner = :schema_name
    """, schema_name=connection.username.upper())
    
    tables = cursor.fetchall()
    
    tables_with_data = []
    records_with_data = {}
    
    for table in tables:
        table_name = table[0]
        
        # Get all column names for the table
        cursor.execute(f"""
            SELECT column_name
            FROM all_tab_columns
            WHERE table_name = :table_name
        """, table_name=table_name)
        
        columns = cursor.fetchall()
        
        for column in columns:
            column_name = column[0]
            
            # Search for the data in the column
            cursor.execute(f"""
                SELECT *
                FROM {table_name}
                WHERE {column_name} LIKE :search_value
            """, search_value=f'%{search_value}%')
            
            records = cursor.fetchall()
            
            if records:
                tables_with_data.append(table_name)
                if table_name not in records_with_data:
                    records_with_data[table_name] = []
                records_with_data[table_name].extend(records)
    
    return tables_with_data, records_with_data

# Example usage
dsn = cx_Oracle.makedsn('hostname', 'port', service_name='service_name')
connection = cx_Oracle.connect(user='username', password='password', dsn=dsn)

search_value = 'This is a sample sentence to search'
tables_with_data, records_with_data = search_data_in_tables(connection, search_value)

print("Tables containing the data:")
for table in tables_with_data:
    print(table)

print("\nRecords containing the data:")
for table, records in records_with_data.items():
    print(f"\nTable: {table}")
    for record in records:
        print(record)

connection.close()

