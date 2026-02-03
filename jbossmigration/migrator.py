import os
import shutil
import json
import logging
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime

# Initialize Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JBossMigrator:
    def __init__(self, config_path, dry_run=False):
        self.dry_run = dry_run
        self.config = self._load_config(config_path)
        self.source_dir = self.config['paths']['source_modules_dir']
        self.target_dir = self.config['paths']['target_modules_dir']
        self.ns_map = self.config.get('namespace_updates', {})
        self.deprecated_subsystems = self.config.get('deprecated_subsystems', [])

    def _load_config(self, path):
        if not os.path.exists(path):
            logger.error(f"Config file not found: {path}")
            raise FileNotFoundError(path)
        with open(path, 'r') as f:
            return json.load(f)

    def run_migration(self):
        logger.info("Starting JBoss Migration...")
        logger.info(f"Source: {self.source_dir}")
        logger.info(f"Target: {self.target_dir}")
        
        if self.dry_run:
            logger.warning("DRY RUN MODE ENABLED - No changes will be written.")

        if not os.path.exists(self.source_dir):
            logger.error(f"Source directory does not exist: {self.source_dir}")
            return

        for root, dirs, files in os.walk(self.source_dir):
            # Calculate relative path
            rel_path = os.path.relpath(root, self.source_dir)
            target_path = os.path.join(self.target_dir, rel_path)

            # Skip creating root directories if they are just containers (optional optimization)
            # but we generally want to replicate structure.
            
            # Determine if this directory is a module (contains module.xml)
            if "module.xml" in files:
                logger.info(f"Migrating module: {rel_path}")
                self._migrate_module_directory(root, target_path, files)

    def _migrate_module_directory(self, src_path, dest_path, files):
        if not self.dry_run:
            os.makedirs(dest_path, exist_ok=True)

        for file in files:
            src_file = os.path.join(src_path, file)
            dest_file = os.path.join(dest_path, file)

            if file == "module.xml":
                self._process_module_xml(src_file, dest_file)
            else:
                if not self.dry_run:
                    shutil.copy2(src_file, dest_file)
                logger.debug(f"Copied resource: {file}")

    def _process_module_xml(self, src_file, dest_file):
        try:
            tree = ET.parse(src_file)
            root = tree.getroot()
            
            # Update Namespace if root tag matches
            # Root tag is usually {urn:jboss:module:1.3}module
            updated = False
            
            # Check xmlns update mechanism
            # ElementTree stores namespace in the tag logic like {uri}tagname
            # simplified namespace check:
            for old_ns, new_ns in self.ns_map.items():
                if old_ns in root.tag:
                    if self.dry_run:
                        logger.info(f"[Dry Run] Would update namespace {old_ns} -> {new_ns} in {dest_file}")
                    else:
                        # Crude but effective for changing the default namespace of the root element
                        # A robust XML handling might reconstruct the tree, but for xmlns migration
                        # text replacement on the file string is sometimes safer to preserve formatting
                        # However, let's try to simulate or stick to ET logic if possible.
                        # Since ET hardcodes namespaces on parse, modifying it is tricky.
                        # Let's switch to a text-based replacement for the validation step to ensure we catch it.
                        updated = True 
                        break

            if self.dry_run:
                if not updated:
                     logger.debug(f"No namespace update needed for {src_file}")
                return

            # For actual writing, we use text processing to strictly replace the xmlns decl
            # This preserves comments and formatting better than ET
            with open(src_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for old_ns, new_ns in self.ns_map.items():
                if old_ns in content:
                    logger.info(f"Updating namespace {old_ns} -> {new_ns}")
                    content = content.replace(old_ns, new_ns)
            
            with open(dest_file, 'w', encoding='utf-8') as f:
                f.write(content)

        except ET.ParseError as e:
            logger.error(f"Failed to parse XML {src_file}: {e}")
            # Fallback copy if corrupt
            if not self.dry_run:
                shutil.copy2(src_file, dest_file)

    def analyze_standalone(self):
        """Analyzes standalone.xml for deprecated subsystems."""
        config_path = self.config['paths'].get('standalone_config')
        if not config_path or not os.path.exists(config_path):
            logger.warning(f"Standalone config not found at: {config_path}")
            return

        logger.info(f"Analyzing configuration: {config_path}")
        try:
            tree = ET.parse(config_path)
            root = tree.getroot()
            profile = root.find(".//{*}profile") # Search with wildcard namespace
            
            if profile is None:
                # Try finding without namespace if above fails or exact match
                # Often easier to iterate all elements
                pass

            # Robust search
            issues_found = []
            for elem in root.iter():
                # Check tag for deprecated subsystem namespaces
                for bad_ns in self.deprecated_subsystems:
                    if bad_ns in elem.tag:
                        issues_found.append(f"Deprecated subsystem found: {elem.tag.split('}')[-1]} ({bad_ns})")

            if issues_found:
                logger.warning("Migration Issues Found:")
                for issue in set(issues_found):
                    logger.warning(f" - {issue}")
            else:
                logger.info("No deprecated subsystems found.")

        except Exception as e:
            logger.error(f"Error analyzing standalone config: {e}")

def main():
    parser = argparse.ArgumentParser(description="JBoss 7 to 8 Migration Tool")
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    parser.add_argument('--dry-run', action='store_true', help='Simulate migration without writing files')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze standalone.xml')
    
    args = parser.parse_args()
    
    # Resolve config path relative to script if not absolute
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.join(os.path.dirname(__file__), config_path)

    try:
        migrator = JBossMigrator(config_path, dry_run=args.dry_run)
        
        if args.analyze_only:
            migrator.analyze_standalone()
        else:
            migrator.run_migration()
            migrator.analyze_standalone()
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")

if __name__ == "__main__":
    main()
