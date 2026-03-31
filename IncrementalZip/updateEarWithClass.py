import zipfile
import tempfile
import shutil
import os
import configparser


def update_classes_in_ear(ear_path, updates, output_ear=None):
    """
    Updates specific .class files in .jar files inside a .ear archive.

    Parameters:
    - ear_path: Path to the original EAR file
    - updates: A dictionary mapping jarname → {class_relative_path_in_jar → new_class_file_path}
      Example: {"lib/myjar.jar": {"com/example/MyClass.class": "updated_classes/MyClass.class"}}
    - output_ear: Path for writing updated EAR. If None, overwrites ear_path.
    """
    output_ear = output_ear or (ear_path + ".updated")
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Extract EAR
        with zipfile.ZipFile(ear_path, 'r') as earzip:
            earzip.extractall(tmpdir)

        # 2. Update JARs
        for jar_relpath, classes in updates.items():
            jar_path = os.path.join(tmpdir, jar_relpath)
            if not os.path.exists(jar_path):
                print(f"JAR {jar_relpath} not found in EAR")
                continue

            with tempfile.TemporaryDirectory() as jar_tmpdir:
                # Extract JAR
                with zipfile.ZipFile(jar_path, 'r') as jarzip:
                    jarzip.extractall(jar_tmpdir)

                # Replace class files
                for class_path_in_jar, new_class_path in classes.items():
                    dest_path = os.path.join(jar_tmpdir, class_path_in_jar)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy2(new_class_path, dest_path)

                # Repack JAR
                with zipfile.ZipFile(jar_path, 'w') as jarzip:
                    for root, dirs, files in os.walk(jar_tmpdir):
                        for file in files:
                            abs_path = os.path.join(root, file)
                            arcname = os.path.relpath(abs_path, jar_tmpdir)
                            jarzip.write(abs_path, arcname)

        # 3. Repack EAR
        with zipfile.ZipFile(output_ear, 'w') as earzip:
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    arcname = os.path.relpath(abs_path, tmpdir)
                    earzip.write(abs_path, arcname)

    print(f"Updated EAR written to: {output_ear}")

def parse_updates_from_ini(ini_path):
    config = configparser.ConfigParser()
    config.optionxform = str  # preserve case
    config.read(ini_path)

    if 'DEFAULT' not in config or 'ear_path' not in config['DEFAULT']:
        raise ValueError("INI file's [DEFAULT] section must have 'ear_path'")
    ear_path = config['DEFAULT']['ear_path']

    updates = {}
    for section in config.sections():
        if section == 'DEFAULT':
            continue
        if 'filelist' not in config[section]:
            print(f"Section [{section}] missing 'filelist'. Skipping.")
            continue
        filelist_path = config[section]['filelist']
        jar_updates = {}
        with open(filelist_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    print(f"Ignoring malformed line in {filelist_path}: {line}")
                    continue
                class_path, new_file = map(str.strip, line.split('=', 1))
                jar_updates[class_path] = new_file
        updates[section] = jar_updates
    return ear_path, updates

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python updateEarWithClass.py <updatePlan.ini> [output_ear]")
        return
    ini_path = sys.argv[1]
    output_ear = sys.argv[2] if len(sys.argv) > 2 else None
    ear_path, updates = parse_updates_from_ini(ini_path)
    update_classes_in_ear(ear_path, updates, output_ear)

if __name__ == "__main__":
    main()