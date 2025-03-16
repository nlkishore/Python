import configparser
import cx_Oracle
from datetime import datetime, timedelta

def get_db_connection(db_details):
    dsn_tns = cx_Oracle.makedsn(db_details['host'], db_details['port'], service_name=db_details['service_name'])
    connection = cx_Oracle.connect(user=db_details['user'], password=db_details['password'], dsn=dsn_tns)
    return connection

def execute_query(connection, query):
    cursor = connection.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    return result

def read_ini_file(file_path):
    config = configparser.ConfigParser()
    config.read(file_path)
    return config

def main():
    ini_file_path = 'config.ini'
    config = read_ini_file(ini_file_path)
    
    for country in config.sections():
        db_details = {
            'host': config[country]['host'],
            'port': config[country]['port'],
            'service_name': config[country]['service_name'],
            'user': config[country]['user'],
            'password': config[country]['password']
        }
        
        query = config[country]['query']
        
        try:
            connection = get_db_connection(db_details)
            results = execute_query(connection, query)
            print(f"Results for {country}:")
            for row in results:
                print(row)
            connection.close()
        except cx_Oracle.DatabaseError as e:
            print(f"Error connecting to database for {country}: {e}")
        
if __name__ == "__main__":
    main()
