import os
import subprocess
import configparser

def get_modified_files_between_dates(repo_path, branch, start_date, end_date):
    # Change directory to the repository path
    os.chdir(repo_path)
    
    # Checkout to the specified branch
    subprocess.run(['git', 'checkout', branch])
    
    # Get the list of modified files between two dates
    result = subprocess.run(['git', 'log', '--name-only', '--pretty=format:', '--since', start_date, '--until', end_date], stdout=subprocess.PIPE)
    modified_files = result.stdout.decode('utf-8').splitlines()
    
    # Filter out empty lines and duplicates
    modified_files = list(filter(None, modified_files))
    modified_files = list(set(modified_files))
    
    return modified_files

def create_java_project_structure(modified_files, output_directory):
    for file in modified_files:
        if file.endswith('.java'):
            # Split the file path to get the directory structure
            directories = file.split('/')[:-1]
            # Create the directory structure in the output directory
            os.makedirs(os.path.join(output_directory, *directories), exist_ok=True)
            # Create an empty Java file in the directory structure
            open(os.path.join(output_directory, file), 'a').close()

def read_config(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    
    repo_path = config['DEFAULT']['repo_path']
    branch = config['DEFAULT']['branch']
    start_date = config['DEFAULT']['start_date']
    end_date = config['DEFAULT']['end_date']
    output_directory = config['DEFAULT']['output_directory']
    
    return repo_path, branch, start_date, end_date, output_directory

# Example usage
config_file = 'config.ini'

# Create a sample INI file with inputs
config = configparser.ConfigParser()
config['DEFAULT'] = {
    'repo_path': '/path/to/your/bitbucket/repository',
    'branch': 'branch_name',
    'start_date': '2023-01-01',
    'end_date': '2023-12-31',
    'output_directory': '/path/to/output/directory'
}

with open(config_file, 'w') as configfile:
    config.write(configfile)

# Read inputs from INI file
repo_path, branch, start_date, end_date, output_directory = read_config(config_file)

# Get modified files and create Java project structure
modified_files = get_modified_files_between_dates(repo_path, branch, start_date, end_date)
create_java_project_structure(modified_files, output_directory)

print("Java project structure created for modified files.")
