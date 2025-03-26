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

def main():
    parser = argparse.ArgumentParser(description="Extract and decompile .class files from a JAR")
    parser.add_argument("-j", "--jar", required=True, help="Path to the JAR file")
    parser.add_argument("-c", "--class", required=True, help="Fully qualified class name (e.g., com.example.MyClass)")
    parser.add_argument("-d", "--decompiler", choices=["jd-cli", "jd-gui", "javap"], required=True, help="Decompiler to use")
    parser.add_argument("-o", "--output", default="./output", help="Directory to extract the class file")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    class_file = extract_class_from_jar(args.jar, args.class, args.output)
    
    if class_file:
        if args.decompiler == "jd-cli":
            decompile_using_jd_cli(class_file)
        elif args.decompiler == "jd-gui":
            decompile_using_jd_gui(class_file)
        elif args.decompiler == "javap":
            decompile_using_javap(class_file)
    
if __name__ == "__main__":
    main()
