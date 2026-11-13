alarmName = payload["Alarm Name"]

query = """
UPDATE alarm_duration_tracking
SET
    end_time = GETDATE(),
    duration_seconds = DATEDIFF(
        SECOND,
        start_time,
        GETDATE()
    )
WHERE
    alarm_name = ?
    AND end_time IS NULL
"""

system.db.runPrepUpdate(
    query,
    [alarmName]
)