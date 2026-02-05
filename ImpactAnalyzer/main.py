import argparse
import json
import time
import os
import shutil
import zipfile
import sys
from datetime import datetime, timedelta

from collectors.log_collector import LogCollector
from collectors.db_analyzer import DBAnalyzer
from collectors.browser_collector import BrowserCollector

def merge_configs(defaults, specific):
    """Deep merge of specific config into defaults."""
    merged = defaults.copy()
    for key, value in specific.items():
        if isinstance(value, dict) and key in merged:
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value
    return merged

def main():
    parser = argparse.ArgumentParser(description="Impact Analyzer for Banking App (Multi-Market)")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--duration", type=int, default=5, help="Duration of test in minutes")
    parser.add_argument("--market", required=True, help="Target Market (SG, MY, TH, etc.)")
    parser.add_argument("--app", required=True, help="App Type (customer, admin)")
    
    args = parser.parse_args()
    
    # 1. Load Config
    if not os.path.exists(args.config):
        print(f"[-] Config file not found: {args.config}")
        sys.exit(1)
        
    with open(args.config, 'r') as f:
        full_config = json.load(f)
        
    # 2. Select Specific Config
    market = args.market.upper()
    app_type = args.app.lower()
    
    if "markets" not in full_config or market not in full_config["markets"]:
        print(f"[-] Market '{market}' not found in configuration.")
        print(f"Available markets: {list(full_config.get('markets', {}).keys())}")
        sys.exit(1)
        
    market_config = full_config["markets"][market]
    
    if app_type not in market_config:
        print(f"[-] App '{app_type}' not found for market '{market}'.")
        print(f"Available apps: {list(market_config.keys())}")
        sys.exit(1)
        
    app_config = market_config[app_type]
    
    # 3. Merge with Global Defaults
    global_defaults = full_config.get("global_defaults", {})
    final_config = merge_configs(global_defaults, app_config)
    
    # Setup Output Dir
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_base = final_config.get('output_dir', 'reports')
    report_name = f"analysis_{market}_{app_type}_{timestamp}"
    report_dir = os.path.join(output_base, report_name)
    os.makedirs(report_dir, exist_ok=True)
    
    print(f"=== Starting Impact Analysis ===")
    print(f"Target: {market} / {app_type}")
    print(f"Duration: {args.duration} minutes")
    
    # 2. Initialize Collectors
    browser_cfg = final_config.get('browser', {})
    browser = BrowserCollector(browser_cfg)
    
    # 3. Start Browser Capture
    if browser_cfg.get('enabled', False):
        browser.start_capture()
        
    start_time = datetime.now()
    
    # 4. Wait for Test Execution
    try:
        print(f"[*] Monitoring started at {start_time}")
        print(f"[*] Perform your test actions now... (Waiting {args.duration}m)")
        # Simple countdown
        for remaining in range(args.duration * 60, 0, -10):
            print(f"   {remaining}s remaining...", end='\r')
            time.sleep(10)
        print("\n[*] Time's up.")
    except KeyboardInterrupt:
        print("\n[*] Interrupted by user. Stopping early.")
        
    end_time = datetime.now()
    
    # 5. Stop Browser and Collect
    if browser_cfg.get('enabled', False):
        browser.stop_capture(report_dir)
        
    # 6. Collect Server Logs
    server_cfg = final_config.get('server')
    if server_cfg:
        # Inject global SSH key if missing in specific config
        if 'ssh_key_path' not in server_cfg and 'ssh_key_path' in global_defaults:
             server_cfg['ssh_key_path'] = global_defaults['ssh_key_path']
             
        logger = LogCollector(server_cfg)
        logger.collect(start_time, end_time, report_dir)
    else:
        print("[-] No server configuration found.")
    
    # 7. Analyze DB
    db_cfg = final_config.get('database')
    if db_cfg:
        db = DBAnalyzer(db_cfg)
        db.analyze(start_time, end_time, report_dir)
    else:
        print("[-] No database configuration found.")
    
    # 8. Zip Results
    zip_name = f"{report_dir}.zip"
    shutil.make_archive(report_dir, 'zip', report_dir)
    
    print(f"\n[SUCCESS] Analysis Complete.")
    print(f"Report: {zip_name}")

if __name__ == "__main__":
    main()
