# OpenRewrite: Spring Framework 4.x/5.x → 6.x + Jakarta — recipes, constraints, manual backlog

This document describes OpenRewrite assets under **`C:\openRewrite`** for moving legacy **Spring Framework 4.x / early 5.x** applications toward **Spring Framework 6.0+** with **Jakarta EE 9+** (`jakarta.*`) compatibility.

**Related:** [SPRING-FRAMEWORK-4-TO-6-JAKARTA-SUMMARY.md](./SPRING-FRAMEWORK-4-TO-6-JAKARTA-SUMMARY.md) · [rewrite-spring-4-to-6-jakarta.yml](./rewrite-spring-4-to-6-jakarta.yml) · [rewrite.yml](./rewrite.yml)

---

## 1. Prerequisites

| Requirement | Notes |
|-------------|--------|
| **JDK 17+** | Mandatory for Spring Framework 6 and for running the compiler after migration. |
| **Servlet container** | For WARs: **Servlet 5+** (e.g. **Tomcat 10+**, **Jetty 11+**, **WildFly** EE 9+). |
| **Maven plugin classpath** | [pom.xml](./pom.xml) must include **`rewrite-migrate-java`** and **`rewrite-spring`** (version aligned with your `rewrite-maven-plugin`; currently **5.19.0** for `rewrite-spring` — bump if OpenRewrite docs recommend a newer pairing). |
| **License** | `rewrite-spring` recipes are under the [Moderne Source Available License](https://docs.moderne.io/licensing/moderne-source-available-license); confirm compliance for your organization. |

---

## 2. Recipe catalog

### 2.1 File locations

| File | Role |
|------|------|
| [rewrite-spring-4-to-6-jakarta.yml](./rewrite-spring-4-to-6-jakarta.yml) | Standalone YAML for Spring recipes (**keep in sync** with `rewrite.yml`). |
| [rewrite.yml](./rewrite.yml) | Registers the same recipes so `configLocation=${project.basedir}/rewrite.yml` picks them up. |

### 2.2 `com.uob.openrewrite.SpringFramework4xTo6xJakarta` (primary transform)

**Purpose:** Automate the bulk of **Spring Framework → 6.0.x** upgrades and **javax → jakarta** in your **Java** sources.

**Composition:**

1. **`org.openrewrite.java.spring.framework.UpgradeSpringFramework_6_0`**  
   - Upstream composite: includes **UpgradeSpringFramework_5_3** (and deeper chain), bumps **`org.springframework:*`** dependencies, and applies Spring-specific code migrations (Assert, HttpClient 5, `ResponseStatusException`, `ResponseEntityExceptionHandler`, `JdbcTemplate` helpers, etc.).  
   - See: [Migrate to Spring Framework 6.0](https://docs.openrewrite.org/recipes/java/spring/framework/upgradespringframework_6_0).

2. **`com.uob.openrewrite.JavaxToJakartaNamespaces`**  
   - Same Jakarta stack used elsewhere in this repo (`JavaxMigrationToJakarta` + explicit `ChangePackage` rules for servlet, JPA, validation, JAXB, etc.).

**Run:**

```text
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run -DactiveRecipes=com.uob.openrewrite.SpringFramework4xTo6xJakarta
```

**Does not fully cover:** items in [Section 4](#4-manual-backlog-and-constraints) (XML, JSP, ecosystem libraries, security config semantics, etc.).

### 2.3 `com.uob.openrewrite.SpringFramework4xTo6xWithSpringSecurity6`

**Purpose:** Same as **SpringFramework4xTo6xJakarta**, plus **`org.openrewrite.java.spring.security6.UpgradeSpringSecurity_6_0`** for projects that use **Spring Security**.

**Run:**

```text
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run -DactiveRecipes=com.uob.openrewrite.SpringFramework4xTo6xWithSpringSecurity6
```

**Note:** OAuth2, SAML, method security, and filter-chain DSL often need **manual** follow-up even after the security recipe.

### 2.4 `com.uob.openrewrite.SpringFramework4To6ManualBacklog` (detection only)

**Purpose:** Generate **search markers / datatables** for patterns that usually need **human review** or **rewrite** beyond generic recipes.

**Includes (non-exhaustive):**

- **`WebMvcConfigurerAdapter`** — removed; use **`WebMvcConfigurer`** default methods.  
- **`SimpleJdbcTemplate`** — removed in Spring 6; migrate to **`JdbcTemplate`** / **`NamedParameterJdbcTemplate`**.  
- **`CommonsMultipartResolver`** — Commons FileUpload–based; prefer **`StandardServletMultipartResolver`** on Servlet 3+ / Jakarta.  
- **`HibernateDaoSupport` (hibernate3 / hibernate4 packages)** — legacy ORM integration removed from Spring 6; move to **Hibernate 6 + `LocalSessionFactoryBean` / JPA**.  
- **`javax.servlet.*` / `javax.persistence.*` / `javax.validation.*`** — should trend to zero after Jakarta migration; hits indicate leftover files.  
- **XML:** `jee:` namespace usage, `http://www.springframework.org/schema/` in `*.xml`, `javax.servlet` in `*.xml` / `*.jsp`.

**Run:**

```text
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run -DactiveRecipes=com.uob.openrewrite.SpringFramework4To6ManualBacklog
```

Use **`exportDatatables=true`** (already enabled in this repo’s `pom.xml`) to export CSV-style results.

---

## 3. Recommended workflow

1. **Branch** and ensure the project builds on a **supported JDK** for your current Spring line (often JDK 8 or 11 for Spring 4/5).  
2. **Upgrade JDK to 17+** on a dedicated migration branch (Spring 6 will not run on Java 8).  
3. Run **`SpringFramework4To6ManualBacklog`** and triage output into tickets.  
4. Run **`SpringFramework4xTo6xJakarta`** (or **WithSpringSecurity6** if applicable).  
5. **Review diffs** (especially POMs and removed dependencies).  
6. Fix **manual backlog** items; run **`mvn clean verify`**.  
7. Deploy to a **Jakarta**-capable runtime and run **integration / smoke tests**.

For very old Spring **4.x** codebases, you may need an intermediate step to **Spring 5.3** on JDK 11 before jumping to **6.0**; if the composite recipe fails mid-way, consult the [Spring Framework 6 upgrade wiki](https://github.com/spring-projects/spring-framework/wiki/Upgrading-to-Spring-Framework-6.x) and consider running **`UpgradeSpringFramework_5_3`** alone first on a branch.

---

## 4. Manual backlog and constraints

The following areas **cannot** be fully automated by the recipes above, or require **validation** after automation.

### 4.1 Platform and build

| Item | Why manual |
|------|------------|
| **JDK baseline** | Spring 6 requires **17+**; CI images, Dockerfiles, and IDE settings must change. |
| **Maven / Gradle BOMs** | Recipes bump many **Spring** artifacts; **third-party** starters (Camel, CXF, vendor libs) must be checked for Jakarta-compatible versions. |
| **Non-Spring JARs still using `javax.*`** | Must upgrade or replace (e.g. old Hibernate, old REST clients, old JSP taglibs). |

### 4.2 XML configuration

| Item | Why manual |
|------|------------|
| **`web.xml` / `web-fragment.xml`** | Servlet **5.0** schema, `metadata-complete`, filter order. |
| **Spring `applicationContext.xml`** | Class names for removed beans, `jee:` / JNDI lookups, custom namespace handlers. |
| **`context:component-scan` / XML namespaces** | Version-specific XSDs; some elements deprecated or removed. |

### 4.3 Web and view layer

| Item | Why manual |
|------|------------|
| **JSP / JSTL** | Taglib URIs and implementations must be **Jakarta**-aligned; scriptlets importing `javax.servlet` need edits. |
| **Tiles, Struts bridges, legacy multipart** | Often outside `rewrite-spring` scope. |
| **`CommonsMultipartResolver` → `StandardServletMultipartResolver`** | Servlet configuration and size thresholds must match ops requirements. |

### 4.4 Data access and ORM

| Item | Why manual |
|------|------------|
| **Hibernate 3/4 Spring packages** | Removed; migrate to **Hibernate 6** or **JPA** with Spring **6** support modules. |
| **`SimpleJdbcTemplate`** | Removed; refactor call sites. |
| **Transaction manager choice** | `JtaTransactionManager`, `DataSourceTransactionManager`, etc. must match deployment. |

### 4.5 Spring Security (if applicable)

| Item | Why manual |
|------|------------|
| **Filter chain / `WebSecurityConfigurerAdapter` removal** | Spring Security 5.7+ / 6.x configuration style changes; recipes help but rarely cover all customizations. |
| **OAuth2 / OIDC** | Client registration and property keys changed across major versions. |

### 4.6 Observability, scheduling, messaging

| Item | Why manual |
|------|------------|
| **Micrometer / Actuator** (if Boot added later) | Not part of plain Spring Framework recipe set. |
| **JMS, Kafka, WebSocket** | Broker client JARs and `javax.jms` → `jakarta.jms` in config. |

### 4.7 Detection recipe limitations

| Item | Notes |
|------|--------|
| **False positives** | `javax.servlet` / Spring schema hits may appear in **comments**, **tests**, or **generated** sources. |
| **Incomplete coverage** | Unknown custom extensions won’t appear in `FindTypes` list—use compiler errors and the Spring wiki as the source of truth. |

---

## 5. Optional: newer Spring 6.1+

OpenRewrite publishes **`UpgradeSpringFramework_6_1`** and later recipes. After a successful **6.0** migration, consider running those in a separate change set with release notes review.

---

## 6. Keeping files in sync

When you edit Spring recipes, update **both** [rewrite-spring-4-to-6-jakarta.yml](./rewrite-spring-4-to-6-jakarta.yml) and the **Spring `---` sections** in [rewrite.yml](./rewrite.yml).
