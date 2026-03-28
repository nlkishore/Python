# OpenRewrite: Turbine 4.x → 7.x web compatibility recipes and manual constraints

This document pairs the **reference upgrade analysis** ([TURBINE-4-TO-7-UPGRADE-SUMMARY.md](./TURBINE-4-TO-7-UPGRADE-SUMMARY.md), mirrored from `C:\Turbineprojects\TurbineFW`) with **OpenRewrite recipes** under `C:\openRewrite` and a clear list of **what automation cannot safely do** for Turbine upgrades.

---

## 1. Recipe files and recipe names

| File | Purpose |
|------|---------|
| [rewrite.yml](./rewrite.yml) | Primary OpenRewrite config for this folder: includes `com.uob.openrewrite.JavaxToJakartaNamespaces` plus **Turbine 4→7** recipes (same definitions as below). |
| [rewrite-turbine4-to-7-webapp.yml](./rewrite-turbine4-to-7-webapp.yml) | Standalone copy of the Turbine 4→7 recipes (useful to copy into another repo or to diff). **Keep in sync** with the `---` blocks appended to `rewrite.yml`. |

### 1.1 `com.uob.openrewrite.Turbine4To7WebCompatible` (transform)

**Intent:** Apply **deterministic** Java source changes that align a legacy Turbine-style web app with a **Turbine 7.x + Jakarta EE 9+** compile model.

**What it does:**

1. Runs **`org.openrewrite.java.migrate.jakarta.JavaxMigrationToJakarta`** (from `rewrite-migrate-java`).
2. Applies explicit **`javax.*` → `jakarta.*`** `ChangePackage` rules for servlet, JMS, transactions, JAXB, annotation, JAX-RS, persistence, validation, activation (same scope as `com.uob.openrewrite.JavaxToJakartaNamespaces`).
3. Applies **`ChangeType`** from `org.apache.turbine.util.TemplateInfo` → `org.apache.turbine.util.template.TemplateInfo` for mixed or legacy imports (harmless if the old FQCN does not exist in your sources).
4. **`RemoveUnusedImports`** and **`AutoFormat`**.

