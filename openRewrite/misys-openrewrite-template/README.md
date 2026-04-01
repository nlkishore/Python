# Misys OpenRewrite Multi-Module Template

## Today's Updates (2026-03-30)

- Added new Turbine migration recipe file: `rewrite/rewrite-turbine2-to-7-services.yml`.
- Added dedicated Maven profile: `rewrite-turbine2-to-7-services-only` in `pom.xml`.
- Added one-command usage for this profile (no `-Drewrite.activeRecipes` needed).
- Added Turbine 2.x service/controller/parser/Fulcrum-security run workflow.
- Updated Turbine migration summary document to include new recipe and profile flow.

This folder provides a concrete parent `pom.xml` + profile layout + recipe hierarchy for these modules:

- `com.misys.portal`
- `com.misys.portal.api`
- `com.misys.portal.common`
- `com.misys.portal.interfaces`
- `com.misys.portal.jetspeed`
- `com.misys.portal.webapp`
- `com.misys.portal.report`

## Structure

- `pom.xml`  
  Parent/aggregator with shared rewrite plugin configuration and profiles.
- `rewrite/rewrite-common.yml`  
  Safe baseline formatting/import cleanup.
- `rewrite/rewrite-jakarta.yml`  
  `javax` to `jakarta` migration set.
- `rewrite/rewrite-jdk17.yml`  
  Java 17 modernization recipes.
- `rewrite/rewrite-torque-turbine.yml`  
  Starter placeholder for framework-specific migration logic.
- `rewrite.yml`  
  Composite recipe (all modernization groups).

## Commands (run from this folder)

### Dry run by profile

```bash
mvn -Prewrite-baseline rewrite:dryRun
mvn -Prewrite-jdk17 rewrite:dryRun
mvn -Prewrite-jakarta rewrite:dryRun
mvn -Prewrite-torque-turbine rewrite:dryRun
mvn -Prewrite-torque7 rewrite:dryRun
mvn -Prewrite-detect-village rewrite:dryRun
mvn -Prewrite-turbine7-backlog rewrite:dryRun
mvn -Prewrite-turbine7-upgrade rewrite:dryRun
mvn -Prewrite-turbine2-to-7-services-only rewrite:dryRun
```

### Apply by profile

```bash
mvn -Prewrite-baseline rewrite:run
mvn -Prewrite-jdk17 rewrite:run
mvn -Prewrite-jakarta rewrite:run
mvn -Prewrite-torque-turbine rewrite:run
mvn -Prewrite-torque7 rewrite:run
mvn -Prewrite-detect-village rewrite:run
mvn -Prewrite-turbine7-backlog rewrite:run
mvn -Prewrite-turbine7-upgrade rewrite:run
mvn -Prewrite-turbine2-to-7-services-only rewrite:run
```

### Full composite run (optional)

```bash
mvn -Drewrite.configLocation=./rewrite.yml -Drewrite.activeRecipes=com.misys.rewrite.AllModernization rewrite:run
```

## Extract one CSV backlog from OpenRewrite datatables

After running `rewrite:dryRun` or `rewrite:run`, use:

```bash
python scripts/extract_manual_backlog.py --root . --out manual-migration-backlog.csv
```

This script scans module `target/rewrite/**` CSV datatables and produces a single file:

- `manual-migration-backlog.csv`

with normalized tracking columns:

- `module`
- `source_table`
- `source_csv`

plus all available datatable columns from OpenRewrite.

If no datatable CSVs are found, re-run rewrite with datatable export enabled and verify profile execution.

### Turbine backlog + upgrade workflow

```bash
# 1) Detect manual migration candidates
mvn -Prewrite-turbine7-backlog rewrite:dryRun

# 2) Build a single CSV backlog from datatables
python scripts/extract_manual_backlog.py --root . --out manual-migration-backlog.csv

# 3) Apply deterministic package/type updates
mvn -Prewrite-turbine7-upgrade rewrite:dryRun
mvn -Prewrite-turbine7-upgrade rewrite:run

# 4) Compile and continue manual remediation from backlog
mvn compile
```

### Turbine 2.x service/controller/parser/security workflow

```bash
# 1) Preview Turbine 2.x -> 7.x service/controller/parser/security changes
mvn -Prewrite-turbine2-to-7-services-only rewrite:dryRun

# 2) Apply deterministic changes
mvn -Prewrite-turbine2-to-7-services-only rewrite:run

# 3) Compile and validate
mvn compile
```

## Notes

- Keep profile runs in separate commits for safer rollback and review.
- Adjust module list in parent `pom.xml` to match your real folder structure.
- Replace placeholder framework mappings in `rewrite/rewrite-torque-turbine.yml` with verified old->new APIs.
- `rewrite/rewrite-torque7.yml` provides a **starter** Torque 3 usage detection + Criteria type migration; update the MapBuilder FQN/equivalent once verified for your Torque versions.
- `rewrite/rewrite-torque7-village-detect.yml` is a **detection-only** recipe to list files referencing Torque 3 classes and Village classes for manual remediation planning.
- `rewrite/rewrite-turbine7-manual-backlog.yml` detects legacy Turbine 3.x APIs for manual migration backlog generation.
- `rewrite/rewrite-turbine7-upgrade.yml` now contains a conservative confirmed-safe set only (TemplateInfo relocation + servlet jakarta namespace); use `rewrite-turbine7-backlog` for non-deterministic API migrations.
- `rewrite/rewrite-turbine2-to-7-services.yml` adds service/controller/parser/Fulcrum-security migration starters (plus backlog detection) for Turbine 2.x style code.
- `pom.xml` includes profile `rewrite-turbine2-to-7-services-only` so this recipe can run without `-Drewrite.activeRecipes`.
- Verified class mapping table: `rewrite/TURBINE3-TO-7-VERIFIED-MAPPING-TABLE.md`
- Legacy source paths are now centralized in parent `pom.xml` under:
  - `legacy.base.dir`
  - `legacy.source.dir.com.misys.portal`
  - `legacy.source.dir.com.misys.portal.api`
  - `legacy.source.dir.com.misys.portal.common`
  - `legacy.source.dir.com.misys.portal.interfaces`
  - `legacy.source.dir.com.misys.portal.jetspeed`
  - `legacy.source.dir.com.misys.portal.webapp`
  - `legacy.source.dir.com.misys.portal.report`

## Child modules created

- `com.misys.portal/pom.xml`
- `com.misys.portal.api/pom.xml`
- `com.misys.portal.common/pom.xml`
- `com.misys.portal.interfaces/pom.xml`
- `com.misys.portal.jetspeed/pom.xml`
- `com.misys.portal.webapp/pom.xml`
- `com.misys.portal.report/pom.xml`

Each child module supports:

1. copy sources from `${legacy.source.dir}` into `target/generated-sources/migrated`
2. add copied folder as Maven source root
3. apply OpenRewrite configuration through parent profiles
4. compile migrated sources with Java 17
