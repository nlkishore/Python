package com.demo.om;

import org.apache.torque.om.BaseObject;
import org.apache.torque.om.ComboKey;

/**
 * SIMULATED GENERATED CODE FROM TORQUE 3.x
 */
public abstract class BaseAuthor extends BaseObject {
    private int authorId;
    private String name;

    public int getAuthorId() {
        return authorId;
    }
    public void setAuthorId(int v) {
        this.authorId = v;
    }
    public String getName() {
        return name;
    }
    public void setName(String v) {
        this.name = v;
    }
}
