# OpenRewrite Starter Recipe Catalog Template

Use this template to plan, track, and operationalize recipe-driven modernization.

Recommended companion documents:

- `C:\openRewrite\OPENREWRITE-BEGINNER-GUIDE-RECIPES-STEPBYSTEP.md`
- `C:\openRewrite\OPENREWRITE-LEGACY-TO-JAKARTAEE-JDK17.md`

---

## 1) Catalog metadata

| Field | Value |
|---|---|
| Program Name | `<e.g., Turbine-Torque Jakarta Modernization>` |
| Catalog Version | `<v1.0>` |
| Date | `<YYYY-MM-DD>` |
| Maintainer | `<team/person>` |
| Target Runtime | `<Jakarta EE server + JDK 17>` |
| Source Control Repo | `<repo URL/path>` |

---

## 2) Migration scope summary

### 2.1 In scope modules

- `<module-1>`
- `<module-2>`
- `<module-3>`

### 2.2 Out of scope modules (current phase)

- `<module-x>`
- `<module-y>`

### 2.3 Target outcomes for this phase

- [ ] Java 17 build compatibility
- [ ] `javax` -> `jakarta` migration (selected modules)
- [ ] Torque 3.x -> 6.x API transition (selected areas)
- [ ] Turbine 3.x -> 7.x mechanical updates

---

## 3) Recipe governance model

### 3.1 Status lifecycle

Use one of:

- `Draft`
- `Ready for Dry Run`
- `Dry Run Passed`
- `Applied`
- `Validated`
- `Deprecated`

### 3.2 Ownership

| Role | Team/Owner |
|---|---|
| Recipe Author | `<name/team>` |
| Technical Reviewer | `<name/team>` |
| Validation Owner | `<name/team>` |
| Release Approver | `<name/team>` |

### 3.3 Validation gates (minimum)

- [ ] Compile gate
- [ ] Unit test gate
- [ ] Integration/runtime smoke gate
- [ ] Regression gate (if high-risk change)

---

## 4) Master recipe register (fill this first)

| Recipe ID | Recipe Name | Framework Area | Type (Built-in/Custom) | Scope (Modules) | Priority | Effort (S/M/L/XL) | Risk (1-5) | Status | Owner |
|---|---|---|---|---|---|---|---|---|---|
| RCP-001 | `<javax-to-jakarta-core>` | Cross-cutting | Built-in | `<module-a,module-b>` | P1 | M | 4 | Draft | `<team>` |
| RCP-002 | `<torque-criteria-method-mapping>` | Torque | Custom | `<dao-module>` | P1 | L | 5 | Draft | `<team>` |
| RCP-003 | `<turbine-config-key-migration>` | Turbine | Custom | `<web-module>` | P2 | M | 3 | Draft | `<team>` |

---

## 5) Built-in recipe catalog section

List built-in recipes selected for this program.

| Built-in Recipe | Why Selected | Preconditions | Expected Impact | Notes |
|---|---|---|---|---|
| `<org.openrewrite...>` | `<reason>` | `<precondition>` | `<file types/modules>` | `<notes>` |
| `<org.openrewrite...>` | `<reason>` | `<precondition>` | `<file types/modules>` | `<notes>` |

---

## 6) Custom recipe catalog section

Create one entry per custom recipe.

### 6.x Custom Recipe Card (copy per recipe)

**Recipe ID:** `<RCP-XXX>`  
**Recipe Name:** `<com.company.modernization.SomeRecipe>`  
**Framework Area:** `<Torque | Turbine | Cross-cutting>`  
**Priority:** `<P1/P2/P3>`  
**Effort:** `<S/M/L/XL>`  
**Risk Score:** `<1-5>`

#### A) Business/technical intent

- legacy pattern:
  - `<describe old API/config pattern>`
- target pattern:
  - `<describe new API/config pattern>`
- why this matters:
  - `<impact/risk/value>`

#### B) Matching strategy

- file types:
  - `<java/xml/properties/yaml>`
