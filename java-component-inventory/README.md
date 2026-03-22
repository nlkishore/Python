# Java component inventory (INI-driven)

Scans **only** configured **component folder names** under a **base path** (other sibling folders are ignored). Produces an **Excel** workbook with:

- **AllFiles** — `ComponentFolder`, `ParentFolderName`, `PackageName`, `ClassFileName`, `FQN`, `RelativePath`
- **Summary3Col** — `FolderName` (component), `PackageName`, `ClassFileName` (strict 3-column summary)
- **Collisions** — same **FQN** (package + class) appearing in **more than one** scanned component
- **Meta** — counts and timestamp

## Setup

```powershell
cd C:\Python-cursor\java-component-inventory
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
```

Or: `pip install -r requirements.txt` and run `python -m java_component_inventory.cli`

## Configuration

1. Copy `config.example.ini` → `config.ini` (gitignored).
2. Set:
   - **`[paths] base_folder`** — root that **contains** your component directories.
   - **`[scan] components`** — comma-separated **names of direct child folders** under `base_folder` to scan (only these are used).

Example: if `base_folder` is `D:\app` and you set `components = core, bank-ext`, only `D:\app\core\**/*.java` and `D:\app\bank-ext\**/*.java` are scanned; `D:\app\docs` is skipped.

Optional:

- **`[output] report_dir`** — where to write Excel (default: `<base_folder>/java-inventory-reports`).
- **`[options] detect_collisions`** — `true` / `false`.

## Run

```powershell
$env:PYTHONPATH = "src"   # if not using pip install -e .
python -m java_component_inventory.cli -c config.ini
```

Or after `pip install -e .`:

```powershell
java-component-scan -c config.ini
java-component-scan -c config.ini -o D:\reports\inventory.xlsx
```

## Requirements

- Python 3.10+
- `openpyxl`

## Notes

- Skips common build segments in paths: `target`, `build`, `out`, `bin`.
- **Package** is read from the `package ...;` declaration; default package types use FQN = class name only.
- **Collisions** use **public top-level** assumption: class name = filename stem.
