import pandas as pd

# Sample DataFrames
data1 = {'ID': [1, 2, 3, 4, 5], 'Value': ['A', 'B', 'C', 'D', 'E']}
data2 = {'ID': [4, 5, 6, 7, 8], 'Value': ['D', 'E', 'F', 'G', 'H']}

df1 = pd.DataFrame(data1)
df2 = pd.DataFrame(data2)

# Convert to set for comparison
set_df1 = set(df1['ID'])
set_df2 = set(df2['ID'])

# Elements in df1 but not in df2
only_in_df1 = set_df1 - set_df2

# Elements in df2 but not in df1
only_in_df2 = set_df2 - set_df1

# Elements in both df1 and df2
common_elements = set_df1 & set_df2

# Create DataFrames to display the results
df_only_in_df1 = df1[df1['ID'].isin(only_in_df1)]
df_only_in_df2 = df2[df2['ID'].isin(only_in_df2)]
df_common_elements = df1[df1['ID'].isin(common_elements)]

# Display Results
print("Elements in df1 but not in df2:")
print(df_only_in_df1)
print("\nElements in df2 but not in df1:")
print(df_only_in_df2)
print("\nElements common to both df1 and df2:")
print(df_common_elements)
