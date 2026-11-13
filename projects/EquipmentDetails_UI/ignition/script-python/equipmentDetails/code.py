def getMetrics(basePath):
    # Define the relative metrics you want for any machine
    metricNames = [
        "goodCount",
        "rejectCount",
        "totalCount",
        "downTime",
        "runTime",
        "idealCycleTime"
    ]

    # Build full tag paths dynamically
    tagPaths = [basePath + "/oee/oeeCore/" + name for name in metricNames]

    values = system.tag.readBlocking(tagPaths)

    results = []
    for i, name in enumerate(metricNames):
        results.append({"title": name, "value": values[i].value})

    return results