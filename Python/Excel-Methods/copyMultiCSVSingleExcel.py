import os
import pandas as pd
import csv

# Specify the folder containing the CSV files
folder_path = '/Users/yaswitha/Documents/IBKRInverstment/Deposit_Yearly'

# List all CSV files in the folder
csv_files = [file for file in os.listdir(folder_path) if file.endswith('.csv')]

# Create a Pandas Excel writer using openpyxl as the engine
output_file_path = '/Users/yaswitha/Documents/IBKRInverstment/Deposit_Yearly/merged_excel_file.xlsx'
writer = pd.ExcelWriter(output_file_path, engine='openpyxl')

# Function to read CSV file while handling inconsistent columns
def read_csv_with_consistent_columns(file_path):
    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        data = list(reader)
    
    # Find the maximum number of columns
    max_cols = max(len(row) for row in data)
    
    # Ensure all rows have the same number of columns
    for i in range(len(data)):
        if len(data[i]) < max_cols:
            data[i] += [''] * (max_cols - len(data[i]))  # Add empty strings to make columns consistent
    
    # Convert the list of rows into a DataFrame
    df = pd.DataFrame(data[1:], columns=data[0])  # Assuming the first row is the header
    return df

# Iterate over all CSV files and add each as a separate sheet in the Excel file
for file in csv_files:
    file_path = os.path.join(folder_path, file)
    data = read_csv_with_consistent_columns(file_path)
    sheet_name = os.path.splitext(file)[0]
    data.to_excel(writer, sheet_name=sheet_name, index=False)

# Save and close the Excel file
writer.close()

print(f'Copied {len(csv_files)} CSV files into {output_file_path}')
