import argparse
import configparser

def load_properties(file_path):
    """Loads a .properties file into a dictionary."""
    properties = {}
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):  # Ignore comments and empty lines
                key_value = line.split("=", 1)
                if len(key_value) == 2:
                    key, value = key_value
                    properties[key.strip()] = value.strip()
    return properties

def compare_properties(file1, file2):
    """Compares two properties files and returns missing and different keys."""
    props1 = load_properties(file1)
    props2 = load_properties(file2)

    missing_in_file2 = {k: props1[k] for k in props1 if k not in props2}
    missing_in_file1 = {k: props2[k] for k in props2 if k not in props1}
    different_values = {k: (props1[k], props2[k]) for k in props1 if k in props2 and props1[k] != props2[k]}

    return missing_in_file2, missing_in_file1, different_values

def generate_report(file1, file2, report_file):
    """Generates a report of missing and different keys."""
    missing_in_file2, missing_in_file1, different_values = compare_properties(file1, file2)

    with open(report_file, "w", encoding="utf-8") as report:
        report.write(f"Comparison Report: {file1} vs {file2}\n")
        report.write("=" * 60 + "\n")

        if missing_in_file2:
            report.write("\nKeys present in {0} but missing in {1}:\n".format(file1, file2))
            for key, value in missing_in_file2.items():
                report.write(f"{key} = {value}\n")

        if missing_in_file1:
            report.write("\nKeys present in {0} but missing in {1}:\n".format(file2, file1))
            for key, value in missing_in_file1.items():
                report.write(f"{key} = {value}\n")

        if different_values:
            report.write("\nKeys with different values:\n")
            for key, (val1, val2) in different_values.items():
                report.write(f"{key}:\n  {file1}: {val1}\n  {file2}: {val2}\n")

    print(f"Comparison report saved to {report_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare two properties files.")
    parser.add_argument("file1", help="Path to first properties file")
    parser.add_argument("file2", help="Path to second properties file")
    parser.add_argument("-o", "--output", default="comparison_report.txt", help="Output report file")

    args = parser.parse_args()
    generate_report(args.file1, args.file2, args.output)