- matching logic:
  - `<MethodMatcher/type match/property key match/etc.>`
- exclusions:
  - `<generated code folders, test fixtures, etc.>`

#### C) Transformation strategy

- transformation rules:
  1. `<rule-1>`
  2. `<rule-2>`
  3. `<rule-3>`
- fallback behavior:
  - `<insert marker / skip / report only>`

#### D) Sample before/after

**Before**
```java
// paste representative snippet
```

**After**
```java
// paste expected transformed snippet
```

#### E) Test cases for recipe

- [ ] positive case 1
- [ ] positive case 2
- [ ] negative/no-change case
- [ ] edge case (null/empty/default config)

#### F) Validation plan

- compile validation:
  - `<commands>`
- runtime/integration validation:
  - `<test suite>`
- owner sign-off:
  - `<owner/team>`

#### G) Rollout plan

- pilot module: `<module>`
- wave-2 modules: `<list>`
- rollback strategy: `<revert commit / disable recipe>`

---

## 7) Torque-specific mapping table template

| Legacy API/Pattern | Target API/Pattern | Recipe ID | Auto-Transform % | Manual Follow-up Needed | Validation Owner |
|---|---|---|---|---|---|
| `<Criteria old pattern>` | `<Criteria new pattern>` | `<RCP-...>` | `<0-100>` | `<yes/no + details>` | `<team>` |
| `<MapBuilder pattern>` | `<metadata pattern>` | `<RCP-...>` | `<0-100>` | `<yes/no + details>` | `<team>` |

---

## 8) Turbine-specific mapping table template

| Legacy Pattern | Target Pattern (Turbine 7) | Recipe ID | Auto-Transform % | Manual Design Work | Validation Owner |
|---|---|---|---|---|---|
| `<legacy request flow hook>` | `<valve chain registration>` | `<RCP-...>` | `<0-100>` | `<yes/no + details>` | `<team>` |
| `<legacy service registration>` | `<new service wiring>` | `<RCP-...>` | `<0-100>` | `<yes/no + details>` | `<team>` |

---

## 9) Execution wave plan

| Wave | Modules | Recipes Included | Entry Criteria | Exit Criteria | Status |
|---|---|---|---|---|---|
| Wave 1 | `<pilot modules>` | `<RCP list>` | `<baseline compile>` | `<compile+tests pass>` | Planned |
| Wave 2 | `<module set>` | `<RCP list>` | `<wave1 validated>` | `<compile+integration pass>` | Planned |
| Wave 3 | `<module set>` | `<RCP list>` | `<wave2 validated>` | `<full regression pass>` | Planned |

---

## 10) Risk register (recipe-level)

| Risk ID | Description | Related Recipe(s) | Probability | Impact | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|---|
| RSK-001 | `<example risk>` | `<RCP-...>` | `<L/M/H>` | `<L/M/H>` | `<mitigation>` | `<team>` | Open |

---

## 11) CI/CD integration checklist

- [ ] Dry-run job in CI for selected recipes
- [ ] Apply job (manual approval gate)
- [ ] Report publishing (recipe datatables / diffs / metrics)
- [ ] Compile + unit + integration gates post-apply
- [ ] Artifact/version policy checks (Java 17 + Jakarta compatibility)

---

## 12) Metrics dashboard template

| Metric | Baseline | Current | Target | Notes |
|---|---|---|---|---|
| Files touched by recipes | `<n>` | `<n>` | `<n>` |  |
| Compile errors after apply | `<n>` | `<n>` | `0` |  |
| Deprecated/internal API usages | `<n>` | `<n>` | `0` |  |
| Manual remediation items | `<n>` | `<n>` | `<n>` |  |
| Validated recipes count | `<n>` | `<n>` | `<n>` |  |

---

## 13) Change log

| Version | Date | Updated By | Summary |
|---|---|---|---|
| v1.0 | `<YYYY-MM-DD>` | `<name/team>` | Initial starter catalog template |

