import re

def parse_diff(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
        
    added_lines = []
    removed_lines = []
    current_file = None

    for line in lines:
        if line.startswith('diff --git'):
            match = re.search(r'diff --git a/(.+?) b/', line)
            if match:
                current_file = match.group(1)
        elif line.startswith('@@ '):
            continue
        elif line.startswith('+') and not line.startswith('+++'):
            added_lines.append((current_file, line[1:].strip()))
        elif line.startswith('-') and not line.startswith('---'):
            removed_lines.append((current_file, line[1:].strip()))

    return added_lines, removed_lines

added, removed = parse_diff('diff_output.txt')

with open('summary.txt', 'w') as summary_file:
    summary_file.write('Added Lines:\n')
    for file, line in added:
        summary_file.write(f'{file}: {line}\n')

    summary_file.write('\nRemoved Lines:\n')
    for file, line in removed:
        summary_file.write(f'{file}: {line}\n')

print('Summary of added and removed lines has been written to summary.txt')
