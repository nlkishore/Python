# OpenRewrite: Torque 3.x → 7.x recipes, constraints, and manual backlog

This document pairs **[TORQUE-3-TO-7-UPGRADE-SUMMARY.md](./TORQUE-3-TO-7-UPGRADE-SUMMARY.md)** (see also `C:\Turbineprojects\TorqueFW\TORQUE-3-TO-7-UPGRADE-SUMMARY.md`) with OpenRewrite assets under **`C:\openRewrite`**.

---

## 1. Recipe file and names

| File | Purpose |
|------|---------|
| [rewrite-torque3-to-7-webapp.yml](./rewrite-torque3-to-7-webapp.yml) | Torque-oriented recipes (standalone copy; **keep in sync** with `rewrite.yml` entries). |
| [rewrite.yml](./rewrite.yml) | Also registers the same recipes (after `JavaxToJakartaNamespaces` / Turbine blocks). |

### 1.1 `com.uob.openrewrite.Torque3To7WithJakartaWebTier`

- **Transforms:** Delegates to **`com.uob.openrewrite.JavaxToJakartaNamespaces`** (same as other web-modernization recipes here).
- **Use when:** The module is a **WAR** or contains **servlets/JSP** alongside Torque.
- **Does not:** Upgrade Torque **generator output**, fix **Village**, or change **Criteria** semantics.

### 1.2 `com.uob.openrewrite.Torque3To7OptionalNewCriteriaPackage` (**high risk**)

- **Transforms:** `ChangeType` from `org.apache.torque.util.Criteria` → `org.apache.torque.criteria.Criteria`, then unused-import removal and `AutoFormat`.
- **Why risky:** Apache documents **behavior differences** (OR/AND, string arguments, **`Criteria.CUSTOM`** removal, **`doDelete(Criteria)`** table resolution). A mechanical rename **will compile in some projects** and **silently break** others.
- **Use when:** You have **already** analyzed each callsite or plan immediate test-driven fixes. Prefer **staying on** deprecated `util.Criteria` on Torque 7 until queries are ported deliberately.

### 1.3 `com.uob.openrewrite.Torque3To7ManualBacklog` (**detection only**)

- **FindTypes** for Torque 3–era APIs: `util.Criteria`, `criteria.Criteria`, `BasePeer`, `VillageUtils`, `MapBuilder`, `Torque`, `Transaction`, and common **`com.workingdogs.village.*`** types.
- **Text search** (`org.openrewrite.text.Find`) for:
  - `com.workingdogs.village` (any remaining references),
  - `Criteria.CUSTOM` (must be redesigned for **new** `Criteria`),
  - `andVerbatimSql` / `orVerbatimSql` (signals migration work or new API usage).

**No source edits.** Run with **`exportDatatables=true`** on `rewrite-maven-plugin` to feed spreadsheets or tickets.

---

## 2. How to run (Maven)

From a project configured with `configLocation` pointing at **`rewrite.yml`** (or a file that includes these recipes):

```text
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run -DactiveRecipes=com.uob.openrewrite.Torque3To7ManualBacklog
```

```text
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run -DactiveRecipes=com.uob.openrewrite.Torque3To7WithJakartaWebTier
```

```text
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run -DactiveRecipes=com.uob.openrewrite.Torque3To7OptionalNewCriteriaPackage
```

**Plugin classpath:** `rewrite-migrate-java` is required for **`JavaxToJakartaNamespaces`**. Text recipes need a plugin classpath that includes **OpenRewrite text** support (typically bundled with the plugin version you use); if `org.openrewrite.text.Find` fails, use **`grep`** / IDE search for the same strings.

---

## 3. Constraints — what OpenRewrite cannot safely automate

| Area | Why manual / backlog |
|------|----------------------|
| **Village removal** | Torque 7 runtime **does not use Village**. Replacements depend on **regenerated peers** and application logic—no universal AST rewrite. |
| **`VillageUtils` / Village types** | Detection only; each callsite must be **redesigned** against Torque 7 APIs. |
| **Code generation** | **Schema XSD**, **templates**, **Maven Torque plugin** / **Ant tasks**, and **output directories** are build concerns, not Java-only refactors. |
| **Peer / OM / MapBuilder regeneration** | Generated files should be **produced** by Torque 7 generator; hand-merge is **error-prone**. |
| **`util.Criteria` → `criteria.Criteria`** | **Semantic** migration per [Migration from Torque 3](https://db.apache.org/torque/torque-7.0/documentation/orm-reference/migration-from-torque-3.html). Optional recipe is **opt-in** and **unsafe** without tests. |
| **Inner types** | e.g. old **`Criteria.Criterion`**, **`Criteria.Join`** may not map 1:1 to new `Criteria` types—**compiler** will flag; fix **by hand**. |
| **`null` `Connection` behavior** | Runtime change; requires **code audit**, not a simple rename. |
| **Column-as-string vs `Column` / `ColumnImpl`** | Structural API change for dynamic column handling. |
| **XML / properties** | `Torque.properties`, datasource config, Turbine **`componentConfiguration.xml`**, Spring XML, etc. |
| **Dependencies** | `pom.xml` / Gradle coordinates for **torque-runtime**, **generator**, **JDBC**—use BOMs and release notes. |
| **JSP / taglibs** | Jakarta JSP/JSTL if moving to Servlet 5+; not covered by Torque recipes alone. |

---

## 4. Suggested workflow

1. Run **`Torque3To7ManualBacklog`** and archive the datatable / search results.  
2. Fix **schema** and **build** to **Torque 7**; **regenerate** all Torque artifacts.  
3. Remove **Village** usage guided by backlog hits.  
4. Run **`Torque3To7WithJakartaWebTier`** on web modules if applicable.  
5. Only then consider **`Torque3To7OptionalNewCriteriaPackage`**, with a **full regression** suite.  
6. **Never** rely on OpenRewrite alone for end-to-end Torque upgrades.

---

## 5. Reference binaries note

Under **`C:\Turbineprojects\TorqueFW`**, **Torque 3.3** documentation is present; the **`torque-runtime-7.0-bin`** tree may be **incomplete** (license-only). Treat **Maven Central** / official distributions as authoritative for **Torque 7** JARs and exact APIs.

---

## 6. Keeping files in sync

When editing recipes, update **both** [rewrite-torque3-to-7-webapp.yml](./rewrite-torque3-to-7-webapp.yml) and the **Torque `---` sections** in [rewrite.yml](./rewrite.yml).
