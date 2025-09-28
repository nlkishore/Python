import os
def remove_comments(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as infile, open(output_path, 'w', encoding='utf-8') as outfile:
        for line in infile:
            stripped = line.strip()
            # Skip lines that are comments or empty
            if stripped.startswith('#') or stripped.startswith('--') or not stripped:
                continue
            outfile.write(line)

# Example usage
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, "TurbineResources.properties")
remove_comments(config_path, os.path.join(script_dir,'TurbineResources_clean.properties'))