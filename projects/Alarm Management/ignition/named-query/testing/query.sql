SELECT TOP 10
	e.source,
    MAX(CASE WHEN d.propname = 'operatorMessage' THEN d.strvalue END) AS operatorMessage,
    MAX(CASE WHEN d.propname = 'index' THEN d.strvalue END) AS [index],
    MAX(CASE WHEN d.propname = 'alarmGroupId' THEN d.strvalue END) AS alarmGroupId,
    MAX(CASE WHEN d.propname = 'alarmCode' THEN d.strvalue END) AS alarmCode,
    MAX(CASE WHEN d.propname = 'severity' THEN d.strvalue END) AS severity,
    MAX(CASE WHEN d.propname = 'fbsSource' THEN d.strvalue END) AS fbsSource,
    COUNT(*) AS alarmCount,
    MAX(e.eventtime) AS lastOccurred
FROM alarm_events e
INNER JOIN alarm_event_data d
    ON e.id = d.id
GROUP BY e.source
ORDER BY alarmCount DESC;