
# Specify the folder containing the CSV files
folder_path = '/Users/yaswitha/Documents/IBKRInverstment/Deposit_Yearly'
import os
import pandas as pd
import io

# Specify the folder containing the CSV files
folder_path = '/Users/yaswitha/Documents/IBKRInverstment/Deposit_Yearly'

# List all CSV files in the folder
csv_files = [file for file in os.listdir(folder_path) if file.endswith('.csv')]

# Create an empty list to store the dataframes
dataframes = []

# Function to read CSV file while skipping bad lines
def read_csv_skip_bad_lines(file_path):
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            try:
                data.append(pd.read_csv(io.StringIO(line)))
            except pd.errors.ParserError:
                print(f"Skipping bad line in {file_path}: {line}")
    return pd.concat(data, ignore_index=True)

# Iterate over all CSV files and add their content to the list
for file in csv_files:
    file_path = os.path.join(folder_path, file)
    data = read_csv_skip_bad_lines(file_path)
    dataframes.append(data)

# Concatenate all dataframes into a single dataframe
merged_data = pd.concat(dataframes, ignore_index=True)

# Specify the output file path
output_file_path = '/Users/yaswitha/Documents/IBKRInverstment/Deposit_Yearly/TotalDeposits.csv'

# Write the merged data to a CSV file
merged_data.to_csv(output_file_path, index=False)

print(f'Merged {len(csv_files)} files into {output_file_path}')
