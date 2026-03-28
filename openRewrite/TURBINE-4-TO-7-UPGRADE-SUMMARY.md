# Apache Turbine 4.x → 7.x: Framework differences and web app upgrade notes

*This file is a copy of the reference guide for the OpenRewrite workspace (`C:\openRewrite`). Canonical Turbine binary trees: `C:\Turbineprojects\TurbineFW\`.*

This summary is derived from the **reference binaries** under the TurbineFW folder:

| Version | Path (reference) |
|--------|------------------------|
| Turbine **4.0** | `turbine-4.0-binaries/turbine-4.0/` (e.g. `turbine-4.0.jar`) |
| Turbine **7.0** | `turbine-7.0-binaries/turbine-7.0/` (e.g. `turbine-7.0.jar`) |

It focuses on **what changed in the framework** and **what you must change** in a **Turbine 4.x–based web application** (Java, `WEB-INF`, Fulcrum/Torque integration, custom valves/modules) to run on **Turbine 7.x** on a **Jakarta EE 9+ / Servlet 5+** stack.

---

## 1. Executive summary

| Area | Turbine 4.x (reference jar) | Turbine 7.x (reference jar) | Upgrade impact |
|------|----------------------------|----------------------------|----------------|
| **Servlet API** | `javax.servlet.*` | `jakarta.servlet.*` | **High**: all app code, filters, JSP taglibs, and dependencies must use Jakarta; app server must be Servlet 5+ (e.g. Tomcat 10+, Jetty 11+, EE 9+). |
| **Bootstrap / `Turbine` servlet** | Extends `javax.servlet.http.HttpServlet`; uses `createRuntimeDirectories` in `configure` | Extends `jakarta.servlet.http.HttpServlet`; uses `configureApplication` → `java.nio.file.Path`; loads config with **Jakarta JAXB** (`jakarta.xml.bind.*`) | **High**: custom subclasses of `Turbine`, or code that mirrors its init, must be rewritten against Jakarta types and the new configuration/bootstrap APIs. |
| **Request encoding** | Character encoding handled in **`Turbine.doGet`** before `RunData` | **`DefaultSetEncodingValve`** runs **first** in the sample classic pipeline | **Medium**: if you relied on timing/order of encoding vs valves, align with the new valve; ensure `turbine-classic-pipeline.xml` includes encoding valve if you use the stock pipeline. |
| **Pipeline valves** | Built-in valves extend **`AbstractValve`** | Built-in valves **implement `Valve` directly**; **`AbstractValve` is not present** in the 7.0 jar | **High** for custom valves: subclasses of `AbstractValve` must be refactored to implement `Valve` (and replicate any helper behavior manually or via composition). |
| **Sample classic pipeline** | No `DefaultSetEncodingValve` | **`DefaultSetEncodingValve`** listed first | **Low–medium**: merge pipeline XML when upgrading config. |
| **Logging (sample `conf/`)** | `Log4j.properties` (Log4j 1.x style) | `log4j2.xml` (Log4j 2) | **Medium**: migrate logging config and runtime dependencies to Log4j 2 (or bridge), consistent with Fulcrum/Turbine 7 expectations. |
| **SQL samples** | Multiple DB folders under `sql/` (MySQL, Oracle, PostgreSQL, etc.) | This distribution includes **MySQL-only** samples under `sql/mysql/` | **Low** for framework upgrade; **plan** DB scripts separately if you are not on MySQL (reuse 4.x scripts or current upstream). |
| **URL mapping valve** | `URLMapperValve` **not** in the 4.0 jar listing | `org.apache.turbine.services.urlmapper.URLMapperValve` **present** | **Optional**: new capability; only affects you if you adopt URL mapper service/pipeline entries. |

---

## 2. Configuration and packaging

### 2.1 Sample `conf/` layout (both versions)

Shared files (same conceptual role):

- `turbine-classic-pipeline.xml` — ordered valve list  
- `componentConfiguration.xml` — Avalon/Fulcrum-style component config (Torque, crypto, intake, parser, etc.)  
- `roleConfiguration.xml` — roles  

**Changed in the sample:**

- **4.x**: `Log4j.properties`  
- **7.x**: `log4j2.xml`  

### 2.2 Classic pipeline diff (from shipped samples)

**Turbine 4.0** (`conf/turbine-classic-pipeline.xml`) starts with:

- `DetermineActionValve` → … → `DetermineRedirectRequestedValve`

**Turbine 7.0** inserts at the **beginning**:

- `DefaultSetEncodingValve`  
- then `DetermineActionValve` → … → `DetermineRedirectRequestedValve`

When upgrading an app, **compare your production `turbine-classic-pipeline.xml`** (or custom pipeline) with the 7.0 sample and decide whether to add encoding as a valve for parity with 7.x behavior.

---

## 3. Java API and bytecode-level differences (verified on jars)

### 3.1 `org.apache.turbine.Turbine`

- **4.0**: `extends javax.servlet.http.HttpServlet`; `RunDataService.getRunData` takes `javax.servlet.http.*` and `javax.servlet.ServletConfig`.  
- **7.0**: `extends jakarta.servlet.http.HttpServlet`; same service signatures use **`jakarta.servlet.http.*`** and **`jakarta.servlet.ServletConfig`**.  
- **7.0** also references **`jakarta.xml.bind.JAXBContext`** / **`Unmarshaller`** for configuration loading (Jakarta XML Binding).  
- **7.0** carries **`jakarta.servlet.annotation.WebServlet`**, **`WebInitParam`**, **`MultipartConfig`** metadata on the servlet class (deployment descriptor / scanning behavior depends on container).

**Implication:** Any code in your WAR that implements `Servlet`, `Filter`, `HttpSessionListener`, or touches `RunData` with `javax.*` types must move to **`jakarta.*`** everywhere in the compile classpath.

### 3.2 Pipeline / custom valves

- **4.0**: e.g. `DefaultLoginValve extends AbstractValve`.  
- **7.0**: `DefaultLoginValve implements Valve` (no `AbstractValve` in jar).  

**Implication:** Custom valves that `extend AbstractValve` will **not compile** against Turbine 7 until refactored to **`implements Valve`** and updated for Jakarta servlet types in `PipelineData` / `RunData` usage.

### 3.3 `TemplateInfo` (reference check)

In **both** 4.0 and 7.0 reference jars, `TemplateInfo` appears as:

- `org/apache/turbine/util/template/TemplateInfo.class`

So **this specific class** did not move between these two reference builds; still **scan your codebase** for any types that *did* move between your exact 4.x patch level and 7.x (use IDE/compiler errors and dependency sources).

---

## 4. Dependency and runtime stack (typical upgrade path)

A Turbine 4.x app usually runs on **Java EE 7/8** (`javax.*`) with older Fulcrum/Torque/Commons stacks. Turbine 7.x targets **Jakarta EE 9+** and modern Fulcrum artifacts.

**Typical checklist:**

1. **JDK**: Move to a supported LTS (e.g. **17+**) if not already; align with your app server and Turbine 7 release notes.  
2. **Servlet container**: Tomcat 10.x+, Jetty 11+, or any EE 9+ runtime that provides **`jakarta.servlet`**.  
3. **Replace `javax.servlet` / `javax.annotation` / `javax.xml.bind`** (where applicable) with **`jakarta.*`** equivalents across **application code**, **taglibs**, and **third-party libraries** (some libraries need major-version bumps).  
4. **Fulcrum / Turbine satellite jars**: Upgrade to versions **compatible with Turbine 7** and Jakarta (crypto, intake, parser, template, security, etc.).  
5. **Torque / persistence**: Turbine still integrates with Torque in sample `componentConfiguration.xml`; upgrade Torque and JDBC drivers to versions validated on your JDK and DB.  
6. **Logging**: Adopt **Log4j 2** configuration (see sample `log4j2.xml`) or an equivalent supported binding; remove Log4j 1.x where obsolete.  
7. **`web.xml`**: Servlet version **5.0+** namespace and metadata; ensure `Turbine` servlet mapping matches your URL pattern and multipart settings if you use file upload.

---

## 5. Web application upgrade checklist (components + code)

Use this as a practical order of work:

1. **Inventory**  
   - Grep for `javax.servlet`, `javax.annotation`, `javax.xml.bind`, `javax.persistence`, etc.  
   - List custom **pipeline valves**, **services**, **modules/actions**, and **layouts** that use servlet APIs.

2. **Server and build**  
   - Select Jakarta-capable runtime; update **Maven/Gradle** BOMs for Servlet, JSP, JSTL, and Fulcrum/Turbine **7.x**.  
   - Fix compilation errors module-by-module.

3. **Replace Turbine / Fulcrum artifacts**  
   - Swap `turbine-4.x` for **`turbine-7.x`** and matching Fulcrum versions from the same generation as the [Apache Turbine](https://turbine.apache.org/) / Fulcrum build you use.

4. **Configuration merge**  
   - Merge `turbine-classic-pipeline.xml` (encoding valve).  
   - Migrate logging from `Log4j.properties` to **`log4j2.xml`** (or your chosen implementation).  
   - Reconcile `componentConfiguration.xml` / `roleConfiguration.xml` with new component classes and properties.

5. **Custom valves**  
   - Remove dependency on **`AbstractValve`**; implement **`Valve`**; update imports to **`jakarta.*`**.

6. **Custom `Turbine` subclass or init hooks**  
   - Align with **`configureApplication`**, **`Path`**, and Jakarta **`ServletConfig` / `ServletContext`**; remove assumptions about **`createRuntimeDirectories`** if that API is gone in your target line.

7. **JSP / templates**  
   - JSTL taglib URIs and implementations for Jakarta (e.g. **`jakarta.tags.*`**) must match the container; fix any **JSP** that imports `javax.servlet.*`.

8. **Integration tests**  
   - Login, session, ACL, redirects, file upload, scheduler (if used), and template rendering.

---

## 6. Reference file paths (quick open)

| Topic | Turbine 4.0 | Turbine 7.0 |
|--------|-------------|-------------|
| Classic pipeline | `turbine-4.0-binaries/turbine-4.0/conf/turbine-classic-pipeline.xml` | `turbine-7.0-binaries/turbine-7.0/conf/turbine-classic-pipeline.xml` |
| Components | `.../conf/componentConfiguration.xml` | `.../conf/componentConfiguration.xml` |
| Logging sample | `.../conf/Log4j.properties` | `.../conf/log4j2.xml` |
| Core jar | `.../turbine-4.0.jar` | `.../turbine-7.0.jar` |

---

## 7. Limitations of this document

- It compares the **specific 4.0 and 7.0 binary trees** under `TurbineFW`, not every intermediate **4.x** patch or **7.x** minor release.  
- **Dependency versions** (Fulcrum, Torque, Commons Configuration **2** vs older stacks) should be taken from the **official Turbine 7 POM** / BOM for the exact release you deploy, not assumed from jars alone.  
- For automated refactorings (e.g. package renames), you may still want a **verified recipe list** (OpenRewrite or similar) maintained next to your codebase.

---

*Generated from a direct comparison of `TurbineFW` reference distributions: pipeline XML, `conf/` samples, and `javap` / `jar tf` inspection of `turbine-4.0.jar` vs `turbine-7.0.jar`.*
