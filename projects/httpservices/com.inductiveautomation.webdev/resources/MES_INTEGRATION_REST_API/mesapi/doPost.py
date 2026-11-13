def doPost(request, session):

    payload = request['data']

    system.util.getLogger("MES").info(str(payload))

    return {
        "json": {
            "status": "SUCCESS",
            "received": payload
        }
    }