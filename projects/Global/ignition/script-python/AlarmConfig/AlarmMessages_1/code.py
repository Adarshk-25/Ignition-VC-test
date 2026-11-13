def getAlarm(groupId, alarmCode):
    query = """
        SELECT OperatorMessage, Label, Troubleshoot
        FROM AlarmMaster
        WHERE AlarmGroupID = ? AND AlarmCode = ?
    """

    rows = system.db.runPrepQuery(query, [groupId, alarmCode])

    if rows:
        return rows[0]

    return None