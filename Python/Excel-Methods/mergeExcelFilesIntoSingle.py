
import os
import pandas as pd

# Specify the folder containing the Excel files
folder_path = '/Users/yaswitha/Documents/IBKRInverstment'

# List all Excel files in the folder
excel_files = [file for file in os.listdir(folder_path) if file.endswith('.xls')]

# Create an empty list to store the dataframes
dataframes = []

# Iterate over all Excel files and add their content to the list
for file in excel_files:
    file_path = os.path.join(folder_path, file)
    data = pd.read_excel(file_path, engine='xlrd')
    dataframes.append(data)

# Concatenate all dataframes into a single dataframe
merged_data = pd.concat(dataframes, ignore_index=True)

# Specify the output file path
output_file_path = 'merged_file.xlsx'

# Write the merged data to an Excel file
merged_data.to_excel(output_file_path, index=False, engine='openpyxl')

print(f'Merged {len(excel_files)} files into {output_file_path}')
