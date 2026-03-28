# Turbine 3.x -> Turbine 7.x Summary and Recipe Plan

This note summarizes major migration themes and how to use OpenRewrite for:

1. automated package/type updates where mappings are deterministic
2. backlog detection where migration requires manual redesign

---

## 1) Key Turbine 3.x -> 7.x change themes

1. **Pipeline/Valve-centric flow**
   - Turbine 7 emphasizes pipeline/valve based processing.
   - Legacy action/screen/request hooks may need redesign, not just import updates.

2. **Service architecture evolution**
   - Many legacy Turbine service responsibilities moved or evolved (often Fulcrum-backed).
   - API/service lookup calls can require type and lifecycle updates.

3. **Configuration model differences**
   - Property keys and service wiring files may differ.
   - OpenRewrite can update keys/patterns if mappings are known.

4. **Jakarta + Java 17 alignment**
   - Servlet and related namespaces move to Jakarta.
   - Runtime/build plugin updates are required alongside framework migration.

---

## 2) OpenRewrite strategy for Turbine migration

### A) Automated updates (safe)

- deterministic package/type changes using `ChangeType` / `ChangePackage`
- import cleanup and formatting
- known config key string replacements

### B) Manual backlog generation

For areas where automated equivalent is uncertain:

- detect legacy Turbine classes/usages with `FindTypes`
- generate datatables
- extract into single CSV backlog using:
  - `scripts/extract_manual_backlog.py`

This gives a controlled list of files needing manual migration.

---

## 3) Recipe files added

- `rewrite/rewrite-turbine7-upgrade.yml`
  - starter deterministic mappings (candidate set; verify in your codebase)
- `rewrite/rewrite-turbine7-manual-backlog.yml`
  - detection-only recipe for legacy Turbine APIs likely requiring manual redesign

---

## 4) Suggested execution flow

1. Run detection first:
   - `mvn -Prewrite-turbine7-backlog rewrite:dryRun`
2. Extract consolidated backlog:
   - `python scripts/extract_manual_backlog.py --root . --out manual-migration-backlog.csv`
3. Run deterministic package/type upgrade:
   - `mvn -Prewrite-turbine7-upgrade rewrite:dryRun`
   - review diffs
   - `mvn -Prewrite-turbine7-upgrade rewrite:run`
4. Compile and validate:
   - `mvn compile`
5. Manually remediate backlog items and re-run profiles.

---

## 5) Important note

`rewrite-turbine7-upgrade.yml` is intentionally a **starter mapping set**.  
Before broad rollout, validate each old->new mapping against your exact Turbine 3.x and Turbine 7.x library versions and custom framework extensions.

