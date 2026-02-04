import oracledb
import os

class DBAnalyzer:
    def __init__(self, config):
        self.config = config
        self.dsn = config['dsn']
        self.user = config['user']
        self.password = config.get('password') # In prod, use env var
        self.critical_tables = config.get('critical_tables', [])
        
    def analyze(self, start_time, end_time, output_dir):
        """Analyzes DB changes in the time window."""
        print(f"[*] Connecting to Oracle DB {self.dsn}...")
        
        report_file = os.path.join(output_dir, "db_impact_report.txt")
        
        try:
            # oracledb thin mode (no client needed) is default in new versions
            conn = oracledb.connect(user=self.user, password=self.password, dsn=self.dsn)
            cursor = conn.cursor()
            
            with open(report_file, "w") as f:
                f.write(f"Database Impact Analysis ({start_time} to {end_time})\n")
                f.write("="*50 + "\n\n")
                
                # 1. Check Schema Changes (DDL)
                f.write("1. Schema Changes (DDL):\n")
                sql_ddl = """
                    SELECT object_name, object_type, last_ddl_time 
                    FROM user_objects 
                    WHERE last_ddl_time >= :1 AND last_ddl_time <= :2
                """
                cursor.execute(sql_ddl, [start_time, end_time])
                rows = cursor.fetchall()
                if not rows:
                    f.write("   None.\n")
                for row in rows:
                    f.write(f"   {row[1]} {row[0]} modified at {row[2]}\n")
                
                f.write("\n")
                
                # 2. Check Data Changes (Row Updates)
                # Assumes tables have a MODIFIED_DATE column
                f.write("2. Data Changes (Critical Tables):\n")
                for table in self.critical_tables:
                    try:
                        # Dynamic query - careful with SQL injection if user input wasn't config based
                        # Using count for summary
                        sql_data = f"SELECT count(*) FROM {table} WHERE MODIFIED_DATE BETWEEN :1 AND :2"
                        cursor.execute(sql_data, [start_time, end_time])
                        count = cursor.fetchone()[0]
                        if count > 0:
                            f.write(f"   Table {table}: {count} rows modified.\n")
                    except oracledb.DatabaseError as e:
                        f.write(f"   Table {table}: Error checking (Missing column?): {e}\n")
                        
            conn.close()
            print(f"[+] DB Report saved to {report_file}")
            return report_file
            
        except Exception as e:
            print(f"[-] Error analyzing DB: {e}")
            return None
