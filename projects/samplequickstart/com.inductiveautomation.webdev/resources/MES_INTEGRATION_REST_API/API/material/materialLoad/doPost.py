def doPost(request, session):


    import system
    import mesClient

    logger = system.util.getLogger("MES_MATERIAL_DOWNLOAD")

    try:
        mesUrl = "https://aprisomesdev.agratas.com/apriso/httpServices/operations/SCADAInboundExecution"

        payload = request["data"]

        logger.info("Received Payload : " + system.util.jsonEncode(payload))

        mesResponse = mesClient.postToMES(
            mesUrl,
            payload
        )

        logger.info("MES Response : " + system.util.jsonEncode(mesResponse))

        return {
            "json": {
                "ResultFlag": True,
                "Message": "Successfully posted to MES",
                "MESResponse": mesResponse
            }
        }

    except Exception as e:
        logger.error("MES API Error : " + str(e))

        return {
            "json": {
                "ResultFlag": False,
                "Message": str(e)
            }
        }