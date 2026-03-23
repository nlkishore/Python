# OpenRewrite for Legacy Turbine/Torque/Jetspeed Modernization

## Executive summary

OpenRewrite is an automated refactoring framework that applies source-code transformations using declarative recipes.  
For legacy stacks like Turbine/Torque + Java EE + ECS/Jetspeed on Java 8, it is well-suited to:

- bulk package/API migration (`javax.*` -> `jakarta.*`)
- Java language/runtime upgrades (8 -> 17)
- dependency and plugin upgrades in Maven/Gradle
- repeatable, auditable, large-scale code changes across multi-module repos

It is strongest for **mechanical** transformations and modernization guardrails.  
It does **not** replace architecture decisions, runtime testing, or framework-specific redesign work.

---

## What OpenRewrite is

OpenRewrite works by parsing code/build files into ASTs and applying recipes:

- Java source refactors
- XML/YAML/Properties transforms
- Maven/Gradle dependency and plugin updates
- Java version and build settings migration

Key traits for enterprise modernization:

- **repeatable**: same recipe gives same result
- **scalable**: works across hundreds/thousands of files
- **reviewable**: outputs regular git diffs
- **composable**: chain recipes into migration stages

---

## Capabilities relevant to your stack

### 1) Java EE -> Jakarta EE namespace migration

For Java EE apps moving to Jakarta EE-compatible servers/frameworks:

- replace imports and types from `javax.*` to `jakarta.*` where APIs moved
- update annotations and related APIs in code/config
- align dependencies to Jakarta artifacts/versions

This is one of the highest-value OpenRewrite use cases.

### 2) Java 8 -> JDK 17 modernization

OpenRewrite can automate many source/build changes:

- language-level cleanups and idiomatic updates
- deprecated API replacements (where recipes exist)
- Maven compiler plugin/source-target updates
- test framework and plugin modernization support

### 3) Build/dependency modernization

For Maven-heavy legacy repos:

- upgrade dependencies with constraints
- enforce minimum secure versions
- update plugin versions and build properties
- standardize BOM usage

### 4) Configuration and descriptor transforms

Legacy projects often include XML descriptors and properties:

- targeted changes in XML/properties files
- consistent namespace/property updates across modules

### 5) Custom recipes for Turbine/Torque/Jetspeed/ECS patterns

Your stack has legacy framework-specific classes/config patterns.  
Where built-in recipes are insufficient, you can create custom recipes to:

- rewrite package/class references for internal framework wrappers
- transform recurring service/action/handler patterns
- enforce modernization conventions per module

---

## How it applies to Turbine/Torque + ECS/Jetspeed projects

### Typical migration layers

1. **Baseline inventory**
   - modules, Java versions, containers, current deps, `javax` usage map

2. **Build readiness**
   - Maven/toolchain updates first to support Java 17 build

3. **Namespace/API migration**
   - `javax` -> `jakarta` and dependent lib alignment

4. **Framework adaptation**
   - Turbine/Torque/Jetspeed integration points that need custom changes

5. **Compile + test hardening**
   - unit/integration/regression + server startup smoke tests

OpenRewrite primarily accelerates steps **2-4** for mechanical code/build edits.

---

## Torque 3.x -> Torque 6.x specific guidance

Your feedback is important: Torque 3 -> 6 is not only namespace migration. It includes architectural and generated-code model changes that affect method-level implementation.

### What changes in this jump

1. **Schema-driven generated classes/stubs changed**
   - classes generated from `schema.xml` differ in structure and API shape between Torque 3 and 6.
   - old generated artifacts should be treated as replaceable output, not hand-migrated line-by-line.

2. **`Criteria` implementation differences**
   - method names/signatures and query construction idioms differ.
   - call sites may compile-break and also require semantic verification.

3. **Legacy `MapBuilder` concept changed**
   - metadata/bootstrap usage patterns are different in newer Torque versions.
   - this can require both API rewrite and refactoring of startup/runtime wiring logic.

### How OpenRewrite should be applied for this scenario

Use a **hybrid migration model**:

