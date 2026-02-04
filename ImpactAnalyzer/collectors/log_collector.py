import paramiko
import os
import datetime

class LogCollector:
    def __init__(self, config):
        self.config = config
        self.host = config['host']
        self.user = config['user']
        self.key_path = config.get('ssh_key_path')
        self.log_path = config['log_path']
        
    def collect(self, start_time, end_time, output_dir):
        """Collects logs for the given time window."""
        print(f"[*] Connecting to {self.host} to fetch logs...")
        
        # Format time for grep/sed (assuming ISO format in logs like 2026-02-05 10:00)
        # You might need to adjust this format based on your actual log4j pattern
        s_str = start_time.strftime("%Y-%m-%d %H:%M")
        e_str = end_time.strftime("%Y-%m-%d %H:%M")
        
        # Command to extract logs between timestamps
        # sed -n '/START/,/END/p' filename
        cmd = f"sed -n '/{s_str}/,/{e_str}/p' {self.log_path}"
        
        local_filename = os.path.join(output_dir, f"server_{self.host}.log")
        
        try:
            # Check if host is localhost (simple check)
            if self.host in ["localhost", "127.0.0.1"] or os.name == 'posix': 
                # Local Execution logic could be added here
                # But typically this tool runs on Windows Client -> Unix Server
                self._ssh_collect(cmd, local_filename)
            else:
                 self._ssh_collect(cmd, local_filename)
                 
            print(f"[+] Logs saved to {local_filename}")
            return local_filename
            
        except Exception as e:
            print(f"[-] Error collecting logs: {e}")
            return None

    def _ssh_collect(self, cmd, local_filename):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        password = self.config.get('password')
        
        if self.key_path and os.path.exists(self.key_path):
            key = paramiko.RSAKey.from_private_key_file(self.key_path)
            client.connect(hostname=self.host, username=self.user, pkey=key)
        elif password:
            client.connect(hostname=self.host, username=self.user, password=password)
        else:
            raise ValueError("No valid SSH authentication method found (key_path or password required).")
        
        stdin, stdout, stderr = client.exec_command(cmd)
        
        with open(local_filename, "w", encoding='utf-8') as f:
            for line in stdout:
                f.write(line)
                
        client.close()
