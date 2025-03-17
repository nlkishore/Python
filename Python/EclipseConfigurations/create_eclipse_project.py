import os
import configparser
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree

# Read configuration from INI file
config = configparser.ConfigParser()
config.read("eclipse_project.ini")

# Extract configurations
project_name = config.get("Project", "name")
source_path = config.get("Project", "source_path")
libraries = config.get("Project", "libraries", fallback="").split(",")
shared_lib_path = config.get("Project", "shared_lib_path", fallback="")

# Project root directory
project_root = os.path.join(os.getcwd(), project_name)
src_folder = os.path.join(project_root, source_path)

# Create directories
os.makedirs(src_folder, exist_ok=True)

# Function to generate .project file
def create_project_file():
    project = Element("projectDescription")
    name = SubElement(project, "name")
    name.text = project_name

    SubElement(project, "comment")
    projects = SubElement(project, "projects")

    build_spec = SubElement(project, "buildSpec")
    build_command = SubElement(build_spec, "buildCommand")
    name = SubElement(build_command, "name")
    name.text = "org.eclipse.jdt.core.javabuilder"

    arguments = SubElement(build_command, "arguments")

    natures = SubElement(project, "natures")
    nature = SubElement(natures, "nature")
    nature.text = "org.eclipse.jdt.core.javanature"

    tree = ElementTree(project)
    with open(os.path.join(project_root, ".project"), "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)

# Function to generate .classpath file
def create_classpath_file():
    classpath = Element("classpath")

    # Add source entry
    classpath_entry = SubElement(classpath, "classpathentry", {
        "kind": "src",
        "path": source_path
    })

    # Add JRE System Library
    SubElement(classpath, "classpathentry", {
        "kind": "con",
        "path": "org.eclipse.jdt.launching.JRE_CONTAINER"
    })

    # Add external libraries
    for lib in libraries:
        lib = lib.strip()
        if lib:
            SubElement(classpath, "classpathentry", {
                "kind": "lib",
                "path": lib
            })

    # Add shared libraries if configured
    if shared_lib_path and os.path.exists(shared_lib_path):
        for shared_lib in os.listdir(shared_lib_path):
            if shared_lib.endswith(".jar"):
                SubElement(classpath, "classpathentry", {
                    "kind": "lib",
                    "path": os.path.join(shared_lib_path, shared_lib)
                })

    # Output .classpath file
    tree = ElementTree(classpath)
    with open(os.path.join(project_root, ".classpath"), "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)

# Run functions
create_project_file()
create_classpath_file()

print(f"Eclipse Java project '{project_name}' created successfully!")
