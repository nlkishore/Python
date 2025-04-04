import zipfile
import os
import subprocess
import argparse

def extract_class_from_jar(jar_path, class_name, output_dir):
    """Extracts a .class file from a JAR archive."""
    with zipfile.ZipFile(jar_path, 'r') as jar:
        class_file = class_name.replace('.', '/') + ".class"
        if class_file in jar.namelist():
            jar.extract(class_file, output_dir)
            print(f"Extracted {class_file} to {output_dir}")
            return os.path.join(output_dir, class_file)
        else:
            print(f"Class {class_name} not found in {jar_path}")
            return None

def decompile_using_jd_cli(class_file):
    """Decompile using jd-cli."""
    output_dir = os.path.dirname(class_file)
    subprocess.run(["jd-cli", class_file, "-od", output_dir])
    print(f"Decompiled {class_file} using jd-cli")

def decompile_using_jd_gui(class_file):
    """Decompile using jd-gui."""
    subprocess.run(["jd-gui.exe", class_file])
    print(f"Opened {class_file} in jd-gui")

def decompile_using_javap(class_file):
    """Decompile using javap."""
    subprocess.run(["javap", "-c", "-verbose", class_file])
    print(f"Decompiled {class_file} using javap")

def compare_zip_files(zip1, zip2, output_report):
    """Compare two ZIP files recursively and generate a report of differences."""
    def get_zip_contents(zip_path):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            return {info.filename: info.file_size for info in zip_ref.infolist()}
    
    contents1 = get_zip_contents(zip1)
    contents2 = get_zip_contents(zip2)
    
    all_files = set(contents1.keys()).union(set(contents2.keys()))
    differences = []
    
    for file in all_files:
        size1 = contents1.get(file, 'Missing')
        size2 = contents2.get(file, 'Missing')
        if size1 != size2:
            differences.append(f"{file}: {size1} bytes vs {size2} bytes")
    
    with open(output_report, 'w') as report:
        report.write("Differences in ZIP files:\n")
        report.write("\n".join(differences))
    
    print(f"Comparison report saved to {output_report}")

def main():
    parser = argparse.ArgumentParser(description="Extract, decompile, and compare JAR or ZIP files")
    parser.add_argument("-j", "--jar", help="Path to the JAR file")
    parser.add_argument("-c", "--class", help="Fully qualified class name (e.g., com.example.MyClass)")
    parser.add_argument("-d", "--decompiler", choices=["jd-cli", "jd-gui", "javap"], help="Decompiler to use")
    parser.add_argument("-o", "--output", default="./output", help="Directory to extract the class file")
    parser.add_argument("--zip1", help="First ZIP file to compare")
    parser.add_argument("--zip2", help="Second ZIP file to compare")
    parser.add_argument("--report", default="zip_comparison_report.txt", help="Output report for ZIP comparison")
    
    args = parser.parse_args()
    
    if args.jar and args.class:
        os.makedirs(args.output, exist_ok=True)
        class_file = extract_class_from_jar(args.jar, args.class, args.output)
        
        if class_file:
            if args.decompiler == "jd-cli":
                decompile_using_jd_cli(class_file)
            elif args.decompiler == "jd-gui":
                decompile_using_jd_gui(class_file)
            elif args.decompiler == "javap":
                decompile_using_javap(class_file)
    
    if args.zip1 and args.zip2:
        compare_zip_files(args.zip1, args.zip2, args.report)
    
if __name__ == "__main__":
    main()