- **Step A: Regenerate first**
  - regenerate all Torque artifacts from `schema.xml` with Torque 6 tooling.
  - keep generated folders isolated and avoid manual edits there.

- **Step B: OpenRewrite for mechanical updates**
  - rewrite imports/type names to new Torque packages/classes.
  - transform known `Criteria` construction patterns and method calls.
  - transform straightforward `MapBuilder` replacements where mapping is deterministic.

- **Step C: Custom recipe + manual queue for non-deterministic cases**
  - create custom recipes that:
    - auto-fix simple patterns,
    - emit markers/report entries for complex or ambiguous usage.
  - route flagged files into manual migration review.

### Practical recipe buckets for Torque migration

- **Type/package recipe set**
  - old Torque class/package references -> new class/package references.

- **Method migration recipe set**
  - old `Criteria` method invocations -> new equivalents (including argument and chaining changes).

- **Metadata/MapBuilder recipe set**
  - legacy map builder registration/usage -> updated Torque 6 metadata approach.

- **Generated-artifact reference recipe set**
  - update hand-written code that references regenerated stubs/peer/base classes.

### What OpenRewrite cannot safely infer here

- business semantics of complex query logic,
- SQL/result equivalence for all `Criteria` transformations,
- runtime side effects of metadata bootstrap changes in custom Turbine/Jetspeed integration.

These require compile + integration tests and selective manual remediation.

### Recommended execution sequence for Torque 3 -> 6

1. Inventory all Torque API usages (`Criteria`, `MapBuilder`, generated class dependencies).
2. Regenerate Torque 6 artifacts from schema.
3. Run staged OpenRewrite recipes (types -> methods -> metadata patterns).
4. Compile and fix unresolved symbols.
5. Run query/regression validation for high-risk modules.
6. Commit in small PRs with migration reports.

### Torque recipe backlog template

Use this table to track each Torque API migration item from discovery through validation.

| Module | Old API / Pattern | New API / Pattern | Rewrite Recipe Name | Recipe Type (Built-in/Custom) | Recipe Status | Validation Owner | Validation Type | Notes |
|---|---|---|---|---|---|---|---|---|
| `module-a` | `OldCriteriaPatternA(...)` | `NewCriteriaPatternA(...)` | `com.company.torque.CriteriaARecipe` | Custom | Planned | `team-a` | Compile + Unit |  |
| `module-b` | `LegacyMapBuilderRegistrationX` | `Torque6MetadataRegistrationX` | `com.company.torque.MapBuilderXRecipe` | Custom | In Progress | `team-b` | Integration + Startup |  |
| `module-c` | `org.apache.torque.oldpkg.TypeY` | `org.apache.torque.newpkg.TypeY` | `org.openrewrite.java.ChangeType` | Built-in | Done | `team-c` | Compile |  |

#### Recipe status values (suggested)

- **Planned**: identified and queued
- **In Progress**: recipe implementation or tuning underway
- **Dry Run Passed**: recipe tested in dry-run mode with expected diff
- **Applied**: recipe applied and committed
- **Validated**: compile/tests/regression checks passed
- **Deferred**: intentionally postponed with rationale

#### Validation owner guidance

- assign an owner at module/service level (not individual file level) for faster sign-off
- for query-heavy `Criteria` changes, include both code owner and QA owner
- for metadata/bootstrap (`MapBuilder`) changes, include runtime/platform owner

---

## Turbine 3.x -> Turbine 7.x specific guidance

Turbine 7.x introduces major architectural differences from Turbine 3.x, including pipeline/valve-centric request processing and different service/configuration patterns.  
This is a design-level modernization where OpenRewrite is useful, but only for the mechanical portion.

### Typical change areas in Turbine upgrade

1. **Request flow architecture**
   - legacy action/screen/navigation flow often moves into pipeline/valve-driven orchestration.

2. **Pipeline and valve configuration**
   - initialization and request handling order are configured differently.
   - legacy configuration keys and locations may need transformation.

3. **Custom services lifecycle and injection**
   - service registration and service wiring can differ significantly from legacy Turbine.

