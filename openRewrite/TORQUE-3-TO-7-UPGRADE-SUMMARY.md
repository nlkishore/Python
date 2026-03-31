# Apache Torque 3.x → 7.x: Differences and web application migration

*Canonical copy also maintained at `C:\Turbineprojects\TorqueFW\TORQUE-3-TO-7-UPGRADE-SUMMARY.md`.*

This note combines **material in the TorqueFW workspace** with the **official Torque 7 migration guide** ([Migration from Torque 3](https://db.apache.org/torque/torque-7.0/documentation/orm-reference/migration-from-torque-3.html)).

## Reference layout under `C:\Turbineprojects\TorqueFW`

| Artifact | Location | Notes |
|----------|----------|--------|
| **Torque 3.3** | `torque-3.3/torque-3.3/` | Full distribution with **Javadoc** (`docs/apidocs/`), Ant `master/`, tests. Use for **Torque 3.3 API** reference (`org.apache.torque.util.Criteria`, `VillageUtils`, etc.). |
| **Torque 7 runtime (incomplete here)** | `torque-runtime-7.0-bin/torque-runtime-7.0/` | Currently contains **NOTICE / LICENSE** only. For **Torque 7** JARs and generated-runtime behavior, use **Maven Central** (`org.apache.torque:torque-runtime` and related modules) or a complete binary download. |

---

## 1. Executive summary (3.x → 7.x)

Torque **7.x** builds on **Torque 4+** changes. There is **no full ground-up API redesign** versus Torque 3, but **runtime semantics**, **generator tooling**, and **deprecated types** matter for a correct upgrade.

| Area | Torque 3.x | Torque 4+ / 7.x | Typical web app impact |
|------|------------|------------------|-------------------------|
| **Criteria** | `org.apache.torque.util.Criteria` | **New** `org.apache.torque.criteria.Criteria` recommended; **old** `util.Criteria` remains but is **deprecated** (same Torque 3.3 semantics) | Staying on **old** `Criteria` is valid short-term on Torque 7; switching package is **not** a pure rename—**behavior differs** (see below). |
| **Village** | Runtime uses **Village** (`com.workingdogs.village.*`); helpers e.g. `org.apache.torque.util.VillageUtils` | **Runtime does not use Village** | **High**: any direct Village usage or peer code depending on Village must be **rewritten** to Torque 7 patterns (often **regenerated peers** + different data access). |
| **Column names** | String-based column naming in many APIs | Column names represented by **`org.apache.torque.Column`**; generated peer constants follow new model | **Medium** if you build `Criteria` / SQL from **raw strings**—may need **`ColumnImpl`** or generated column types. |
| **Connections** | Passing **`null`** for a connection could be auto-handled | **`null` connection is an error** | **Medium**: audit `doSelect`, `doInsert`, `doUpdate`, `doDelete`, and custom peer calls. |
| **`Criteria.CUSTOM`** | `Criteria.CUSTOM` operator | **Removed** on **new** `criteria.Criteria`; use **`andVerbatimSql()`** / **`orVerbatimSql()`** | **High** when migrating to **new** `Criteria`. |
| **OR / AND semantics** | Legacy `util.Criteria` behavior | **New** `criteria.Criteria`: different rules for **or** methods; **first-arg `String`** handling differs (literal vs column) | **High** for complex dynamic queries—must re-read Javadoc and retest. |
| **`doDelete(Criteria)`** | Table inferred from criteria contents | With **new** `criteria.Criteria`, table is the **peer’s** table | **High** for deletes built from generic criteria. |
| **Generator** | Ant-centric / older generator layout | **General-purpose generator**; **templates must be configured** (Maven plugin, Ant tasks, template docs) | **High**: regenerate **`BasePeer`**, `Peer`, `MapBuilder`, `Record`/`Object` classes; update **build** (`pom.xml` / Ant `torque-ant-tasks`). |
| **Schema** | Torque 3 schema | Validate against **Torque 4+ XSD**; see project docs / JIRA **TORQUE-126** subtasks for typical fixes | **Medium–high** before codegen. |
| **JDK / supported DBs** | Older JDK (3.3 era) | Torque 4+ requires at least **Java 5+** historically; **Torque 7** aligns with modern JDKs (use release notes for your exact 7.x) | Align **JDK**, JDBC drivers, and container. |

---

## 2. Web application–specific work

A **WAR** using Torque 3.x usually combines:

1. **Generated** Torque sources (peers, OM, maps) from an older generator.  
2. **Hand-written** services/actions using `Criteria`, `BasePeer`, `Transaction`, Village types, or `MapBuilder`.  
3. **Integration** with a framework (e.g. **Apache Turbine**) via **Torque component** configuration (`Torque.properties` / `schema.xml` paths / datasource).  
4. Sometimes **JSP/servlet** code using `javax.*` (→ **Jakarta** on Servlet 5+ stacks).

**Upgrade order (practical):**

1. Read official **Migration from Torque 3** and the **changes report** for your target **7.x** version.  
2. Fix **schema** to pass Torque 4+ validation; **regenerate** all Torque artifacts with **Torque 7** generator + **explicit templates**.  
3. Bump **Maven/Gradle** coordinates to **Torque 7** runtime + generator + plugin versions.  
4. **Remove or replace Village** usage; replace `VillageUtils`-style patterns.  
5. Decide **per module** whether to keep **`org.apache.torque.util.Criteria`** temporarily or migrate to **`org.apache.torque.criteria.Criteria`** with **semantic** fixes.  
6. Audit **`null`** `Connection` usage.  
7. If the app is on **Jakarta EE 9+**, run **javax → jakarta** migration for servlet/JSP code (separate from Torque ORM).  
8. **Regression-test** CRUD, transactions, reporting queries, and delete-by-criteria.

---

## 3. OpenRewrite vs manual work

- **Automatable (with caveats):** Jakarta package migrations in **application** Java; optional **type rename** `util.Criteria` → `criteria.Criteria` that **compiles** but may **change behavior**—treat as **opt-in** only.  
- **Not safely automatable:** Village removal, generator/template upgrades, schema XSD fixes, semantic Criteria changes, peer regeneration, datasource/`Torque.properties` migration, and most **XML** / **build** edits.

See **[OPENREWRITE-TORQUE3-TO-7-RECIPE-AND-CONSTRAINTS.md](./OPENREWRITE-TORQUE3-TO-7-RECIPE-AND-CONSTRAINTS.md)** for recipes and a **manual backlog** checklist.

---

## 4. References

- [Migration from Torque 3 (Torque 7.0 docs)](https://db.apache.org/torque/torque-7.0/documentation/orm-reference/migration-from-torque-3.html)  
- [Torque 7 tutorial / ORM reference](https://db.apache.org/torque/torque-7.0/documentation/tutorial/index.html)  
- [Criteria (torque-runtime) Javadoc on javadoc.io](https://javadoc.io/doc/org.apache.torque/torque-runtime/latest/org/apache/torque/criteria/Criteria.html)  
- Local **Torque 3.3** API: `torque-3.3/torque-3.3/docs/apidocs/overview-summary.html`

---

*Workspace note: complete **Torque 7** binaries should be obtained from Maven or a full distribution if `torque-runtime-7.0-bin` is incomplete.*
