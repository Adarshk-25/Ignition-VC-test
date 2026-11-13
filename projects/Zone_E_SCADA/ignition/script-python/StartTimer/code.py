alarmName = payload["Alarm Name"]

query = """
INSERT INTO alarm_duration_tracking
(alarm_name,start_time)
VALUES (?, GETDATE())
"""

system.db.runPrepUpdate(
    query,
    [alarmName]
)