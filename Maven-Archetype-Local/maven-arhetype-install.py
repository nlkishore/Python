import configparser
import subprocess
import os
import shutil

def run(cmd, cwd=None):
    print(f"\n🔧 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f"❌ Command failed: {cmd}")

def normalize_version(pom_path, snapshot_version, release_version):
    if not os.path.exists(pom_path):
        raise FileNotFoundError(f"POM file not found: {pom_path}")
    with open(pom_path, "r", encoding="utf-8") as f:
        content = f.read()
    if snapshot_version in content:
        content = content.replace(snapshot_version, release_version)
        with open(pom_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Normalized version from {snapshot_version} to {release_version} in {pom_path}")
    else:
        print(f"ℹ️ No version normalization needed — already set to {release_version}")

# Load config.ini from script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, "config.ini")
config = configparser.ConfigParser()
config.read(config_path)

# Paths
repo_url = config["paths"]["git_repo_url"]
clone_dir = config["paths"]["clone_dir"]
settings_file = config["paths"]["settings_file"]
workspace = config["paths"]["project_workspace"]

# Archetype
group_id = config["archetype"]["group_id"]
artifact_id = config["archetype"]["artifact_id"]
release_version = config["archetype"]["version"]
snapshot_version = config["archetype"]["snapshot_version"]

# Projects
project_names = [p.strip() for p in config["projects"]["names"].split(",")]
project_group_id = config["projects"]["group_id"]
project_version = config["projects"]["version"]

# Step 1: Clone Git repo
# if os.path.exists(clone_dir):
#     print(f"🧹 Removing existing clone directory: {clone_dir}")
#     shutil.rmtree(clone_dir)

# run(f"git clone {repo_url} \"{clone_dir}\"")

# Step 2: Normalize version in archetype POM
# pom_path = os.path.join(clone_dir, artifact_id, "pom.xml")
# normalize_version(pom_path, snapshot_version, release_version)

# Step 3: Install archetype using custom settings
# run(f"mvn clean install -s \"{settings_file}\"", cwd=os.path.join(clone_dir, artifact_id))

# Step 4: Generate projects using direct coordinates
for name in project_names:
    cmd = (
        f"mvn archetype:generate "
        f"-s \"{settings_file}\" "
        f"-DarchetypeGroupId={group_id} "
        f"-DarchetypeArtifactId={artifact_id} "
        f"-DarchetypeVersion={release_version} "
        f"-DgroupId={project_group_id} "
        f"-DartifactId={name} "
        f"-Dversion={project_version} "
        f"-DinteractiveMode=false"
    )
    run(cmd, cwd=workspace)

print("\n🎉 All projects generated successfully.")