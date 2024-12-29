import re
from datetime import datetime

def extract_log_details(log_file_path, output_file_path):
    try:
        with open(log_file_path, 'r', encoding='utf-8') as file:
            log_lines = file.readlines()
        
        # Define regular expression patterns
        timestamp_pattern = re.compile(r'^\[(.*?)\]')
        exception_pattern = re.compile(r'Exception|Error')
        stack_trace_pattern = re.compile(r'at\s+(.*?)\((.*?):(\d+)\)')

        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            current_timestamp = None
            for line in log_lines:
                # Extract timestamp
                timestamp_match = timestamp_pattern.search(line)
                if timestamp_match:
                    current_timestamp = timestamp_match.group(1)
                    try:
                        current_timestamp = datetime.strptime(current_timestamp, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        pass  # Handle other timestamp formats if necessary
                
                # Extract exceptions and stack trace details
                if exception_pattern.search(line):
                    output_file.write(f"Timestamp: {current_timestamp}\n")
                    output_file.write(f"Exception: {line.strip()}\n")
                
                stack_trace_match = stack_trace_pattern.search(line)
                if stack_trace_match:
                    class_name = stack_trace_match.group(1)
                    file_name = stack_trace_match.group(2)
                    line_number = stack_trace_match.group(3)
                    output_file.write(f"Class: {class_name}, File: {file_name}, Line: {line_number}\n")
                    output_file.write("\n")
        
        print(f"Extracted log details have been saved to {output_file_path}")
    
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except OSError as e:
        print(f"OSError: {e}")
    except UnicodeDecodeError as e:
        print(f"UnicodeDecodeError: {e}")

if __name__ == "__main__":
    log_file_path = 'logfile.log'
    output_file_path = 'extracted_log_details.txt'
    extract_log_details(log_file_path, output_file_path)
