# Analysis: Migrating Torque 3.x to 7.x without `schema.xml`

## The Core Problem
You have a legacy application with generated Torque 3.x classes (`Base*`, `Peer*`) but are missing the source `schema.xml`. You wish to reuse these old classes with the new Torque 7.x runtime to avoid the risks of reverse-engineering the database.

## 1. Feasibility of Reusing Old Stubs (Option A)
**Verdict: Technically Impossible without Rewrite**

Attempts to compile or run Torque 3.x generated classes against Torque 7.x libraries will fail for these reasons:

1.  **The "Criteria" Mismatch**:
    *   **Old Code**: Imports `org.apache.torque.util.Criteria`.
    *   **New Runtime**: Expects `org.apache.torque.criteria.Criteria`.
    *   **Impact**: Every `doSelect(Criteria c)` call in your old stubs has the wrong method signature. You would have to re-compile the old stubs, which would fail because the old `Criteria` class doesn't exist in Torque 7.

2.  **Base Class Removal**:
    *   Old `Peer` classes extend `org.apache.torque.util.BasePeer`.
    *   In Torque 7, `BasePeer` is either removed or has a completely different internal API. The static methods your old stubs rely on (`BasePeer.doSelect`, `BasePeer.executeQuery`) have changed or moved.

3.  **Result**: To "reuse" the stubs, you would have to modify the source code of every generated class to update imports and logic—effectively rewriting the generator manually.

## 2. Recommendation: Reverse Engineering "Safe Mode" (Option B)
Since reuse is broken, you **must** regenerate the stubs. To mitigate the risk of data gaps (PKs, Sequences), follow this "Safe Mode" workflow:

### Step 1: Automated Reverse Engineering
Use Torque's `torque:jdbc` Maven goal (or Ant task) to inspect the live database.
*   **What it captures well**: Table names, Column names, Types, Primary Keys (if defined in DB), Foreign Keys.
*   **What it might miss**: Accessor logic, custom indexes, specific "ID Broker" settings.

### Step 2: Metadata Recovery from Compiled Code
Since you don't have `schema.xml`, but you **do** have the compiled class files (or legacy source), you can cross-reference:
*   **Primary Keys**: Look at `BaseXxxPeer.java` -> `TABLE_NAME` and `buildCriteria` methods to see which columns were treated as PKs.
*   **Sequences**: Check `BaseXxxPeer.java` (or the map builder). If it uses `idMethod="native"`, it relies on the DB (safe). If it used `idMethod="idbroker"`, you will see references to `IDBroker` within the Peer class.

### Step 3: The "Diff" Test
1.  Run `torque:jdbc` to generate a candidate `schema.xml`.
2.  Generate code from this candidate schema (into a temp folder).
3.  Compare the **signatures** of the new `Base*` classes against your old `Base*` classes.
    *   *Check*: Do the getters/setters match? (e.g., `getUserId` vs `getId`).
    *   *Check*: Are the types consistent?

## 3. Dealing with Sequences & ID Brokers
*   **Sequences**: If your DB is Oracle/Postgres, Torque 7 `native` requires the generic sequence name or specific configuration.
    *   *Check*: Does the legacy app currently insert into `TURBINE_SCHEDULER_JOB`? Check if it uses a sequence.
*   **ID Broker**: If possible, **abandon** the ID Broker in favor of Native Sequences / Auto-Increment. ID Broker is a legacy bottleneck.

## Summary Recommenation
1.  **Do NOT try to reuse old stubs**. You will fall into "Dependency Hell".
2.  **Run Torque Reverse Engineering** against a production-clone DB.
3.  **Audit the generated schema** against your existing Java classes to ensure field names match.
