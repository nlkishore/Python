import requests
from bs4 import BeautifulSoup
import pandas as pd

# URL of SonarLint Java rules page
URL = "https://rules.sonarsource.com/java/"

# Get HTML content
response = requests.get(URL)
soup = BeautifulSoup(response.text, "html.parser")

# Find the specific <ol> with id="rules-list"
rules_ol = soup.find("ol", {"class":"RulesListstyles__StyledOl-sc-6thbbv-0 fqPwoD"})

# Find all rule entries
#rules = soup.find_all("a", class_="rules-index__rule-id")

#ol class="RulesListstyles__StyledOl-sc-6thbbv-0 fqPwoD"
rule_links = soup.find_all("a")
print(f"Rule are ",rule_links)
rule_data = []
for link in rule_links:
    if "RSPEC" in link["href"]:  # Check if "RSPEC" is in the href attribute
        rule_id = link["href"].split("/")[-2]  # Extract "RSPEC-XXXX"
        rule_text = link.text.strip()  # Extract rule description
        full_url = "https://rules.sonarsource.com" + link["href"]

        print(f"Rule ID: {rule_id}")
        print(f"Rule Text: {rule_text}")
        print(f"Full URL: {full_url}")
        print("-" * 40)

        rule_data.append({"Rule ID": rule_id, "Rule Name": rule_text, "Full URL":full_url})
# Extract rule IDs (RSPEC-xxxx) and names
'''rule_data = []
for rule in rules:
    rule_id = rule.text.strip()
    rule_name = rule.find_next_sibling("span").text.strip() if rule.find_next_sibling("span") else ""
    print(rule_name)
    rule_data.append({"Rule ID": rule_id, "Rule Name": rule_name})
'''
# Convert to DataFrame
df = pd.DataFrame(rule_data)

# Save to Excel
df.to_excel("SonarLint-Java-Rules.xlsx", index=False)

print("✅ Extracted all SonarLint Java Rule IDs. Saved as 'SonarLint-Java-Rules.xlsx'")
