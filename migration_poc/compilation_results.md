# POC Results: Adapter Pattern for Torque 3 -> 6

## Experiment Setup
1.  **Schema**: Defined `AUTHOR` and `BOOK` tables.
2.  **Legacy Code**: Created `BaseAuthorPeer.java` (simulating Torque 3 generated code).
3.  **Adapter Layer**: Created `org.apache.torque.util.BasePeer` and `Criteria` to bridge the gap.

## Findings

### 1. Compilation "Success" (False Positive)
With the adapters in place, the legacy `BaseAuthorPeer` **might compile** because:
*   `BaseAuthorPeer` calls `BasePeer.doSelect(Criteria)`.
*   Our Adapter `BasePeer` exists and has that method.
*   Our Adapter `Criteria` extends the new Torque 6 `Criteria`.

### 2. Runtime Failure (The Real Issue)
The adapter method `BasePeer.doSelect(Criteria)` is impossible to implement correctly in a generic way for Torque 6.

**Code:**
```java
// In Adapter BasePeer.java
public static List doSelect(Criteria criteria) {
    // ERROR: In Torque 6, criteria object doesn't strictly own the "Database Connection" or "Mapper" logic.
    // We need to know WHICH Peer class to ask to execute the select.
    // In Torque 3, BasePeer guessed this or handled it via the MapBuilder.
    // In Torque 6, this logic is moved to specific PeerImpl classes.
    throw new TorqueException("Cannot determine target table for generic select");
}
```

### 3. Missing Metadata
*   The legacy `BaseAuthorPeer` defines `TABLE_NAME` as a String.
*   Torque 6 expects table metadata to be loaded from `TableMap` classes which are structured differently.
*   The Adapter would need to **re-initialize** the entire Torque 6 runtime mapping system using the *old* MapBuilder pattern, which is removed in Torque 6.

## Conclusion
The Adapter pattern results in a **runtime-broken** application. To make it work, you would effectively have to rewrite the entire Torque 3 Core Runtime inside your adapter classes.

**Verdict**: Do not use Adapters. Regenerate the code.
