import configparser
import os

def load_config(config_file='config.ini'):
    """
    Loads configuration from an INI file.
    Resolves the file path relative to the directory of the calling script 
    or the current working directory if not absolute.
    """
    if not os.path.isabs(config_file):
        # Try to find config relative to the caller's directory
        # logic: get the directory of the script calling this function ? 
        # Actually simplest is relative to CWD or relative to this module
        # But commonly "relative path" means relative to where the script is run.
        
        # However, for a shared library, users might expect it to load from
        # the same folder as the library or their own project root.
        
        # Let's support looking in the CWD first
        cwd_path = os.path.join(os.getcwd(), config_file)
        if os.path.exists(cwd_path):
            config_path = cwd_path
        else:
             # Fallback: Look in the directory where this module resides (common)
             module_dir = os.path.dirname(os.path.abspath(__file__))
             module_path = os.path.join(module_dir, config_file)
             config_path = module_path
    else:
        config_path = config_file

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    config = configparser.ConfigParser()
    config.read(config_path)
    return config
