# Deep Dive: Jetspeed 1.x & Adapter Patterns

## 1. Jetspeed 1.x on Jakarta EE: The "Iceberg" Problem
Converting Jetspeed 1.x to run on Jakarta EE (JDK 17+) is **not** merely a namespace search-and-replace (`javax.` -> `jakarta.`). It is a fundamental architectural mismatch.

### A. The Namespace is the Tip of the Iceberg
*   **Compilation**: You can run a script to change `javax.servlet` to `jakarta.servlet`.
*   **Runtime Failure**: Jetspeed 1.x relies on the **Servlet 2.3 API**. Jakarta EE 9+ implements **Servlet 5.0+**.
    *   **Removed Methods**: APIs used by Jetspeed (e.g., specific `HttpSession` management, deprecated logging in ServletContext) no longer exist.
    *   **Behavioral Changes**: strict rules on cookie handling, session implementation, and encoding.

### B. The "ECS" Architecture (Element Construction Set)
Jetspeed 1.x builds UI using **Apache ECS**.
*   **Pattern**: Java code creating HTML objects: `code.addElement(new TR().addElement(new TD("Hello")))`.
*   **Status**: ECS is **Retiring/Dead**. It is not Jakarta compatible and has no modern replacement.
*   **Impact**: **100% of UI code** in Jetspeed 1.x (Portlets) utilizing ECS must be rewritten to use a Template Engine (Velocity/Freemarker) or a modern UI framework. **No auto-migration possible.**

### C. Portlet API Incompatibility
*   Jetspeed 1.x uses a proprietary API that predates the standard Java Portlet API (JSR-168).
*   It cannot run strict JSR-168/286 portlets without substantial wrappers.
*   Modern Portlet containers (Pluto, Liferay) do not support the Jetspeed 1.x API.

---

## 2. Adapter Patterns: Bridging 3.x to 7.x

To reduce the need to rewrite *every* line of business logic, we can use **Adapter Patterns**.

### A. The "Static to Instance" Bridge (Torque)
**Problem**: Legacy code calls `BaseUserPeer.doSelect(criteria)`. Torque 6+ uses dependency injection (`userPeer.doSelect(criteria)`).

**Solution**: Regenerate `Base*Peer` classes to act as **Static Facades**.

**Concept Code (Java):**
```java
// REGENERATED BaseUserPeer.java (Custom Template)
public class BaseUserPeer {
    
    // Bridge: Static method looks up the generic service
    public static List<User> doSelect(Criteria c) throws TorqueException {
        // "LegacyServiceLocator" is a new helper you must write
        UserPeer instance = LegacyServiceLocator.getService(UserPeer.class);
        return instance.doSelect(c);
    }
}
```
*   **Pros**: 50,000+ lines of "Business Logic" calling `BaseUserPeer.doSelect` remain valid.
*   **Cons**: slightly slower (service lookup), but acceptable for migration.

### B. The "Turbine RunData" Adapter
**Problem**: Turbine 7.x changes the `RunData` interface and how functionality is accessed (Pipeline changes).

**Solution**: Create a `LegacyRunData` wrapper.
1.  **Intercept**: In the new Turbine 7 Pipeline, wrap the new `PipelineData` object into your custom `LegacyRunData`.
2.  **Delegate**:
    ```java
    public class LegacyRunData implements RunData {
        private final PipelineData modernData;
        
        public User getUser() {
            // Map new API to old API
            return (User) modernData.getUser(); 
        }
        
        public void setMessage(String msg) {
            // Adapter logic
        }
    }
    ```

---

## 3. Other Missing Concepts & Complexities

### A. Logging (Log4j 1.x -> Log4j 2.x)
*   Jetspeed/Turbine 2.x use `Category` and `Priority`.
*   **Fix**: Use the `log4j-1.2-api` bridge jar. It allows old calls to route to the new Log4j 2 core engine.

### B. Configuration (Commons Config)
*   Old: `TurbineResources.properties` accessed via static keys.
*   New: `commons-configuration2`.
*   **Risk**: properties files syntax changes (list handling). Keys might be renamed.
*   **Action**: Audit all `Turbine.getConfiguration().getString("...")` calls.

### C. Serialization (Castor)
*   As noted in search, `Castor 0.9.x` is used.
*   **Issue**: Likely incompatible with JDK 17 modules (reflection restrictions).
*   **Replacement**: JAXB (Jakarta XML Binding) or Jackson.
*   **Effort**: High. All XML mapping files (`mapping.xml`) must be converted to JAXB annotations or Jackson schemas.

## 4. Final Recommendation
1.  **Drop Jetspeed 1.x**: It is the "Anchor" implementation. Logic trapped in ECS/proprietary Portlets is technical debt that cannot be migrated, only rewritten.
2.  **Extract Service Layer**: Move all Torque/DB logic into a clean Service Layer.
3.  **Re-skin**: Build a modern UI (Spring Boot + React/Thymeleaf) that calls the Extracted Service Layer.
4.  **Do NOT** try to run Jetspeed 1.x on Jakarta EE. It is a dead end.
