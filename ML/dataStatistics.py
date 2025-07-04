import pandas as pd

# Sample data
data = {
    'Name': ['Alice', 'Bob', 'Charlie', 'David', 'Emily'],
    'Age': [25, 30, 35, 40, 45],
    'Salary': [50000, 60000, 70000, 80000, 90000],
    'Department': ['HR', 'Finance', 'IT', 'HR', 'Finance']
}

# Creating a DataFrame
df = pd.DataFrame(data)

# Displaying the DataFrame
print("Original DataFrame:")
print(df)

# Manipulating data
# Adding a new column
df['Experience'] = [5, 8, 10, 12, 15]

# Changing values in a column
df.loc[df['Name'] == 'Bob', 'Salary'] = 65000

# Dropping a column
df.drop('Department', axis=1, inplace=True)

# Displaying the manipulated DataFrame
print("\nManipulated DataFrame:")
print(df)

# Deriving statistical information
# Summary statistics
summary_stats = df.describe()
print("\nSummary Statistics:")
print(summary_stats)

# Mean of Salary
mean_salary = df['Salary'].mean()
print("\nMean Salary:", mean_salary)

# Median of Age
median_age = df['Age'].median()
print("\nMedian Age:", median_age)