4. **Framework integration touchpoints**
   - custom ECS/Jetspeed integrations may rely on old hooks and need adaptation.

### Where OpenRewrite helps effectively

OpenRewrite can automate **mechanical** upgrade tasks at scale:

- replace old Turbine package/type references with Turbine 7 equivalents
- migrate method signatures and common call patterns where mapping is deterministic
- update configuration artifacts (properties/XML/YAML) with key/name changes
- normalize bootstrapping code for service lookup/injection patterns where repeatable
- add migration markers for code paths needing manual redesign

### Where OpenRewrite is limited

OpenRewrite cannot safely infer:

- target valve/pipeline design for your business flow
- ordering semantics of custom valves without architecture decisions
- runtime behavior equivalence of custom services just from API mapping

So for Turbine upgrade, OpenRewrite is an **accelerator**, not a full architecture migration engine.

### Recommended hybrid approach for Turbine 3 -> 7

1. **Define target Turbine 7 architecture first**
   - target valve chain, pipeline stages, custom service boundaries.

2. **Build a migration mapping catalog**
   - old Turbine APIs/config keys -> new Turbine 7 APIs/config keys.

3. **Run staged OpenRewrite recipes**
   - Stage A: package/type migration
   - Stage B: method/signature updates
   - Stage C: config key/resource transformations
   - Stage D: marker insertion for manual redesign hotspots

4. **Manual refactor for non-mechanical design shifts**
   - valve orchestration logic
   - custom service lifecycle/boot order
   - integration hooks with Jetspeed/ECS extensions

5. **Validation**
   - compile + startup checks
   - request-flow regression suite
   - valve ordering and side-effect tests

### Turbine upgrade recipe backlog template (optional extension)

Use the same backlog model as Torque, with Turbine-specific patterns:

| Module | Legacy Turbine Pattern | Turbine 7 Target Pattern | Rewrite Recipe Name | Recipe Status | Validation Owner | Notes |
|---|---|---|---|---|---|---|
| `web-core` | Legacy request chain hook | Valve chain registration | `com.company.turbine.ValveChainRecipe` | Planned | `platform-team` |  |
| `service-a` | Legacy service locator usage | Turbine 7 service API usage | `com.company.turbine.ServiceApiRecipe` | In Progress | `service-team-a` |  |
| `config` | Legacy Turbine property keys | Turbine 7 config keys | `com.company.turbine.ConfigKeyRecipe` | Dry Run Passed | `platform-team` |  |

### Combined migration matrix (Torque + Turbine)

Use this matrix to prioritize cross-framework migration work and plan sprint sequencing.

Scoring guidance:

- **Priority**: `P1` (critical), `P2` (important), `P3` (normal)
- **Effort**: `S` (small), `M` (medium), `L` (large), `XL` (very large)
- **Risk Score**: `1` (low) to `5` (high), based on runtime impact + uncertainty

| Workstream | Framework | Legacy Area | Target Area | Recipe Coverage | Priority | Effort | Risk Score | Owner | Validation Gate |
|---|---|---|---|---|---|---|---|---|---|
| Generated artifacts regeneration | Torque | `schema.xml` old stubs/peers | Torque 6 regenerated classes | Partial (outside Rewrite) | P1 | M | 4 | DB/Platform Team | Compile + DAO regression |
| Criteria API migration | Torque | Legacy `Criteria` calls | Torque 6 Criteria patterns | High (custom recipes) | P1 | L | 5 | Data Access Team | SQL equivalence + integration |
| MapBuilder/metadata migration | Torque | Legacy `MapBuilder` model | Torque 6 metadata approach | Medium (custom + manual) | P1 | L | 5 | Platform Team | Startup + metadata load tests |
| Request pipeline migration | Turbine | Legacy action/screen flow | Turbine 7 valve/pipeline flow | Low (design-heavy) | P1 | XL | 5 | Web Platform Team | Flow regression + UAT |
| Service lifecycle wiring | Turbine | Legacy service registration | Turbine 7 service model | Medium | P1 | L | 4 | Core Services Team | Startup + contract tests |
| Config key/resource migration | Turbine | Legacy Turbine configs | Turbine 7 config conventions | High | P2 | M | 3 | Platform Team | Config smoke tests |
| Package/type modernization | Torque + Turbine | Old framework package references | Updated package/type references | High (built-in + custom) | P2 | M | 3 | Shared Modernization Team | Compile |
| Jakarta namespace migration | Cross-cutting | `javax.*` usage | `jakarta.*` usage | High (built-in recipes) | P1 | M | 4 | Shared Modernization Team | Compile + server startup |
| Java 8 to Java 17 language/build updates | Cross-cutting | old JDK/compiler settings | JDK 17 build/runtime | High | P1 | M | 4 | Build/DevEx Team | Full CI + performance smoke |
| ECS/Jetspeed integration adaptation | Turbine + ECS/Jetspeed | Legacy extension hooks | Updated integration hooks | Low/Medium (mostly manual) | P1 | XL | 5 | Integration Team | End-to-end regression |

