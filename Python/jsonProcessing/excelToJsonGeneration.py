import pandas as pd

# Define the JSON structure
data = {
    "Department": {
        "DepartmentID": 101,
        "DepartmentName": "Engineering",
        "Manager": {
            "ManagerID": 1,
            "ManagerName": "Alice Smith",
            "Email": "alice.smith@example.com"
        },
        "Employees": [
            {
                "EmployeeID": 1011,
                "EmployeeName": "Bob Johnson",
                "Position": "Software Engineer",
                "Salary": 70000,
                "Contact": {
                    "Email": "bob.johnson@example.com",
                    "Phone": "+123456789"
                },
                "Skills": ["Java", "Python", "AWS"]
            },
            {
                "EmployeeID": 1012,
                "EmployeeName": "Carol White",
                "Position": "DevOps Engineer",
                "Salary": 75000,
                "Contact": {
                    "Email": "carol.white@example.com",
                    "Phone": "+987654321"
                },
                "Skills": ["Docker", "Kubernetes", "CI/CD"]
            },
            {
                "EmployeeID": 1013,
                "EmployeeName": "David Brown",
                "Position": "Frontend Developer",
                "Salary": 68000,
                "Contact": {
                    "Email": "david.brown@example.com",
                    "Phone": "+192837465"
                },
                "Skills": ["JavaScript", "React", "CSS"]
            }
        ]
    }
}

# Extract department and employees information
department_info = data["Department"]
employees_info = department_info.pop("Employees")

# Convert to DataFrame
employees_df = pd.DataFrame(employees_info)

# Flatten nested contact information and skills
contacts = employees_df["Contact"].apply(pd.Series)
skills = employees_df["Skills"].apply(lambda x: ', '.join(x) if isinstance(x, list) else '')
employees_df = pd.concat([employees_df.drop(["Contact", "Skills"], axis=1), contacts, skills.rename("Skills")], axis=1)

# Add department information to each employee row
for key, value in department_info.items():
    if isinstance(value, dict):
        for sub_key, sub_value in value.items():
            employees_df[f'{key}_{sub_key}'] = sub_value
    else:
        employees_df[key] = value

# Reorder columns to bring department info to the front
cols = ['DepartmentID', 'DepartmentName', 'Manager_ManagerID', 'Manager_ManagerName', 'Manager_Email'] + [col for col in employees_df.columns if col not in ['DepartmentID', 'DepartmentName', 'Manager_ManagerID', 'Manager_ManagerName', 'Manager_Email']]
employees_df = employees_df[cols]

# Save to Excel
employees_df.to_excel('combined_data.xlsx', index=False)

print('JSON data has been successfully converted to a single Excel sheet!')
