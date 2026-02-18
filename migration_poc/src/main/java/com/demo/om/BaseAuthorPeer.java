package com.demo.om;

import java.util.List;
import org.apache.torque.Torque;
import org.apache.torque.TorqueException;
// OLD TORQUE 3 IMPORT
import org.apache.torque.util.Criteria;
import org.apache.torque.util.BasePeer;

/**
 * SIMULATED GENERATED CODE FROM TORQUE 3.x
 * This represents the "Legacy Stub" we are trying to save.
 */
public abstract class BaseAuthorPeer extends BasePeer {

    public static final String TABLE_NAME = "AUTHOR";
    public static final String AUTHOR_ID = "AUTHOR.AUTHOR_ID";
    public static final String NAME = "AUTHOR.NAME";

    public static List doSelect(Criteria criteria) throws TorqueException {
        return BasePeer.doSelect(criteria);
    }

    public static void doDelete(Criteria criteria) throws TorqueException {
         BasePeer.doDelete(criteria, TABLE_NAME);
    }
}
