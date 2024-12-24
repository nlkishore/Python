import pandas as pd

# Specify the path to your Excel file
file_path = '/Users/yaswitha/Documents/IBKRInverstment/Deposit_Yearly/merged_excel_file.xlsx'

# Read all sheets into a dictionary of DataFrames
sheets_dict = pd.read_excel(file_path, sheet_name=None)

# List to store all data frames
dataframes = []

# Iterate over the sheets and store them into the list
for sheet_name, df in sheets_dict.items():
    dataframes.append(df)

# Example condition: Merge data frames based on a specific column value
# Let's assume we want to merge on the 'ID' column and the condition is to match 'ID' values
merged_df = pd.concat(dataframes, ignore_index=True)

# Example: Filter the merged data frame based on a condition
# Let's assume we only want rows where 'ID' is greater than a specific value (e.g., 100)
filtered_df = merged_df[merged_df['Statement'] == 'Statement of Funds']

# Save the filtered merged data frame to a new Excel file
output_file_path = '/Users/yaswitha/Documents/IBKRInverstment/Deposit_Yearly/filtered_merged_file.xlsx'
filtered_df.to_excel(output_file_path, index=False)

print(f'Merged and filtered data saved to {output_file_path}')
