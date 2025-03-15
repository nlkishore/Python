SELECT DISTINCT st.Assigned_USER_ID AS User_ID,st.Token_Serial_Number,
st.Company_NAME,
st.Company_ABBV_NAME,
MAX(a.Date_TIME) AS Max_Date_Time
FROM GTP_SECURITY_TOKEN st
LEFT JOIN GTP_AUDIT a ON st.Assigned_USER_ID = a.User_ID
LEFT JOIN GTP_AUDIT_ITEM ai ON a.AUDIT_ID = ai.AUDIT_ID
JOIN GTP_USERS u ON st.Assigned_USER_ID = u.User_ID
WHERE u.ACTV_FLAG = 'A'
GROUP BY st.Assigned_USER_ID, st.Token_Serial_Number, st.Company_NAME, st.Company_ABBV_NAME
HAVING MAX(a.Date_TIME) IS NULL OR MAX(a.Date_TIME) < ADD_MONTHS(SYSDATE, -12);
