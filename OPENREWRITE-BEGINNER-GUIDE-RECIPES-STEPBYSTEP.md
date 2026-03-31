# OpenRewrite Beginner Guide (Using Legacy Modernization Context)

This guide is for team members who are new to OpenRewrite and want a practical, step-by-step way to use it for enterprise modernization.

Reference context document:  
`C:\openRewrite\OPENREWRITE-LEGACY-TO-JAKARTAEE-JDK17.md`

---

## 1) What is OpenRewrite (quick intro)

OpenRewrite is an automated refactoring framework for large codebases.  
It applies transformations through **recipes** and produces normal git diffs.

You use it to:

- modernize Java versions and build plugins
- migrate APIs/packages (for example `javax` to `jakarta`)
- update dependencies safely and repeatedly
- apply organization-wide code modernization rules

For your context (Turbine/Torque/Jetspeed modernization), OpenRewrite is ideal for **mechanical changes at scale**.

---

## 2) Core OpenRewrite concepts

### Recipe

A recipe is a transformation rule.  
Examples:

- change one Java type to another
- migrate deprecated API usage
- update Maven dependency coordinates

### Built-in vs custom recipe

- **Built-in recipes**: provided by OpenRewrite ecosystem (good starting point).
- **Custom recipes**: written by your team when framework-specific migration logic is needed (for example Torque/Turbine custom patterns).

### Dry run

Run recipes in analysis mode first to inspect expected changes before writing files.

### Data tables / reports

Many recipes produce reports that help prioritize and validate migration effort.

---

## 3) Where OpenRewrite helps most in your migration

From your reference document, the strongest automation zones are:

- Java 8 -> Java 17 build/source modernization
- Java EE -> Jakarta package/API migration
- dependency and plugin upgrades
- repetitive framework API changes where mapping is deterministic

Areas that still require architecture decisions:

- Turbine 3 -> 7 valve/pipeline redesign
- Torque behavior-level changes (`Criteria`, metadata/bootstrap semantics)
- runtime integration behavior validation

---

## 4) Prerequisites for first-time users

1. Java 17 installed.
2. Maven or Gradle project builds successfully in baseline branch.
3. Git branch dedicated for migration.
4. CI pipeline available for compile/test verification.
5. Small pilot module selected before full-repo run.

---

## 5) Step-by-step OpenRewrite adoption path

## Step 1: Baseline inventory

- capture current Java version, dependencies, plugin versions
- identify target modules for first pilot
- list high-risk framework hotspots (Turbine pipeline/services, Torque Criteria/MapBuilder)

Output: migration inventory sheet + pilot scope.

## Step 2: Start with built-in recipes only

For first execution, avoid custom recipes.  
Use well-known built-in recipes to reduce risk:

- Java version modernization recipes
- `javax` -> `jakarta` migration recipes
- Maven dependency/plugin upgrade recipes

Run in dry mode first, inspect diffs, then apply.

## Step 3: Validate after every recipe stage

After each stage:

1. compile
2. run tests
3. review changed files
4. commit separately

Use one commit per recipe-group for easier rollback.

## Step 4: Introduce custom recipes for framework-specific gaps

After built-in recipes stabilize, add custom recipes for:

- Torque-specific API migration patterns
- Turbine-specific API/config pattern rewrites
- standardization rules for your organization

## Step 5: Add governance in CI

Automate recipe execution checks:

- fail builds on unresolved deprecated/internal APIs
- publish recipe reports
- enforce approved dependency policies

## Step 6: Scale module by module

- move from pilot -> medium module -> full repo
- keep risk-based sequencing (P1 items first from your migration matrix)
- re-run recipes periodically to prevent drift

---

## 6) How to create custom recipes (beginner path)

### Option A: YAML declarative recipes (easiest start)

Use YAML when transformation is straightforward:

- changing dependency coordinates
- renaming types/packages with direct mapping
- composing multiple existing recipes

Best for teams new to OpenRewrite.

### Option B: Java-based recipes (advanced)

Use Java recipe classes when logic is pattern-sensitive:

- method invocation migration with signature/argument logic
- conditional transformations
- framework-specific flow changes

Typical pattern:

1. create recipe class
2. implement visitor (`JavaIsoVisitor`)
3. match nodes (`MethodMatcher`, type checks)
4. transform via templates
5. test recipe against sample input/output

---

## 7) Suggested recipe development lifecycle

1. **Identify pattern** (repeatable old -> new mapping).
2. **Create sample before/after cases**.
3. **Implement recipe** (YAML or Java).
4. **Run dry** on pilot module.
5. **Measure output** (files touched, compile breaks reduced).
6. **Validate runtime behavior** where needed.
7. **Promote to shared recipe catalog**.

---

## 8) Practical execution plan for your team (first 30-60 days)

### Week 1-2

- onboarding session for OpenRewrite basics
- pilot module selection
- run built-in dry runs and capture findings

### Week 3-4

- apply built-in recipe sets in staged commits
- establish compile/test gate template
- create first Torque/Turbine custom recipe backlog

### Week 5-8

- implement top-priority custom recipes
- integrate reports in CI
- expand rollout to additional modules

---

## 9) Common mistakes to avoid

- running too many recipe groups in one commit
- skipping dry run and review
- treating OpenRewrite as full architecture migration engine
- not involving runtime/system owners for pipeline/service behavior changes
- no regression gate for query-heavy Torque migrations

---

## 10) Checklist for new OpenRewrite users

- [ ] I understand built-in vs custom recipes.
- [ ] I can run dry run and interpret outputs.
- [ ] I can apply one recipe group and validate compile/tests.
- [ ] I know which migration items are mechanical vs architectural.
- [ ] I can create/update recipe backlog tables for Torque/Turbine.

---

## 11) How this guide maps to your existing document

Use this beginner guide as the "how to start" playbook, and use:  
`OPENREWRITE-LEGACY-TO-JAKARTAEE-JDK17.md` for:

- migration strategy and risk planning
- Torque/Turbine specific guidance
- combined migration matrix (priority, effort, risk)
- Java 17 strictness and third-party detection checklist

Together:

- **Beginner guide** = onboarding + execution method
- **Legacy migration guide** = architecture context + decision framework

---

## 12) Optional next enhancement

Create a third document with:

- actual starter recipe catalog template
- sample YAML recipe file structure
- sample Java custom recipe skeleton for Torque `Criteria` call migration

