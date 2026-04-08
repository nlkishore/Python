# Turbine Migration Dual-Build Project

This project provides a **multi-module Maven skeleton** to support migration from:

- **JDK 8 + Java EE + Spring 4 + older Turbine/Torque**
to
- **JDK 17 + Jakarta EE + Spring 6 + Turbine 7 + Torque 7**

Modules included:

- `com.misys.portal`
- `com.misys.portal.api`
- `com.misys.portal.webapp`
- `com.misys.portal.report`
- `com.misys.portal.jetspeed`
- `com.misys.portal.common`
- `com.misys.portal.interfaces`

## Profiles

- `copy-and-legacy-build`
  - Copies current sources to working folder (`target/migration-work/...`)
  - Runs `maven-antrun-plugin` generation placeholder from XML
  - Compiles with `--release 8`
- `legacy-compile-only`
  - Compiles with `--release 8`
  - Does **not** copy sources
  - Does **not** run Ant generation
- `rewrite-migrate`
  - Runs OpenRewrite recipes for Jakarta/Spring/Turbine/Torque migration
- `modern-build`
  - Runs generation placeholder from XML
  - Compiles with `--release 17`

## Intended migration sequence

### 1) Copy sources to working folder (copy profile)

From project root:

```bash
mvn -Pcopy-and-legacy-build -DskipTests generate-sources
```

This uses `maven-resources-plugin` to copy `src/main/java` to:

- `${module}/target/migration-work/src/main/java`

### 2) Generate Java classes from XML

Also covered in `generate-sources` by `maven-antrun-plugin` execution:

- output folder: `${module}/target/generated-sources/xml`

> Replace the Ant `<echo>` placeholder in parent `pom.xml` with your actual XML -> Java generation tasks (XJC, custom generator, etc.).

### 3) Compile with JDK 8 / Java EE stack

```bash
mvn -Plegacy-compile-only -DskipTests clean compile
```

### 4) Run OpenRewrite migration

Dry-run:

```bash
mvn -Prewrite-migrate rewrite:dryRun
```

Apply:

```bash
mvn -Prewrite-migrate rewrite:run
```

The profile references recipe IDs:

- `com.misys.rewrite.turbine7.upgrade`
- `com.misys.rewrite.torque7.upgrade`
- `com.misys.rewrite.jakarta.upgrade`
- `com.misys.rewrite.spring6.upgrade`

Update these IDs to match your actual recipe names in your rewrite YAML files.

### 5) Compile with JDK 17 / Jakarta stack

```bash
mvn -Pmodern-build -DskipTests clean compile
```

## Operating modes (important)

This project supports two usage modes:

### Mode A: First-time setup flow (full sequence)

Use this when you are initializing migration for a module/repository, or when you explicitly need to refresh copied sources.

1. **Copy resources + run Ant generation + legacy checks**
2. **Compile on JDK 8 / Java EE profile**
3. **Apply OpenRewrite migration**
4. **Compile on JDK 17 / Jakarta profile**

Recommended commands:

```bash
# Step A1 + A2 (copy + ant + compile with legacy profile)
mvn -Pcopy-and-legacy-build -DskipTests clean compile

# Step A3 (rewrite dry run first)
mvn -Prewrite-migrate rewrite:dryRun

# Step A3 apply
mvn -Prewrite-migrate rewrite:run

# Step A4 (modern compile)
mvn -Pmodern-build -DskipTests clean compile
```

### Mode B: Repeat migration flow (no copy unless explicitly requested)

After first-time setup, **do not copy sources again by default**.
Daily/iterative cycle should be:

1. Compile current state (legacy or current branch baseline)
2. Apply OpenRewrite recipes
3. Compile with JDK 17 / Jakarta profile

Recommended commands:

```bash
# Baseline compile (legacy profile, but no separate manual copy step)
mvn -Plegacy-compile-only -DskipTests compile

# Apply rewrite
mvn -Prewrite-migrate rewrite:run

# Compile modernized sources
mvn -Pmodern-build -DskipTests compile
```

## Explicit copy-source request behavior (enforced)

- Treat source-copy as an **explicit action**.
- Use `copy-and-legacy-build` only when requested (for example: "refresh from local repository", "re-seed migration work folder", or schema/source reset scenarios).
- For normal iterations, use `legacy-compile-only` to avoid accidental copy refresh.
- This behavior is now enforced by separate profiles in `pom.xml`.

## Project structure

```text
turbine-migration-dual-build/
  pom.xml                       (parent + profiles)
  README.md
  com.misys.portal/pom.xml
  com.misys.portal.api/pom.xml
  com.misys.portal.webapp/pom.xml
  com.misys.portal.report/pom.xml
  com.misys.portal.jetspeed/pom.xml
  com.misys.portal.common/pom.xml
  com.misys.portal.interfaces/pom.xml
```

## Notes for production usage

1. Replace placeholder dependencies with your exact legacy and modern BOM/dependency sets.
2. Replace the Ant placeholder with real generation logic.
3. Pin OpenRewrite plugin and recipe artifacts to tested versions.
4. Consider adding separate CI jobs:
   - explicit copy+legacy validation (`copy-and-legacy-build`)
   - daily baseline compile (`legacy-compile-only`)
   - rewrite run + modern compile (`rewrite-migrate,modern-build`)
5. Keep migration commits small:
   - source copy/gen adjustments
   - rewrite namespace changes
   - final compile fixes
