import re
from collections import deque

def extract_exceptions(log_file_path, output_file_path, lines_before=3, lines_after=3):
    try:
        with open(log_file_path, 'r', encoding='utf-8') as file:
            log_lines = file.readlines()
        
        pattern = re.compile(r'Exception|Error')  # Adjust this pattern to match the exceptions in your log file
        
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            buffer = deque(maxlen=lines_before)
            after_count = 0
            
            for line in log_lines:
                if pattern.search(line):
                    # Write buffered lines before the exception
                    output_file.writelines(buffer)
                    # Write the exception line
                    output_file.write(line)
                    after_count = lines_after  # Initialize counter for lines after the exception
                elif after_count > 0:
                    # Write lines after the exception
                    output_file.write(line)
                    after_count -= 1
                buffer.append(line)
        
        print(f"Extracted exceptions have been saved to {output_file_path}")
    
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except OSError as e:
        print(f"OSError: {e}")
    except UnicodeDecodeError as e:
        print(f"UnicodeDecodeError: {e}")

if __name__ == "__main__":
    log_file_path = 'logfile.log'
    output_file_path = 'extracted_exceptions.txt'
    extract_exceptions(log_file_path, output_file_path)
