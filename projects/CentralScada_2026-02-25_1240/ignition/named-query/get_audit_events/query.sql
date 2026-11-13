SELECT 
    audit_events_id,
    event_timestamp,
    actor,
    action,
    action_target,
    status_code,
    originating_system
FROM dbo.audit_events
WHERE
    (:startDate IS NULL OR event_timestamp >= :startDate)
AND
    (:endDate IS NULL OR event_timestamp <= :endDate)

AND (
    :filterType IS NULL
    OR :filterType = ''
    OR :filterType = 'all'
    OR (:filterType = 'user' AND actor IS NOT NULL)
    OR (:filterType = 'mail' AND action LIKE '%mail%')
    OR (:filterType = 'zone' AND action_target LIKE '%Zone%')
    OR (:filterType = 'action' AND action = :actionValue)
)

ORDER BY event_timestamp DESC;