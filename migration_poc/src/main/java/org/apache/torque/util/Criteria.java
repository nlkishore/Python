package org.apache.torque.util;

// Adapter for Torque 6.x
// We explicitly place this in the "org.apache.torque.util" package 
// to trick the legacy imports.

import org.apache.torque.criteria.CriteriaInterface;

public class Criteria extends org.apache.torque.criteria.Criteria {
    // Torque 3.x methods that might be missing in Torque 6
    
    public Criteria() {
        super();
    }
    
    // Legacy method: add(String, int) - might be add(String, Object) in T6
    public Criteria add(String column, int value) {
        super.add(column, value);
        return this;
    }
}
