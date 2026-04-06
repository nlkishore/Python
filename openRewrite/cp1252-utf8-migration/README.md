# CP-1252 → UTF-8 migration helper

Legacy sources are often stored as **Windows-1252 (CP-1252)**. Modern stacks and tools (including OpenRewrite) expect **UTF-8** text. This folder contains a small **Python 3** utility that:

1. **Reads** each file as **CP-1252** and **writes UTF-8** (optional).
2. **Reports** every **non-ASCII** character (code point U+0080 and above) with **file path, line, column, and offset**.
3. **Classifies** (heuristic) whether that character sits in a **comment**, **string/char literal**, or **code** — so you can see whether a change is likely **compile-neutral** vs needs review.

**Important:** CP-1252 decodes every byte to a Unicode character; there is usually **no** “missing” character unless the file is **not** really CP-1252 (mixed UTF-8, binary, etc.). In that case the decoder may insert **U+FFFD**; the report flags that. Use **`--replace-undecodable-with-space`** to turn U+FFFD into a space after inspection.

## Requirements

- **Python 3.9+** (stdlib only; no `pip` packages required).

**Decoding:** By default each file is read as **UTF-8 (strict)** first. If that fails, the file is read as **CP-1252**. That way already-migrated UTF-8 sources are not misinterpreted. To scan a tree that is **only** legacy CP-1252 on disk, use **`--assume-cp1252-only`**.

## Report-only (recommended first)

```bat
python convert_cp1252_to_utf8.py --root C:\path\to\legacy-webapp
```

This creates a folder like `charset-migration-report-<timestamp>` under `--root` with:

| File | Content |
|------|---------|
| `findings.csv` | Spreadsheet-friendly report |
| `findings.json` | Same data for tooling |
| `summary.txt` | Counts and paths |

## Convert files to UTF-8

Back up originals with suffix `.cp1252.bak` and overwrite with UTF-8:

```bat
python convert_cp1252_to_utf8.py --root C:\path\to\legacy-webapp --write
```

Dry-run (no writes) but still emit reports:

```bat
python convert_cp1252_to_utf8.py --root C:\path\to\legacy-webapp --write --dry-run
```

Optional UTF-8 **BOM** (usually **not** needed for Java sources):

```bat
python convert_cp1252_to_utf8.py --root C:\path\to\src --write --utf8-bom
```

## Compile-impact column (heuristic)

| `compile_impact` | Meaning |
|------------------|---------|
| `low_comment_only` | Character is inside a **comment** (Java) or **`.properties`** comment / **`.md`** text — usually **no** compile impact. |
| `medium_string_or_char` | Inside **string/char literal** (Java) or **quoted** span (XML-like) or **value** side of `.properties` — may affect **runtime** or **display**. |
| `high_review_code_or_markup` | Outside those regions (or **unknown** for `.js/.css` etc.) — **review** before automation. |

**Not** a full Java/XML parser: edge cases (annotations, regex, nested templates) can be misclassified. **Sort** `findings.csv` by `compile_impact` and `path` for manual fixes before running OpenRewrite.

## Limiting scope

```bat
python convert_cp1252_to_utf8.py --root C:\src --include "*.java" --report-dir C:\reports\run1
```

Exclude patterns:

```bat
python convert_cp1252_to_utf8.py --root C:\src --exclude "**/generated/**" --exclude "**/test/**"
```

## OpenRewrite workflow

1. Run this tool **report-only** on the module.
2. Fix or accept **high** / **medium** rows (especially in identifiers and strings).
3. Run **`--write`** to normalize encoding to UTF-8.
4. **Commit** the conversion, then run OpenRewrite recipes on **UTF-8** sources.