#### Matrix usage recommendations

1. Execute all **P1** items first, grouped by dependency order:
   - build/runtime readiness -> generated artifacts -> API migration -> pipeline/service redesign.
2. Within the same priority, start with lower effort/high coverage items to reduce compile failures early.
3. Treat all items with **Risk Score >= 4** as mandatory for integration + regression test gates.
4. Re-score risk after each stage (Dry Run, Applied, Validated) and update sprint planning.

---

## Java 8 -> Java 17 strictness (JPMS and third-party library handling)

Java 17 introduces stronger encapsulation and module-era behavior that can expose hidden technical debt in Java 8 applications.  
For legacy Turbine/Torque/Jetspeed systems, this is both a build/runtime and architecture concern.

### Major platform changes to account for

1. **JPMS-era encapsulation**
   - stronger access checks and reduced tolerance for deep reflection into JDK internals.
   - classpath-based apps can still run, but hidden illegal-access patterns often surface.

2. **Removed JDK modules from Java 8 era**
   - old assumptions about bundled Java EE/CORBA APIs no longer hold.
   - dependencies such as JAXB/JAX-WS/activation must be explicitly provided via external artifacts.

3. **`javax` and `jakarta` ecosystem split**
   - libraries pinned to `javax` may conflict with Jakarta-compatible application runtime strategy.

4. **Bytecode/reflection framework compatibility**
   - outdated proxy/bytecode libraries can fail under Java 17.
   - transitive dependencies become a critical risk area.

### How to detect third-party module/library issues

Use a combination of static and build-time checks:

1. **JDK dependency analysis**
   - `jdeps --multi-release 17 --recursive <artifact-or-dir>`
   - `jdeps --jdk-internals --recursive <artifact-or-dir>`
   - identify illegal/internal API usage and module-level risks.

2. **Deprecated-for-removal scan**
   - `jdeprscan --release 17 <artifact-or-dir>`
   - identify APIs likely to break in future JDK upgrades.

3. **Dependency graph and convergence checks**
   - Maven/Gradle dependency tree analysis for stale/duplicate/conflicting transitive libraries.
   - enforce convergence to avoid shadowed classes and inconsistent bytecode stacks.

4. **Duplicate class / split package detection**
   - detect same class or same package spread across multiple jars/modules.
   - especially important when introducing module-path or mixed runtime arrangements.

5. **Automatic module naming review**
   - check jars without `module-info` for stable `Automatic-Module-Name`.
   - prevent module name collisions across third-party dependencies.

### Other major architecture handling considerations

- prefer **classpath-first migration** to Java 17 for legacy apps, then evaluate module-path adoption per module.
- isolate high-risk integrations (security, session, startup bootstrap, reflection-heavy components) in dedicated test suites.
- formalize dependency governance (approved versions, forbidden artifacts, BOM alignment).
- treat server/runtime upgrade and Java upgrade as coordinated tracks (not independent tasks).

### How OpenRewrite helps in this area

OpenRewrite is highly effective for:

- upgrading dependency coordinates/versions in build files
- replacing removed/deprecated source API usages where deterministic
- `javax` -> `jakarta` package/API transformations
- modernization of compiler and build plugin configuration

