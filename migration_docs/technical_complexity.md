# Technical Complexity Analysis: Jetspeed/Turbine/Torque Migration

## 1. Categorization of Dependencies & Complexities

### A. Core Frameworks (High Complexity)
| Component | From | To | Complexity | Key Challenges |
| :--- | :--- | :--- | :--- | :--- |
| **Jetspeed** | 1.x | N/A | **Critical** | Incompatible with Servlet 5.0 (Jakarta). Requires complete rewrite/replacement. |
| **Turbine** | 2.x/3.x | 7.0 | High | Pipeline changes, Action/Screen signature changes, genericized APIs. |
| **Torque** | 3.x | 6.x | High | Removal of Village, change in connection/transaction management (`Transaction` object vs static `Transaction.begin`). |

### B. Data Layer (Torque/Village)
*   **`com.workingdogs.village.*`**: COMPLETE REMOVAL.
    *   **Impact**: Any code iterating over `Record` objects or using `Value` directly will break.
    *   **Remediation**: Must replace with JDBC `ResultSet` handling or Torque `List<DataObject>`.
*   **Custom SQL**: Code using `BasePeer.executeQuery` returning Village Records must be rewritten to use `Torque.executeQuery` returning Lists or custom mappers.
*   **MapBuilders**: Removed. Metadata is now handled differently (Peer classes).

### C. Third-Party Libraries (Medium Complexity)
| Library | Issue | Resolution |
| :--- | :--- | :--- |
| **Castor** | XML serialization | Upgrade to Castor 1.4+ or JAXB. Check Jakarta support. |
| **Log4j 1.x** | EOL / Security | Migrated to Log4j 2.x (API changes required). |
| **Commons-*** | Version mismatch | Upgrade to latest `commons-lang3`, `commons-configuration2`. API changes expected. |
| **Velocity** | 1.x -> 2.x | Syntax is mostly compatible, but configuration and tools (Context) have changed. |

## 2. Compilation vs. Runtime Risks

### Compilation Errors (Estimated Count: 1000+)
*   **Imports**: `javax.servlet` -> `jakarta.servlet` (Easy, Automated).
*   **Torque Generated Classes**: Methods removed/renamed (Medium, Regenerate).
*   **Village Usage**: Missing classes (Hard, Manual Refactor).
*   **Interface Implementation**: `Turbine` Action interfaces adding generic types (Medium, Manual).

### Runtime Risks
*   **ClassLoading**: Jetspeed 1.x often relied on complex custom classloaders which JDK 9+ modules (JPMS) may block.
*   **JNDI/DataSource**: Jakarta EE changes how DataSources are looked up.
*   **Session Serialization**: Updated libraries may not deserialize old session objects (if rolling upgrade attempted).
*   **Velocity Templates**: Macros might fail silently if deprecated syntax was used.

## 3. Torque Upgrade Options Analysis

### Option 1: Regenerate Stubs (Recommended)
*   **Process**: Run Torque 6 Generator.
*   **Outcome**: Clean code, compile errors in business logic only.
*   **Risk**: High initial volume of errors, but "Correct by Construction" once fixed.

### Option 2: Reuse Old Stubs + Adapters (Not Recommended)
*   **Process**: Keep old `Base*` classes, modify them to call new Torque 6 APIs.
*   **Issue**: Torque 6 expects specific internal state in runtime objects that old stubs won't have.
*   **Verdict**: Likely impossible for a large project. The "Adapter" logic would effectively be rewriting the Generator.

## 4. Missing Classes in Torque 7
*   **`MapBuilder`**: Gone. Logic moved to `Peer` classes.
    *   *Fix*: Update `Torque.properties` to not reference MapBuilders. Use `Peer.getTableMap()` if needed.
*   **`BaseObject`**: Replaced by an Interface or different base class in Torque 6.
    *   *Fix*: Update 3rd party code to use the Interface.
*   **`Village`**: Gone.
    *   *Fix*: See Automation Script in `village_refactor.py`.

