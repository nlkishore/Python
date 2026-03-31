# Turbine 3.x -> 7.x Verified Mapping Table (Jar-Checked)

Verification source used:

- `C:\Apache-Turbine-7.x\turbine-7.0\turbine-7.0.jar`

Method:

1. inspect Turbine 7 classes from jar
2. compare legacy Turbine 3 candidates (from backlog recipe set and prior migration notes)
3. classify each candidate as:
   - **UNCHANGED_IN_7**
   - **MOVED_IN_7**
   - **NOT_FOUND_IN_7_MANUAL**

> Important: This is a production-safety mapping table for automated rewrite boundaries.  
> Only `MOVED_IN_7` items with explicit old->new FQN are used in `ChangeType`.

## Verified mapping status

| Legacy candidate (Turbine 3.x) | Turbine 7.x status | Verified target in Turbine 7 | Automation decision |
|---|---|---|---|
| `org.apache.turbine.util.RunData` | UNCHANGED_IN_7 | `org.apache.turbine.util.RunData` | No rewrite needed |
| `org.apache.turbine.services.TurbineServices` | UNCHANGED_IN_7 | `org.apache.turbine.services.TurbineServices` | No rewrite needed |
| `org.apache.turbine.services.Service` | UNCHANGED_IN_7 | `org.apache.turbine.services.Service` | No rewrite needed |
| `org.apache.turbine.modules.Action` | UNCHANGED_IN_7 | `org.apache.turbine.modules.Action` | No rewrite needed |
| `org.apache.turbine.modules.Screen` | UNCHANGED_IN_7 | `org.apache.turbine.modules.Screen` | No rewrite needed |
| `org.apache.turbine.modules.Navigation` | UNCHANGED_IN_7 | `org.apache.turbine.modules.Navigation` | No rewrite needed |
| `org.apache.turbine.util.TemplateInfo` | MOVED_IN_7 | `org.apache.turbine.util.template.TemplateInfo` | Add `ChangeType` |
| `org.apache.turbine.services.security.TurbineSecurityService` | NOT_FOUND_IN_7_MANUAL | n/a | Manual mapping/backlog |
| `org.apache.turbine.services.localization.LocalizationService` | NOT_FOUND_IN_7_MANUAL | n/a | Manual mapping/backlog |

## Applied rewrite policy

- Keep `rewrite-turbine7-upgrade.yml` limited to:
  - jar-confirmed `MOVED_IN_7` mappings only
  - plus Jakarta servlet namespace updates
- Keep all `NOT_FOUND_IN_7_MANUAL` items in:
  - `rewrite-turbine7-manual-backlog.yml`
  - then resolve manually with service-level validation.

