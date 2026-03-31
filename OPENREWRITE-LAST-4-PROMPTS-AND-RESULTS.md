# OpenRewrite — Last 4 Prompt Queries and Results

Generated: `2026-03-25`

## 1) User prompt

“Create a recipe for known import changes between Torque 3.x and Torque 6.x , like Criteria class package change , replacement of MapBuilderr usgae in Torque 6.x , removeing Village package dependency in Toruque 6.x”

### Result

Requested the exact old→new mappings (FQNs) for:
- `Criteria` import/type
- `MapBuilder` replacement (including 1–2 Torque 3 usage snippets and the Torque 6 target API pattern)
- the specific “Village” package dependency (Java FQN(s) and/or Maven coordinates)

Provided guidance on how OpenRewrite recipes would be structured:
- built-in type/package migrations for deterministic imports
- custom Java recipes (or marker/skip) for MapBuilder usage replacements when semantics change
- build+source rewrite for removing the Village dependency and any related imports/usages

## 2) User prompt

“Explain about market approach in details”

### Result

Explained the **marker approach** used in modernization with OpenRewrite:
- apply recipes only when pattern matches are safe/deterministic
- otherwise **mark for manual review** (via comments and/or structured reporting)
- gate pipelines to fail/warn when unresolved markers remain

Clarified why this is important for Torque/Turbine modernization where changes can be semantic (Criteria/MapBuilder/generated stubs).

## 3) User prompt

“Update the document with new section for the given feedback.”

### Result

Updated:
- `C:\openRewrite\OPENREWRITE-LEGACY-TO-JAKARTAEE-JDK17.md`

Added a new dedicated section:
- **Torque 3.x -> Torque 6.x specific guidance**

Covered:
- generated stub/schema outputs should be regenerated (don’t hand-migrate)
- Criteria and MapBuilder semantic differences
- hybrid strategy: regenerate first + OpenRewrite for mechanical updates + custom recipes + marker/manual queue for non-deterministic cases

## 4) User prompt

“Lets move to separate document to explore more on openRewrite , features with the context the reaource is new to openRewrite , how to create recipes and step by step approach to use openRewrite , using the referance of  `C:\openRewrite\OPENREWRITE-LEGACY-TO-JAKARTAEE-JDK17.md`”

### Result

Created:
- `C:\openRewrite\OPENREWRITE-BEGINNER-GUIDE-RECIPES-STEPBYSTEP.md`

Included:
- OpenRewrite concepts (recipes, built-in vs custom, dry run)
- step-by-step adoption plan
- approach to custom recipe creation (YAML declarative vs Java recipes)
- mapping guidance to your reference migration document

*** End of document

