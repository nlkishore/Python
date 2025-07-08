# main.py
from scp_collector_node import scp_collector_node

def main():
    state = {
        "config_file": "servers.ini",
        "output_dir": "/home/collector/received_files",
        "max_threads": 4
    }

    result = scp_collector_node(state)
    print(f"🎉 Result: {result}")

if __name__ == "__main__":
    main()