OpenRewrite does **not** fully solve:

- binary/module conflicts across third-party jars
- runtime reflection access errors that appear only during execution
- module-path design decisions and split-package architecture resolution

### Recommended Java 17 modernization workflow (with OpenRewrite)

1. Run OpenRewrite recipes for Java/Jakarta/dependency/build updates.
2. Compile on JDK 17 and fix direct source-level failures.
3. Run `jdeps` + duplicate/split-package checks in CI.
4. Upgrade or replace incompatible third-party libraries.
5. Execute integration/startup/regression tests on target runtime.
6. Optionally phase into deeper JPMS adoption once stable on Java 17.

### CI checklist (suggested)

- [ ] Build on JDK 17 toolchain
- [ ] OpenRewrite recipe run succeeded and committed
- [ ] Dependency convergence and duplicate class checks passed
- [ ] `jdeps --jdk-internals` report reviewed
- [ ] `jdeprscan` report reviewed
- [ ] Runtime smoke tests passed on target Jakarta-compatible server

---

## What OpenRewrite cannot do automatically (important)

- decide target architecture/module boundaries
- guarantee runtime behavior equivalence
- fully migrate proprietary ECS/Jetspeed custom runtime semantics
- solve all servlet/container behavior differences without testing

Use it as an accelerator, not a one-click migration.

---

## Recommended modernization approach (practical)

### Phase A: Dry run and blast-radius estimate

- run recipes with `dryRun`
- produce metrics: files touched, modules impacted, key API hotspots
- review top risk modules first (auth, session, filters, container integration)

### Phase B: Staged transformation

- Stage 1: build/plugins/dependencies
- Stage 2: Java 17 source/build compatibility
- Stage 3: Jakarta namespace and API transitions
- Stage 4: framework-specific custom recipes

Use separate commits/PRs per stage for safer rollback and review.

### Phase C: Validation gates

- compile all modules
- run unit + integration suites
- deploy to Jakarta-compatible runtime (Tomcat 10+/Jetty EE10/etc. as applicable)
- smoke-test Turbine/Torque/Jetspeed flows

### Phase D: Governance and repeatability

- codify recipes in repo
- run in CI for modernization policy checks
- re-run recipes periodically for drift control

---

## Example transformation categories for your target state

Target: **Jakarta EE + JDK 17**

- package migration recipes (javax to jakarta)
- Maven `maven-compiler-plugin` and related build plugin updates
- dependency upgrades compatible with Jakarta and Java 17
- recipe-based cleanup for deprecated Java 8 idioms
- custom recipes for framework-specific extension points

---

## Risks and mitigations

1. **Partial migration conflicts**
   - Mitigation: migrate in bounded module groups; keep branch isolation.

2. **Transitive dependency mismatch**
   - Mitigation: BOM alignment + dependency convergence checks.

3. **Container/runtime incompatibilities**
   - Mitigation: early deploy tests on target runtime; servlet/JSP/taglib checks.

4. **Custom framework hooks breakage**
   - Mitigation: custom recipes + targeted regression pack for Turbine/Jetspeed flows.

---

## Suggested enterprise workflow

- Create a dedicated modernization branch per stage
- Run OpenRewrite recipes -> commit generated diffs
- Perform manual review on high-risk files
- Execute compile/test/deploy gates
- Merge incrementally

This gives traceability and controlled risk while still getting strong automation benefits.

---

## Tooling decision summary

For your scenario, OpenRewrite is a strong fit as the **core code transformation engine** for:

- Java 8 -> 17 upgrade mechanics
- Java EE -> Jakarta EE namespace and dependency migration
- large-scale, repeatable refactoring across Turbine/Torque/Jetspeed modules

Pair it with:

- robust CI validation
- framework-specific custom recipes
- staged rollout and regression testing

---

## Optional next step

If needed, the next document can define:

- an initial OpenRewrite recipe set (built-in + custom placeholders),
- stage-wise execution commands,
- and a validation checklist mapped to each module in your legacy project.

