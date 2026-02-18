# Strategy for Resolving Cyclic Dependencies in Legacy Migration

## The User's Proposition
> "Combine all files into a single component, then separate into different components based on certain criteria."

**Verdict: YES, this is the recommended "Nuclear Option" for deep legacy cycles.**
In academic software engineering, we try to fix cycles in place. In **Legacy Migration**, it is often faster to collapse the structure to fix the build, and then re-slice it correctly.

---

## Phase 1: The Collapse (Consolidation)
**Why?** Legacy projects often have "Fake Modules"—folders that look like modules but have circular calls (e.g., `OrderService` in Module A calls `CustomerService` in Module B, which calls `OrderService` to get history). Maven/Grade builds will fail instantly.

**Action:**
1.  **Merge Source Trees**: Move all `src/main/java` content from sub-components into a single `monolith/src/main/java`.
2.  **Flatten Resources**: Merge `src/main/resources`.
3.  **Unified POM**: Create one `pom.xml` with ALL 3rd party dependencies.
4.  **Verify Build**: Ensure the project compiles as one unit. Cycles within a single module are allowed by the Java compiler (at class level), whereas cycles between Maven modules are forbidden.

## Phase 2: Analysis (The Tangle)
Once it compiles, you can use IDE tools to see the truth.

*   **Tools**: Use IntelliJ "Analyze > Analyze Cyclic Dependencies" or JArchitect.
*   **Identify the "God Classes"**: Usually, there are 1-2 core classes (e.g., `GlobalCache`, `BaseObject`) that everyone touches.

## Phase 3: The Split (Re-Modularization Criteria)
Do not split by "Layer" (DAO, Service, Web) as this often causes cycles. Split by **Stability** and **Domain**.

### Step 3.1: Extract "Shared Kernel" (Level 0)
Create a module `common-utils` or `shared-kernel`.
*   **Criteria**: Code that depends on NOTHING but JDK and 3rd party libs.
*   **Candidates**: `StringUtil`, `DateUtil`, `Constants`, exceptions.
*   *Move these first.*

### Step 3.2: Extract "API / Contracts" (Level 1)
To break a cycle where A calls B and B calls A:
1.  Create a module `core-api`.
2.  Extract **Interfaces** only.
    *   Move `IOrderService` and `ICustomerService` to `core-api`.
    *   Move DTOs (Data Objects) they use to `core-api`.
3.  **Result**: Implementation A depends on `core-api`. Implementation B depends on `core-api`. **Cycle Broken.**

### Step 3.3: Vertical Slices (Level 2)
Try to group by feature, not technical function.
*   `mod-sales` (Orders, Invoices)
*   `mod-crm` (Customers)
*   If `mod-sales` needs customer data, it uses the **Interface** from Step 3.2, injected at runtime (Dependency Injection).

## Summary: The Workflow
1.  **Collapse** to `src/main/java`.
2.  **Refactor** locally (IDE rename, move).
3.  **Extract** `common-utils` (No dependencies).
4.  **Extract** `core-api` (Interfaces & POJOs).
5.  **Extract** Feature Modules (Implementations).

## Alternative: Build-Time Cycle Breaker (Not Recommended)
You can use tools like "maven-build-helper" to add multiple source directories, but this hides the problem. The "Collapse and Split" method forces you to fix the architecture.
