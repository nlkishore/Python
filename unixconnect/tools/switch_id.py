import pexpect
import getpass
import yaml
import argparse
import os

def su_and_run(user, password, command):
    try:
        child = pexpect.spawn(f"su - {user}", encoding="utf-8", timeout=10)
        child.expect("Password:")
        child.sendline(password)
        child.expect([r"\$", "#"])
        child.sendline(command)
        child.expect([r"\$", "#"])
        output = child.before.strip().split("\n", 1)[-1].strip()
        child.sendline("exit")
        child.close()
        return output
    except Exception as e:
        return f"❌ Failed to switch to {user}: {e}"

def load_users(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser(description="Switch to multiple Unix users and run a command.")
    parser.add_argument("--cmd", required=True, help="Shell command to run under each user")
    parser.add_argument("--config", default="users.yaml", help="YAML file listing user roles and usernames")
    args = parser.parse_args()

    users = load_users(args.config)
    password = getpass.getpass("🔐 Enter shared password for all target users: ")

    for label, username in users.items():
        print(f"\n🧑‍💼 [{label}] → {username}")
        output = su_and_run(username, password, args.cmd)
        print(f"📦 Output:\n{output}")

if __name__ == "__main__":
    main()