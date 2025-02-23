#Reads your Excel file.
#✅ Fixes typos in controller names.
#✅ Merges controllers under the same category in a single row.
#✅ Saves the modified data to a new Excel file.

import pandas as pd

# Load the Excel file
file_path = "your_file.xlsx"  # Update with your file path
df = pd.read_excel(file_path, header=None, names=["Category", "Controller"])

# Fix possible typos
df["Controller"] = df["Controller"].replace("RegustrationController.java", "RegistrationController.java")

# Group by Category and concatenate controller names
df_grouped = df.groupby("Category")["Controller"].apply(lambda x: ",".join(x)).reset_index()

# Save to a new Excel file
output_file = "modified_excel.xlsx"
df_grouped.to_excel(output_file, index=False)

print(f"Modified Excel file saved as {output_file}")