**What it does *not* do:** Anything listed in [Section 3](#3-constraints-openrewrite-cannot-replace-manual-work).

### 1.2 `com.uob.openrewrite.Turbine4To7ManualBacklog` (detection only)

**Intent:** Produce **search results / datatable rows** for code that almost always needs **human review** after moving to Turbine 7.

**What it does:**

- **`FindTypes`** for `AbstractValve`, `Turbine`, `TurbineServices`, `Action`, `Screen`, `Navigation`, `RunData` (with `matchInherited: true` where applicable).
- **`org.openrewrite.text.Find`** for the literal `createRuntimeDirectories` in `**/*.java` (flag for Turbine 4-style bootstrap that changed in Turbine 7).

**It does not modify sources.** Use with `exportDatatables` on the Maven plugin to feed a backlog CSV or ticket list.

---

## 2. How to run (Maven)

From `C:\openRewrite` (after pointing the project at real Java sources, not placeholder paths):

```text
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run -DactiveRecipes=com.uob.openrewrite.Turbine4To7WebCompatible
```

Detection-only:

```text
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run -DactiveRecipes=com.uob.openrewrite.Turbine4To7ManualBacklog
```

**Plugin classpath:** The parent [pom.xml](./pom.xml) declares **`rewrite-migrate-java`** for `JavaxMigrationToJakarta`. If `org.openrewrite.text.Find` fails to resolve at runtime, add the matching **`org.openrewrite.recipe` artifact** that provides text recipes for your `rewrite-maven-plugin` version, or remove the `Find` step from the detection recipe and rely on `grep` for `createRuntimeDirectories`.

**Dry run / patch:** Use OpenRewrite’s usual goals (`rewrite:dryRun`, `rewrite:run` with patch export) per [OpenRewrite docs](https://docs.openrewrite.org/).

---

## 3. Constraints: OpenRewrite cannot replace manual work

OpenRewrite excels at **namespace and type renames** on Java sources. A Turbine 4→7 move also needs **behavioral and platform** changes that are **unsafe or impossible** to encode as a generic recipe. Treat the following as **manual** (or as **project-specific** custom recipes after design review).

### 3.1 Custom pipeline valves (`AbstractValve` removal)

| Constraint | Reason |
|------------|--------|
| **No automatic `extends AbstractValve` → `implements Valve` fix** | Requires changing **inheritance vs implementation**, re-implementing `invoke`, and often inlining logic that lived in `AbstractValve`. A blind `ChangeType` can produce invalid Java (`extends Valve` vs `implements Valve`). |
| **Semantic behavior** | Helpers, exception handling, and `PipelineData` usage must match Turbine 7’s **`Valve`** contract and Jakarta types. |

**Manual:** Refactor each custom valve to **`implements org.apache.turbine.pipeline.Valve`**, adjust method signatures to **`jakarta.servlet`**, and compile against **`turbine-7.x`**.

### 3.2 Subclasses of `org.apache.turbine.Turbine` and bootstrap code

| Constraint | Reason |
|------------|--------|
| **`createRuntimeDirectories` → `configureApplication` / `Path`** | API and control flow changed between Turbine 4 and 7; this is a **rewrite**, not a rename. |
| **Jakarta JAXB and configuration loading** | Turbine 7 loads configuration with **Jakarta XML Binding**; custom init must be revalidated. |
| **Annotations** | Turbine 7 uses **`jakarta.servlet.annotation`** (`WebServlet`, `MultipartConfig`, etc.); merge with your deployment model (web.xml vs annotations). |

**Manual:** Reconcile custom `Turbine` subclasses with Turbine 7 source or Javadoc for your exact **7.x** patch level.

### 3.3 XML and non-Java resources

| Constraint | Reason |
|------------|--------|
| **`turbine-classic-pipeline.xml`** | Inserting **`DefaultSetEncodingValve`** at the correct position is a **structural XML merge**; doing it wrong breaks request processing. |
| **`componentConfiguration.xml` / `roleConfiguration.xml`** | Component class names and properties may differ across Fulcrum/Turbine versions; requires validation against target artifacts. |
| **`web.xml` / `web-fragment.xml`** | Servlet **5.0** schema, `metadata-complete`, and filter mappings need container-specific review. OpenRewrite’s Jakarta migration may help **some** descriptors, but **not** Turbine-specific semantics. |
| **JSP / taglibs** | JSTL and taglib URIs must match a **Jakarta**-compatible implementation; JSP is not covered by the Java recipes in this repo. |

**Manual:** Merge configs using Turbine 7 samples under `TurbineFW` (or your vendor baseline) and run integration tests.

### 3.4 Logging and operations

| Constraint | Reason |
|------------|--------|
| **`Log4j.properties` → Log4j 2 (`log4j2.xml`)** | Cross-cutting ops change; not a Java AST transform in application code. |

**Manual:** Adopt Log4j 2 (or your standard) and remove Log4j 1.x where required.

### 3.5 Build dependencies and runtime

| Constraint | Reason |
|------------|--------|
| **Maven/Gradle coordinates** | Bumping **`turbine`**, **Fulcrum**, **Torque**, **Commons Configuration 2**, JDBC drivers, and the **servlet container** is **build metadata**, not something this YAML set edits. |
| **Third-party JARs** | Libraries that still use **`javax.*`** must be upgraded or replaced; OpenRewrite only rewrites **your** sources unless you add recipes for those JARs (unusual). |
| **Database scripts** | Turbine 7 sample SQL in the reference tree may be **MySQL-only**; other DBs need DBA-owned migration. |

**Manual:** Use the official Turbine 7 BOM/POM and your application server’s Jakarta compatibility matrix.

### 3.6 Detection recipe noise

| Constraint | Reason |
|------------|--------|
| **`FindTypes` on `Turbine`, `RunData`, modules** | Flags **every** legitimate use—not only incompatible ones. Use as a **backlog hint**, not as proof of a defect. |
| **`Find` on `createRuntimeDirectories`** | May match comments or unrelated strings; verify each hit. |

---

## 4. Suggested workflow

1. Run **`Turbine4To7ManualBacklog`** (or `grep`/IDE) to inventory risk areas.  
2. Update **build** to Turbine 7 + Jakarta **provided** APIs and fix **dependency** conflicts.  
3. Run **`Turbine4To7WebCompatible`** on Java sources; review diff.  
4. Manually fix **valves**, **Turbine** subclasses, **XML**, **JSP**, **logging**.  
5. Run full **compile**, **unit**, and **integration** tests on a **Servlet 5+** runtime (e.g. Tomcat 10+).

---

## 5. Keeping recipes in sync

- **`rewrite-turbine4-to-7-webapp.yml`** and the **`---` Turbine sections** in **`rewrite.yml`** should stay aligned. If you edit one, edit the other (or maintain a single file and generate the second).

---

## 6. Related material

- [TURBINE-4-TO-7-UPGRADE-SUMMARY.md](./TURBINE-4-TO-7-UPGRADE-SUMMARY.md) — framework differences from TurbineFW binaries.  
- `C:\openRewrite\misys-openrewrite-template\rewrite\` — additional Turbine/Torque recipes (e.g. `rewrite-turbine7-upgrade.yml`, verified mapping table) if you use that template project.
