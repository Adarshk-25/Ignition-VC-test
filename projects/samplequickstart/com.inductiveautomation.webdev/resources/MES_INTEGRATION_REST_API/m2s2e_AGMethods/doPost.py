def doPost(request, session):
###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# Interface      : M2S -> S2E (REST API to OPC UA Method)
# API Name       : SetRecipe
# Module         : Ignition WebDev
# OPC UA Method  : AGMethods/SetRecipe
#
# Description:
#   1. Receives Recipe JSON payload through REST API.
#   2. Extracts Header and Recipe Parameters.
#   3. Converts payload into PLC expected JSON format.
#   4. Calls Siemens PLC OPC UA Method (SetRecipe).
#   5. Returns PLC response back to REST API caller.
#
# Version History
# -----------------------------------------------------------------------------
# Version | Date       | Author      | Description
# -----------------------------------------------------------------------------
# 1.0     | 13-Jul-2026| Hari        | Initial POC implementation
#
###############################################################################

    # Create Gateway Logger
    logger = system.util.getLogger("SetRecipePOC-m2s2e_agMethods")

    try:

        #######################################################################
        # Step 1 : Read incoming REST API JSON payload
        #######################################################################
        data = request["postData"]

        #######################################################################
        # Step 2 : Extract Header and Recipe Parameters
        #
        # Expected JSON Format:
        #
        # {
        #   "header": {...},
        #   "parameters": [...]
        # }
        #######################################################################
        header = data["header"]
        parameters = data["parameters"]

        #######################################################################
        # Step 3 : OPC UA Connection Details
        #######################################################################
        connectionName = "PLC"

        objectId = (
            "nsu=http://agratas.com/UA/;"
            "s=IN11.E305.PCE.CMS21/AGMethods"
        )

        methodId = (
            "nsu=http://agratas.com/UA/;"
            "s=IN11.E305.PCE.CMS21/AGMethods/SetRecipe"
        )

        #######################################################################
        # Step 4 : Convert Header and Parameters into JSON Strings
        #
        # PLC Method expects:
        # Input 1 -> Header JSON
        # Input 2 -> Parameters JSON Array
        #######################################################################
        inputs = [
            system.util.jsonEncode(header),
            system.util.jsonEncode(parameters)
        ]

        logger.info("Calling OPC UA Method : SetRecipe")

        #######################################################################
        # Step 5 : Invoke Siemens PLC OPC UA Method
        #######################################################################
        result = system.opcua.callMethod(
            connectionName,
            objectId,
            methodId,
            inputs
        )

        #######################################################################
        # Step 6 : Log PLC Response
        #######################################################################
        logger.info("OPC UA Result : %s" % str(result))

        #######################################################################
        # Step 7 : Return Success Response to REST API Caller
        #######################################################################
        return {
            "json": {
                "success": True,
                "message": "OPC UA Method executed successfully.",
                "result": str(result)
            }
        }

    except Exception as error:

        #######################################################################
        # Exception Handling
        #######################################################################
        logger.error("SetRecipe API failed : %s" % str(error))

        # Return HTTP Status 500
        request["servletResponse"].setStatus(500)

        # Return Error Response
        return {
            "json": {
                "success": False,
                "message": str(error)
            }
        }