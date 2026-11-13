SELECT
    a.eventtime AS EventTime,
    lbl.strvalue AS AlarmName,
    sev.intvalue AS Severity,
    opmsg.strvalue AS OperatorMessage,
    ts.strvalue AS Troubleshoot,
    c.eventtime AS ClearTime,
    ack.eventtime AS AckTime,
    fbs.strvalue AS FBSSource,

    RIGHT('00' + CAST(DATEDIFF(SECOND,a.eventtime,c.eventtime)/3600 AS VARCHAR),2)
    + ':' +
    RIGHT('00' + CAST((DATEDIFF(SECOND,a.eventtime,c.eventtime)%3600)/60 AS VARCHAR),2)
    + ':' +
    RIGHT('00' + CAST(DATEDIFF(SECOND,a.eventtime,c.eventtime)%60 AS VARCHAR),2)
    AS ActiveDuration

FROM alarm_events a

INNER JOIN alarm_events c
    ON a.eventid = c.eventid

LEFT JOIN alarm_event_data lbl
    ON a.id = lbl.id
    AND lbl.propname = 'label'

LEFT JOIN alarm_event_data sev
    ON a.id = sev.id
    AND sev.propname = 'Severity'

LEFT JOIN alarm_event_data opmsg
    ON a.id = opmsg.id
    AND opmsg.propname = 'Operator Message'
    
LEFT JOIN alarm_event_data ts
        ON a.id = ts.id
        AND ts.propname = 'Troubleshoot'
LEFT JOIN alarm_event_data fbs
    ON a.id = fbs.id
    AND fbs.propname = 'FBS Source'
    
LEFT JOIN alarm_events ack
    ON a.eventid = ack.eventid
    AND ack.eventtype = 2

WHERE a.eventtype = 0
AND c.eventtype = 1

ORDER BY c.eventtime DESC