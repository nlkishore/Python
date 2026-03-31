# OpenRewrite Jakarta Migration Runner (Copy Sources → Rewrite → Compile)

This folder contains a small Maven runner that:

1. **Copies Java sources** from a configured legacy location into this build workspace
2. Runs **OpenRewrite** to migrate **`javax.*` → `jakarta.*`** (Servlet/JMS/Transaction/JAXB + companions)
3. **Compiles** the migrated sources on **JDK 17** with Jakarta dependencies

---

## Files

- `pom.xml`
  - Copies sources during `generate-sources`
  - Activates OpenRewrite recipe: `com.uob.openrewrite.JavaxToJakartaNamespaces`
  - Compiles with Java 17 (`maven.compiler.release=17`)
- `rewrite.yml`
  - Composite recipe: built-in `JavaxMigrationToJakarta` + explicit package mappings

---

## Prerequisites

- JDK 17 installed and active
- Maven installed (`mvn` in PATH)
- Network access to Maven Central (or your internal Nexus/Artifactory proxy)

---

## Configure source copy path

Edit `pom.xml` and set the legacy Java source directory:

- `src.input.dir` (example currently: `C:/path/to/legacy/src/main/java`)

The copied sources are written to:

- `target/generated-sources/migrated`

---

## Commands (run from `C:\openRewrite`)

### 1) Copy sources + run OpenRewrite + compile

```bash
mvn -U generate-sources rewrite:run compile
```

### 2) (Optional) Dry-run OpenRewrite first (no file changes)

```bash
mvn -U generate-sources rewrite:dryRun
```

### 3) Re-run only compile (after rewrite)

```bash
mvn -U compile
```

---

## What gets migrated

`rewrite.yml` includes:

- `javax.servlet` → `jakarta.servlet`
- `javax.jms` → `jakarta.jms`
- `javax.transaction` → `jakarta.transaction`
- `javax.xml.bind` → `jakarta.xml.bind`

Plus common companion namespaces often used in enterprise code:

- `javax.annotation` → `jakarta.annotation`
- `javax.ws.rs` → `jakarta.ws.rs`
- `javax.persistence` → `jakarta.persistence`
- `javax.validation` → `jakarta.validation`
- `javax.activation` → `jakarta.activation`

---

## Notes / troubleshooting

- **Compilation failures after rewrite** usually mean you need additional Jakarta dependencies
  (e.g., `jakarta.mail`, `jakarta.xml.soap`, etc.) depending on what `javax.*` APIs your legacy sources used.
- If your code depends on an application server API, many Jakarta APIs should remain `scope=provided`.
- OpenRewrite results and datatables (if produced) will be under the Maven `target/` directory.

