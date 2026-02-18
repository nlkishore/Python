# Modularization Strategy for Isolation

To manage the migration effectively, identifying and isolating legacy dependencies is crucial. The `module_extractor.py` script assists in physically separating code into different Maven-like modules.

## Purpose
The script scans your Java source code and moves files into new directories based on their imports.
*   **`legacy-village`**: Files importing `com.workingdogs.village.*`. These are the highest risk and should be refactored first.
*   **`legacy-torque`**: Files importing `org.apache.torque.*`. These need to be regenerated or updated.

## Usage

1.  **Configure**: Edit `c:\Python\migration_docs\module_extractor.py`.
    *   Set `SOURCE_DIR` to your existing source root (e.g., `C:\MyProject\src\main\java`).
    *   Set `OUTPUT_DIR` to where you want the new modules created.
    *   Set `DRY_RUN = True` initially to see what WILL happen without moving files.

2.  **Run**:
    ```bash
    python c:\Python\migration_docs\module_extractor.py
    ```

3.  **Review Output**: The script will print a summary of how many files would be moved to each module.

4.  **Execute**: Change `DRY_RUN = False` in the script and run it again to perform the move.

## Post-Extraction Steps
After moving the files, you will have broken references (compilation errors).
1.  **Create `pom.xml`** files for the new modules (`legacy-village`, `legacy-torque`).
2.  **Update Dependencies**: The main application now depends on these modules.
3.  **Refactor**: Now you can work on `legacy-village` in isolation, replacing the Village imports with your Adapter or JDBC code, without touching the rest of the application.
