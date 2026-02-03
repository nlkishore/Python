import json
import csv
import os
import sys
import logging
import argparse
from datetime import datetime

# Initialize Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Try importing Atlassian API
try:
    from atlassian import Bitbucket
except ImportError:
    # We allow running without the library ONLY if in mock mode, checked later
    pass


def load_config(config_path):
    """Load configuration from JSON file."""
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        return json.load(f)


def get_missing_commits(bb, project, repo, source_branch, target_branch):
    """
    Fetch commits present in source_branch but missing in target_branch.
    """
    logger.info(f"Comparing {source_branch} -> {target_branch}...")
    try:
        commits = bb.get_commits(project, repo, branch=source_branch, exclude=target_branch, limit=100)
        
        missing = []
        for commit in commits:
            if len(commit.get('parents', [])) > 1:
                continue

            missing.append({
                'id': commit['id'],
                'author': commit['author']['name'] if 'author' in commit else 'Unknown',
                'date': datetime.fromtimestamp(commit['authorTimestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                'message': commit['message'].strip().split('\n')[0]
            })
            
        logger.info(f"Found {len(missing)} missing commits.")
        return missing

    except Exception as e:
        logger.error(f"Failed to fetch commits for {source_branch} -> {target_branch}: {e}")
        return []


def get_mock_commits(source_branch, target_branch):
    """Generate mock data for testing."""
    logger.info(f"[MOCK] Comparing {source_branch} -> {target_branch}...")
    import random
    if random.choice([True, False]):
        return [{
            'id': f'abc{random.randint(100,999)}',
            'author': 'Mock User',
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'message': f'Fix critical issue in {source_branch}'
        }]
    return []


def generate_csv_report(data, output_path):
    """Generate CSV report."""
    if not data:
        return

    keys = ['Country', 'Source Branch', 'Target Branch', 'Commit ID', 'Author', 'Date', 'Message']
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        logger.info(f"CSV Report generated: {output_path}")
    except Exception as e:
        logger.error(f"Failed to write CSV report: {e}")


def generate_html_report(data, output_path):
    """Generate a simple HTML dashboard report."""
    if not data:
        return

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    html_content = """
    <html>
    <head>
        <title>Bitbucket Branch Integrity Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #205081; }
            table { border-collapse: collapse; width: 100%; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #205081; color: white; }
            tr:hover { background-color: #f5f5f5; }
            .badge { padding: 4px 8px; border-radius: 4px; background-color: #ffeded; color: #c9190b; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>Branch Integrity Audit Report</h1>
        <p>Generated on: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
        <table>
            <thead>
                <tr>
                    <th>Country</th>
                    <th>Source Branch</th>
                    <th>Target Branch</th>
                    <th>Commit ID</th>
                    <th>Author</th>
                    <th>Date</th>
                    <th>Message</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for row in data:
        html_content += f"""
            <tr>
                <td>{row['Country']}</td>
                <td>{row['Source Branch']}</td>
                <td>{row['Target Branch']}</td>
                <td><code>{row['Commit ID']}</code></td>
                <td>{row['Author']}</td>
                <td>{row['Date']}</td>
                <td>{row['Message']}</td>
            </tr>
        """
        
    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"HTML Report generated: {output_path}")
    except Exception as e:
        logger.error(f"Failed to write HTML report: {e}")


def main():
    parser = argparse.ArgumentParser(description="Bitbucket Branch Auditor")
    parser.add_argument('--mock', action='store_true', help="Run in mock mode without connecting to Bitbucket")
    args = parser.parse_args()

    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    config = load_config(config_path)

    bb = None
    if not args.mock:
        # Check import again
        if 'atlassian' not in sys.modules:
             logger.error("Required library 'atlassian-python-api' not found.")
             logger.error("Please install it using: pip install atlassian-python-api")
             sys.exit(1)

        bb_config = config['bitbucket']
        try:
            bb = Bitbucket(
                url=bb_config['url'],
                username=bb_config['username'],
                password=bb_config['password']
            )
        except Exception as e:
            logger.error(f"Failed to connect to Bitbucket: {e}")
            return
    else:
        logger.warning("RUNNING IN MOCK MODE. No actual data will be fetched.")

    project = config['bitbucket']['project']
    repo = config['bitbucket']['repo']
    
    all_missing_commits = []

    for country in config.get('countries', []):
        country_name = country['name']
        logger.info(f"Processing Country: {country_name}")
        
        pairs = country.get('pairs', [])
        for pair in pairs:
            src = pair['source']
            tgt = pair['target']
            
            if args.mock:
                commits = get_mock_commits(src, tgt)
            else:
                commits = get_missing_commits(bb, project, repo, src, tgt)
            
            for c in commits:
                all_missing_commits.append({
                    'Country': country_name,
                    'Source Branch': src,
                    'Target Branch': tgt,
                    'Commit ID': c['id'],
                    'Author': c['author'],
                    'Date': c['date'],
                    'Message': c['message']
                })

    report_config = config.get('report', {})
    output_dir = report_config.get('output_dir', 'reports')
    csv_filename = report_config.get('filename', 'audit_report.csv')
    html_filename = csv_filename.replace('.csv', '.html')

    csv_path = os.path.join(output_dir, csv_filename)
    html_path = os.path.join(output_dir, html_filename)

    if all_missing_commits:
        generate_csv_report(all_missing_commits, csv_path)
        generate_html_report(all_missing_commits, html_path)
    else:
        logger.info("No missing commits found.")


if __name__ == "__main__":
    main()
