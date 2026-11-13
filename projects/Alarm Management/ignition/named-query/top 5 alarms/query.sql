SELECT TOP 10
    source AS AlarmIdentifier,
    COUNT(*) AS OccurrenceCount
FROM
    alarm_events
GROUP BY
    source
ORDER BY
    OccurrenceCount DESC;
