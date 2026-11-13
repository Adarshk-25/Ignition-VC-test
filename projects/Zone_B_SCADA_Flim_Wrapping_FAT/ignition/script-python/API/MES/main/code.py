def sendProduction(machineId, shift, count):
    url = "https://mes.company.com/api/production"

    payload = {
        "machineId": machineId,
        "shift": shift,
        "count": count
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + system.tag.read("[default]MES/AuthToken").value
    }

    response = system.net.httpPost(
        url=url,
        contentType="application/json",
        postData=system.util.jsonEncode(payload),
        headers=headers
    )

    return response