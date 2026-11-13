def doPost(request, session):


    import system
    import mesclient_noauth

    logger = system.util.getLogger("MES_MATERIAL_DOWNLOAD")

    try:
        mesUrl = "https://aprisomesdev.agratas.com/apriso/httpServices/operations/AGR_PRD_S2M_MaterialInfo"

        payload = request["data"]

        logger.info("Received Payload : " + system.util.jsonEncode(payload))

        mesResponse = mesclient_noauth.postToMESNoAuth(
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