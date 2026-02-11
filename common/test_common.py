import sys
import os

# Add current directory to path so we can import 'common' if running from outside
# But here we assume this script is IN common or we adjust path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config_loader import load_config
from connectors import connect_bitbucket, connect_artifactory, connect_jenkins

def test_commons():
    print("--- Testing Config Loader ---")
    try:
        # relative path test
        config = load_config('config.ini')
        print("[OK] Config loaded successfully")
        
        print(f"Bitbucket URL: {config.get('bitbucket', 'url')}")
        
    except Exception as e:
        print(f"[FAIL] Config load failed: {e}")
        return

    print("\n--- Testing Connectors (Expect errors as URLs are fake) ---")
    connect_bitbucket(config)
    connect_artifactory(config)
    connect_jenkins(config)

if __name__ == "__main__":
    test_commons()
