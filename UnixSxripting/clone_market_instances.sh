#!/bin/bash
# 
# Usage: ./clone_market_instance.sh GEBCUJP
market_code=$1

if [ -z "$market_code" ]; then
  echo "❗ Error: Market code not provided."
  echo "Usage: ./clone_market_instance.sh GEBCUJP"
  exit 1
fi

echo "🚀 Cloning deployment setup for $market_code..."

# Base paths
base_path="/prodlb"
template_market="GEBCUSG"

# Create new market folder structure
mkdir -p $base_path/$market_code/{appcatonfolder,docrootfolder,resourcesfolder}

# Copy template files
cp -r $base_path/$template_market/appcatonfolder/* $base_path/$market_code/appcatonfolder/
cp -r $base_path/$template_market/docrootfolder/* $base_path/$market_code/docrootfolder/
cp -r $base_path/$template_market/resourcesfolder/* $base_path/$market_code/resourcesfolder/

# Clone JBoss instance
jboss_src="/app/jboss/eap/instances/eapmm"
jboss_target="/app/jboss/eap/instances/eap${market_code: -2}"

cp -r $jboss_src $jboss_target
sed -i "s/$template_market/$market_code/g" $jboss_target/standalone/configuration/standalone.xml

# Clone Apache web instance
apache_src="/app/apache/instances/webservermm"
apache_target="/app/apache/instances/webserver${market_code: -2}"

cp -r $apache_src $apache_target
sed -i "s/$template_market/$market_code/g" $apache_target/conf/httpd.conf

# Replace internal references in copied folders
grep -rl "$template_market" "$base_path/$market_code" | xargs sed -i "s/$template_market/$market_code/g"

echo "✅ Deployment setup for $market_code created successfully."
