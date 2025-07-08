from generate_and_install_ssh_key_node import generate_and_install_ssh_key_node
from owner_copy_workflow_node import owner_copy_workflow_node

def main():
    # Setup: define host and users
    host = "your.server.com"

    # SSH install for owner1
    state1 = {
        "host": host,
        "username": "alice",
        "password": "alicePassword123",  # Only needed for first-time key install
        "key_dir": "/Users/laxmi/.ssh"
    }
    result1 = generate_and_install_ssh_key_node(state1)
    key_path_owner1 = result1["key_path"]

    # SSH install for owner2
    state2 = {
        "host": host,
        "username": "bob",
        "password": "bobPassword123",  # Only needed for first-time key install
        "key_dir": "/Users/laxmi/.ssh"
    }
    result2 = generate_and_install_ssh_key_node(state2)
    key_path_owner2 = result2["key_path"]

    # Run secure file transfer
    file_transfer_state = {
        "host": host,
        "owner1": "alice",
        "owner2": "bob",
        "key_path_owner1": key_path_owner1,
        "key_path_owner2": key_path_owner2,
        "source_file": "/home/alice/data.txt",
        "destination_path": "/home/bob/shared/"
    }

    result = owner_copy_workflow_node(file_transfer_state)
    print("✅ File transfer complete.")
    print(f"📁 Temp file removed: {result['tmp_file']}")
    print(f"📦 Final destination: {result['final_path']}")

if __name__ == "__main__":
    main()