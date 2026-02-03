import os
import sys
import logging

# Add usage of logging for better output control
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(1, 'C:/Python/ConfigReader/')
try:
    import PropReader as propreader
except ImportError:
    logger.error("PropReader module not found in C:/Python/ConfigReader/")
    sys.exit(1)


def get_config_values():
    """Reads all necessary configuration values from the properties file."""
    try:
        config = {}
        config['folder_list'] = propreader.readConfigValue('spring', 'folderlist').split(',')
        config['base_folder'] = propreader.readConfigValue('spring', 'basefolder')
        config['project_name'] = propreader.readConfigValue('spring', 'projectname')
        config['src_folder'] = propreader.readConfigValue('spring', 'srcfolder')
        return config
    except Exception as e:
        logger.error(f"Error reading configuration: {e}")
        raise


def create_source_file_template(full_path, folder_path_key, relative_path):
    """Creates a Java source file template within the specified directory."""
    pkg_name = relative_path.replace('\\', '.')
    # Removing 'folder' suffix to guess the filename key, e.g., 'configfolder' -> 'configfilename'
    file_path_key = folder_path_key.replace('folder', 'filename')
    
    logger.debug(f"Converting folder key '{folder_path_key}' to file key '{file_path_key}'")

    if 'filename' in file_path_key:
        try:
            file_names_str = propreader.readConfigValue('spring', file_path_key)
            if not file_names_str:
                return

            file_name_list = file_names_str.split(',')
            for file_name in file_name_list:
                file_full_path = os.path.join(full_path, file_name)
                logger.info(f"Creating file: {file_full_path}")
                
                # Using 'w' to ensure valid file content (single package/class definition)
                with open(file_full_path, "w") as f:
                    f.write(f"package {pkg_name};\n\n")
                    class_name = file_name.replace('.java', '')
                    f.write(f"public class {class_name} {{}}\n")
        except Exception as ex:
            logger.error(f"Error creating file template: {ex}")


def spring_boot_base():
    """Main function to generate Spring Boot project structure."""
    logger.info('Starting Spring Boot Project Generation')
    try:
        config = get_config_values()
        
        base_folder = config['base_folder']
        project_name = config['project_name']
        src_folder = config['src_folder']
        folder_keys = config['folder_list']
        
        project_root = os.path.join(base_folder, project_name)
        src_root = os.path.join(project_root, src_folder)

        logger.info(f"Base Folder: {base_folder}")
        logger.info(f"Project Name: {project_name}")
        logger.info(f"Source Folder: {src_folder}")

        # Create project root
        if not os.path.exists(project_root):
            os.makedirs(project_root)
            logger.info(f"Created project root: {project_root}")
        
        # Create src root
        if not os.path.exists(src_root):
             os.makedirs(src_root)
             logger.info(f"Created src root: {src_root}")

        for folder_key in folder_keys:
            folder_key = folder_key.strip()
            if not folder_key:
                continue
                
            relative_path = propreader.readConfigValue('spring', folder_key)
            if not relative_path:
                logger.warning(f"No path found for key: {folder_key}")
                continue

            # Construct full path safely
            # Note: The original code does: baseFolder + / + projectName + / + srcCodeFolder + / + fldrPath
            # So the folders defined in config are subfolders of the src directory.
            full_path = os.path.join(src_root, relative_path)
            
            logger.info(f"Processing folder: {relative_path}")
            
            if not os.path.exists(full_path):
                os.makedirs(full_path)
                logger.info(f"Created directory: {full_path}")
            
            create_source_file_template(full_path, folder_key, relative_path)

    except Exception as ex:
        logger.error(f"An error occurred: {ex}")


if __name__ == "__main__":
    spring_boot_base()

