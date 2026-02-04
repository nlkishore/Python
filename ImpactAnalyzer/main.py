import argparse
import json
import time
import os
import shutil
import zipfile
from datetime import datetime, timedelta

from collectors.log_collector import LogCollector
from collectors.db_analyzer import DBAnalyzer
from collectors.browser_collector import BrowserCollector

def main():
    parser = argparse.ArgumentParser(description="Impact Analyzer for Banking App")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--duration", type=int, default=5, help="Duration of test in minutes")
    args = parser.parse_args()
    
    # 1. Load Config
    with open(args.config, 'r') as f:
        config = json.load(f)
        
    # Setup Output Dir
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_base = config.get('output_dir', 'reports')
    report_dir = os.path.join(output_base, f"analysis_{timestamp}")
    os.makedirs(report_dir, exist_ok=True)
    
    print(f"=== Starting Impact Analysis (Duration: {args.duration}m) ===")
    
    # 2. Initialize Collectors
    browser = BrowserCollector(config['browser'])
    
    # 3. Start Browser Capture
    if config['browser']['enabled']:
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
    if config['browser']['enabled']:
        browser.stop_capture(report_dir)
        
    # 6. Collect Server Logs
    logger = LogCollector(config['server'])
    logger.collect(start_time, end_time, report_dir)
    
    # 7. Analyze DB
    db = DBAnalyzer(config['database'])
    db.analyze(start_time, end_time, report_dir)
    
    # 8. Zip Results
    zip_name = f"{report_dir}.zip"
    shutil.make_archive(report_dir, 'zip', report_dir)
    
    print(f"\n[SUCCESS] Analysis Complete.")
    print(f"Report: {zip_name}")

if __name__ == "__main__":
    main()
