# Legacy Turbine/Torque Jakarta Compatibility Pack

This folder provides a practical OpenRewrite-based starter for migrating a legacy Turbine/Torque web application from Java EE to Jakarta EE on JDK 17.

It is focused on three asks:

1. Identify third-party libraries that still depend on Java EE (`javax.*`)
2. Define a path to make those libraries compatible with Jakarta EE
3. Provide additional recommendations to find migration gaps early

## Folder contents

- `rewrite-jakarta-compatibility.yml`  
  OpenRewrite recipes for dependency discovery and code migration.
- `analyze_javaee_dependencies.py`  
  Python report generator from Maven dependency tree output.
- `compatibility-mapping-template.csv`  
  Working template to track each library and compatibility decision.

## 1) Identify libraries with Java EE dependency

### A. Source/API usage scan (OpenRewrite)

Run this recipe to detect direct `javax.*` usage in source:

`com.company.migration.FindJavaEeApisInCode`

This will produce OpenRewrite data tables showing where `javax` APIs are used.

### B. Maven dependency scan (OpenRewrite)

Run this recipe to identify known Java EE related dependencies:

`com.company.migration.FindJavaEeDependencies`

It searches for typical Java EE coordinates (for example: `javax.servlet`, `javax.persistence`, `javax.validation`, `javax.ws.rs`, `javax.xml.bind`, `javax.annotation`).

### C. Full dependency tree scan (Python helper)

1. Generate dependency tree from your project root:
   - `mvn -q -DskipTests dependency:tree -DoutputFile=target/dependency-tree.txt`
2. Run:
   - `python analyze_javaee_dependencies.py --tree-file target/dependency-tree.txt --out-dir target/jakarta-compat-report`

Outputs:

- `target/jakarta-compat-report/javaee_dependency_report.csv`
- `target/jakarta-compat-report/javaee_dependency_report.json`

## 2) Path to make Java EE-dependent libraries Jakarta compatible

Use this decision path per library:

1. **Upgrade in place first**  
   Check if vendor already ships a Jakarta-compatible version.
2. **Replace if no Jakarta release**  
   Move to equivalent maintained library that supports Jakarta EE / JDK 17.
3. **Bridge only as temporary fallback**  
   Keep old library isolated and use compatibility bridges only short-term.
4. **Refactor custom integration points**  
   Legacy Turbine/Torque extensions often need custom code updates beyond package rename.

Track each dependency in `compatibility-mapping-template.csv` with:

- Current GAV
- Java EE API used
- Target Jakarta-compatible version or replacement
- Migration action (`upgrade`, `replace`, `remove`, `manual`)
- Risk and owner

## 3) Other recommendations to detect gaps

- Run `jdeps --jdk-internals --recursive` on built artifacts to detect JDK-internal usage that breaks on Java 17.
- Run `jdeprscan --release 17` to flag deprecated-for-removal APIs.
- Add duplicate class and dependency convergence checks in CI (`maven-enforcer-plugin`).
- Validate runtime on Jakarta container (Tomcat 10+) early, not only compile-time checks.
- Keep migration staged: dependency upgrades first, namespace migration next, framework-specific refactor last.

## Suggested migration sequence

1. Run discovery recipes (`FindJavaEeDependencies`, `FindJavaEeApisInCode`).
2. Generate dependency report via Python helper.
3. Fill `compatibility-mapping-template.csv` and approve decisions.
4. Run namespace/dependency migration recipe (`MigrateJavaEeToJakartaBaseline`).
5. Compile on JDK 17 and fix remaining manual hotspots.
6. Execute integration tests on target runtime.

## Sample OpenRewrite run

From your project root:

`mvn -Drewrite.configLocation=C:/openRewrite/jakarta-compatibility-rewrite/rewrite-jakarta-compatibility.yml -Drewrite.activeRecipes=com.company.migration.FindJavaEeDependencies,com.company.migration.FindJavaEeApisInCode org.openrewrite.maven:rewrite-maven-plugin:run`

Then apply migration recipe when ready:

`mvn -Drewrite.configLocation=C:/openRewrite/jakarta-compatibility-rewrite/rewrite-jakarta-compatibility.yml -Drewrite.activeRecipes=com.company.migration.MigrateJavaEeToJakartaBaseline org.openrewrite.maven:rewrite-maven-plugin:run`
