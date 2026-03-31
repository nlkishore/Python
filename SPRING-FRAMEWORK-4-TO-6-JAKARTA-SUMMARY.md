# Spring Framework 4.x → 6.x and Jakarta EE alignment (summary)

Spring **6.x** requires **JDK 17+** and the **Jakarta EE 9+** namespace (`jakarta.*`) for Servlet, JPA, Bean Validation, JMS, and related APIs that Spring integrates with. Spring **5.3.x** was the last line supporting **Java EE 8** (`javax.*`) while introducing a Jakarta variant for forward compatibility; Spring **6** is Jakarta-only.

## 1. High-level differences (4.x era → 6.x)

| Topic | Spring 4.x (typical) | Spring 6.x |
|--------|----------------------|------------|
| **Java** | Often JDK 6–8 | **JDK 17 minimum** (21 LTS common) |
| **Servlet / MVC** | `javax.servlet.*` in apps | **`jakarta.servlet.*`** |
| **JPA / validation** | `javax.persistence`, `javax.validation` | **`jakarta.persistence`**, **`jakarta.validation`** |
| **Spring modules** | BOM aligned to 4.x | **`org.springframework:*` 6.0+**; removed legacy integrations |
| **HTTP client** | Apache HttpClient 4.x patterns in places | Spring 6 recipes migrate toward **HttpClient 5** where applicable |
| **Spring Security** (if used) | 4.x / 5.x on `javax` | **Spring Security 6.x** on `jakarta` (coordinate upgrade) |

## 2. What OpenRewrite automates (see recipe doc)

The **`org.openrewrite.java.spring.framework.UpgradeSpringFramework_6_0`** recipe (from **`rewrite-spring`**) composes:

- A chain that includes **Migrate to Spring Framework 5.3** (and earlier steps in the chain) for incremental API and dependency updates.
- **Upgrade `org.springframework` artifacts** toward **6.0.x** in Maven/Gradle metadata.
- Targeted fixes (examples from upstream recipe): **Spring `Assert`**, **Apache HttpClient 5**, **`ResponseStatusException`**, **`ResponseEntityExceptionHandler`**, **`JdbcTemplate.queryForLong`**, etc.

Your workspace adds **`JavaxToJakartaNamespaces`** after that so **application** code moves to **`jakarta.*`**.

## 3. Official references

- [Upgrading to Spring Framework 6.x](https://github.com/spring-projects/spring-framework/wiki/Upgrading-to-Spring-Framework-6.x)  
- [OpenRewrite — Migrate to Spring Framework 6.0](https://docs.openrewrite.org/recipes/java/spring/framework/upgradespringframework_6_0)  
- [Jakarta EE / Servlet 5+ runtimes](https://jakarta.ee/) (Tomcat 10+, etc.)

## 4. Next steps

Run recipes and manual backlog per **[OPENREWRITE-SPRING4-TO-6-RECIPE-AND-CONSTRAINTS.md](./OPENREWRITE-SPRING4-TO-6-RECIPE-AND-CONSTRAINTS.md)**.
