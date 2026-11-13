def getAlarm(groupId, alarmCode, FBS_Source):
    query = """
        SELECT OperatorMessage, Label, Troubleshoot
        FROM AlarmMaster
        WHERE AlarmGroupID = ? AND AlarmCode = ? AND FBS_Source = ?
    """

    rows = system.db.runPrepQuery(query, [groupId, alarmCode, FBS_Source])

    if rows:
        return rows[0]

    return None