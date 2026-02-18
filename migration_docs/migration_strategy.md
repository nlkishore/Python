# Migration Strategy: Legacy Java App to JDK 17 & Jakarta EE

## Executive Summary
This document outlines the systematic approach for converting a Business As Usual (BAU) application based on **Jetspeed 1.x**, **Turbine 2.x/3.x**, and **Torque 3.x** to a modern stack comprising **JDK 17**, **Turbine 7.x**, and **Torque 6.x** (or 7.x).

> [!WARNING]
> **Jetspeed 1.x Critical Incompatibility**: Jetspeed 1.x is functionally incompatible with JDK 17 and Jakarta EE. It relies on Servlet 2.3/2.4 APIs which are removed in Jakarta EE. No simple upgrade path exists. A complete port to a modern portal framework (or converting to a standard Web App) is required.

## 1. Migration Paths

### 1.1 Turbine Upgrade (3.x -> 7.0)
Turbine 7.0 is the target version for JDK 17 and Jakarta EE support.
*   **Key Changes**:
    *   Package renaming: `javax.servlet` -> `jakarta.servlet`.
    *   Removal of deprecated utilities (Fulcrum replacements).
    *   Generics support in core APIs.
*   **Strategy**:
    *   Update `pom.xml` / `build.xml` dependencies.
    *   Run partial automated replacements for package names.
    *   Refactor Actions/Screens to implement the new Interface signatures.

### 1.2 Torque Upgrade (3.x -> 6.x/7.x)
Torque 6.x/7.x drops support for `com.workingdogs.village` entirely.
*   **Option 1: Regenerate Stubs (Recommended)**
    *   Update `schema.xml` to latest Torque DTD.
    *   Use `torque-maven-plugin` (or Ant task) generator from Torque 6.x to regenerate `Base*`, `Peer`, and `MapBuilder` classes.
    *   **Pros**: Guarantees compatibility with new Torque runtime; fixes hidden superclass issues.
    *   **Cons**: Compiles breaks everywhere initially.
*   **Option 2: Adapter / Manual Patching (Not Recommended)**
    *   Attempting to keep old stubs (`BaseObject`) and adapting them.
    *   **Risks**: Torque 6 architectural changes (transaction handling, column maps) are too deep. Old stubs will fail at runtime even if compiled.

### 1.3 Village (`com.workingdogs.village` Refactoring)
Since `village` is removed, code relying on `Record`, `Value`, or `Schema` objects must be refactored.
*   **Approach**: encapsulate all Village usage into a `LegacyDataUtil` or Repository layer before upgrade.
*   Implement the "Adapter Pattern" as requested:
    1.  Scan code for `com.workingdogs.village.*`.
    2.  Move logic to `VillageAdapter`.
    3.  Replace calls in BAU code to use `VillageAdapter`.
    4.  Switch `VillageAdapter` implementation to use standard JDBC or Torque 6 Criteria API.

## 2. Automation Capabilities
*   **Compilation Errors**: ~60% fixable via automation (imports, simple type changes).
*   **Logic Changes**: ~40% require manual intervention (transaction boundaries, removed methods, specific Village logic).
*   **Run-time Issues**: ClassCastExceptions, missing configuration keys, JNDI lookup failures.

## 3. Estimated Effort & Skill
*   **Skill Required**: Senior Java Developer (Expertise in Refactoring, JDBC, Legacy Frameworks).
*   **Effort**: High.
*   **Manual Effort**: Required for re-implementing business logic tied to Village types.

## 4. Specific Recommendations
*   **Missing Classes**: `MapBuilder` is deprecated/removed in favor of internal metadata. Remove references and rely on generated `Peer` static metadata.
*   **BaseObject**: Replaced by Torque equivalents. Do not try to keep the old source. Regenerate.

## 5. Proposed Workflow
1.  **Preparation**: Containerize existing app (Docker) to ensure we have a working reference.
2.  **Infrastructure**: Setup JDK 17, Tomcat 10 (Jakarta EE), DB.
3.  **Torque Upgrade**:
    *   Run `village_refactor` script (provided).
    *   Regenerate Torque OMs (Object Models).
    *   Fix compile errors in OMs.
4.  **Turbine Upgrade**:
    *   Update dependencies.
    *   Migrate `javax.*` to `jakarta.*`.
5.  **Jetspeed Remediation**:
    *   *Decision Point*: Rewrite Portal layer or strip Portal features.

