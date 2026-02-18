# Schema Construction & Database Mapping Guide

## 1. ID Generation Risks
When migrating from Torque 3 to 7, the `idMethod` configuration is critical.

### The "Native" vs "IDBroker" Problem
*   **Torque 3 (Legacy)**: Often used `idMethod="idbroker"`. This relied on a generic `ID_TABLE` in the database to dispense IDs. This is safe but slow and non-standard.
*   **Torque 7 (Modern)**: Prefers `idMethod="native"`.
    *   **PostgreSQL/Oracle**: Uses Sequences.
    *   **MySQL/SQL Server**: Uses Identity/Auto-Increment columns.

**Risk**: If your legacy database assumes an ID Broker table exists, but you switch to "native" in Torque 7, inserts will fail because Torque will try to ask the DB sequence instead of looking up the ID Broker table.
**Fix**: Check your legacy `schema.xml` or database.
*   If `ID_TABLE` exists -> You were using IDBroker.
*   **Recommendation**: Switch to Native Sequences if possible. It is much more performant.

### How to Check ID Method from Legacy Stubs
If you are unsure which ID method was used, check the generated `*MapBuilder.java` files (e.g., `AuthorMapBuilder.java`).

1.  **Open `AuthorMapBuilder.java`**.
2.  Search for `doBuild()` method.
3.  Look for `tMap.setPrimaryKeyMethod(...)`.
    *   `TableMap.ID_BROKER` -> **ID Broker** (Requires `ID_TABLE`).
    *   `TableMap.NATIVE` -> **Native** (Sequence/AutoIncrement).
    *   `TableMap.NONE` -> **None** (Manual ID assignment).

**Updated Automation**: The provided `schema_recover.py` now attempts to parse this automatically.

## 2. Data Type Mapping (Java <-> SQL)
Accurate mapping is essential to prevent `ClassCastException` or data truncation.

| Java Type | Torque 3 `generic` | Torque 7 (Target) | DB Column (Example) | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `int` / `Integer` | `INTEGER` | `INTEGER` | `NUMBER(10)` / `INT` | Standard. |
| `long` / `Long` | `BIGINT` | `BIGINT` | `NUMBER(19)` / `BIGINT` | **Watch out**: IDs > 2 billion must use BIGINT. |
| `String` | `VARCHAR` | `VARCHAR` | `VARCHAR2` / `TEXT` | **Size matters**. define `size="255"` in schema if unsure. |
| `java.util.Date` | `TIMESTAMP` | `TIMESTAMP` | `TIMESTAMP` / `DATETIME` | Torque 7 is stricter about util.Date vs sql.Timestamp. |
| `BigDecimal` | `DECIMAL` | `DECIMAL` | `NUMBER(10,2)` | Essential for currency. Define scale/precision. |
| `boolean` | `BOOLEANINT` | `BOOLEANINT` | `NUMBER(1)` | Many legacy DBs store booleans as 0/1. Use `BOOLEANINT` or `BOOLEANCHAR` (Y/N). |

## 3. The "Schema vs Database" Gap
Functional gaps often occur when the Schema defines constraints that the Database does not (or vice versa).

*   **Required Fields**: If schema says `required="true"` but DB allows `NULL`, Torque generated code will throw Exceptions before even talking to the DB.
    *   *Rule*: Relax the schema (`required="false"`) if the DB allows NULLs.
*   **Foreign Keys**: Torque generates Java code for `getRelatedObject()`.
    *   *Risk*: If `foreign-key` tags are missing in `schema.xml`, you lose these convenience methods.
    *   *Recovery*: The automation script **cannot** recover Foreign Keys easily. You must manually check for `INT` columns that refer to other tables (e.g., `AUTHOR_ID` in `BOOK` table).

## 4. Automation Script Usage
The provided `schema_recover.py` is a **heuristic tool**.
1.  **Run it** against your legacy source code.
2.  **Review** the `recovered_schema.xml`.
3.  **Manual Adjustments**:
    *   Add `primaryKey="true"` where missed.
    *   Add `autoIncrement="true"` for ID columns.
    *   Add `<foreign-key>` relationships (Context specific).
    *   Verify `size=""` attributes for VARCHARs.
