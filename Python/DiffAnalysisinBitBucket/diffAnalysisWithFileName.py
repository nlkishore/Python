import re

def parse_diff(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
        
    added_lines = []
    removed_lines = []
    current_file = None
    current_method = None

    method_pattern = re.compile(r'(public|private|protected|static|\s)+[a-zA-Z<>]+\s+\w+\(.*?\)\s*\{?')

    for line in lines:
        if line.startswith('diff --git'):
            match = re.search(r'diff --git a/(.+?) b/', line)
            if match:
                current_file = match.group(1)
        elif line.startswith('@@ '):
            continue
        elif line.startswith('+') and not line.startswith('+++'):
            method_name = find_method_name(lines, method_pattern, line)
            added_lines.append((current_file, method_name, line[1:].strip()))
        elif line.startswith('-') and not line.startswith('---'):
            method_name = find_method_name(lines, method_pattern, line)
            removed_lines.append((current_file, method_name, line[1:].strip()))

    return added_lines, removed_lines

def find_method_name(lines, method_pattern, current_line):
    for line in reversed(lines[:lines.index(current_line)]):
        if method_pattern.match(line):
            return line.strip()
    return 'Unknown Method'

added, removed = parse_diff('diff_output.txt')

with open('summary.txt', 'w') as summary_file:
    summary_file.write('Added Lines:\n')
    for file, method, line in added:
        summary_file.write(f'{file} - {method}: {line}\n')

    summary_file.write('\nRemoved Lines:\n')
    for file, method, line in removed:
        summary_file.write(f'{file} - {method}: {line}\n')

print('Summary of added and removed lines with method names has been written to summary.txt')
