def doPost(request, session):
	###############################################################################
	# Project        : AGRATAS SCADA - MES Integration
	# Interface      : M2S.RecipeDownload
	# Direction      : MES -> SCADA -> PLC
	# REST Direction : M2S
	# PLC Direction  : S2E
	# Module         : Ignition WebDev doPost
	#
	# PLC HEADER : AGRecipeHeader
	# --------------------------------
	# ProcessStep : WString
	# ProductID   : WString
	# UnitFBS     : WString
	# RecipeID    : WString
	#
	# PLC PARAMETERS : Array[0..4] of AGParameter
	# --------------------------------------------
	# ParameterRef  : WString
	# ParameterType : WString
	# ParameterUOM  : WString
	# USL           : Real
	# LSL           : Real
	# Setpoint      : Real
	#
	# MES -> PLC HEADER MAPPING
	# -------------------------
	# ProcessStep <- RecipeDownload.ProcessCode
	# ProductID   <- RecipeDownload.ProductNo
	# UnitFBS     <- RecipeDownload.EquipmentId
	# RecipeID    <- ProcessCode + "." + ProcessDescription
	#
	# MES -> PLC PARAMETER MAPPING
	# ----------------------------
	# ParameterRef  <- ParameterCode
	# ParameterType <- str(ParameterType)
	# ParameterUOM  <- ParameterUom
	# USL           <- UpperSpecificationLimit
	# LSL           <- LowerSpecificationLimit
	# Setpoint      <- TargetValue
	#
	# DYNAMIC OPC UA ROUTING
	# ----------------------
	# RecipeDownload.EquipmentId is used to dynamically construct the target
	# OPC UA ObjectId and MethodId.
	#
	# Example:
	#
	# EquipmentId = IN11.E123.PAE.NTC11
	#
	# ObjectId:
	# nsu=http://agratas.com/UA/;s=IN11.E123.PAE.NTC11/AGMethods
	#
	# MethodId:
	# nsu=http://agratas.com/UA/;s=IN11.E123.PAE.NTC11/AGMethods/SetRecipe
	#
	# This removes the hard-coded PLC equipment path and allows the same
	# M2S.RecipeDownload interface to route SetRecipe to different equipment
	# based on RecipeDownload.EquipmentId.
	#
	# IMPORTANT FOR IGNITION / SIEMENS OPC UA
	# ---------------------------------------
	# Siemens custom structures are represented as ExtensionObject values.
	#
	# DO NOT send:
	#     inputs = [plcHeader, plcParameters]
	#
	# because plcParameters becomes org.python.core.PyList and Ignition cannot
	# convert PyList -> ExtensionObject[].
	#
	# Send JSON STRING representations:
	#
	#     plcHeaderJson = system.util.jsonEncode(plcHeader)
	#     parametersJson = system.util.jsonEncode(plcParameters)
	#
	#     inputs = [
	#         plcHeaderJson,
	#         parametersJson
	#     ]
	###############################################################################
	
	
	from java.text import SimpleDateFormat
	from java.util import Date
	from java.util import TimeZone
	
	
	###############################################################################
	# Logger
	###############################################################################
	
	logger = system.util.getLogger(
	    "SetRecipePOC-m2s2e_agMethods"
	)
	
	
	###############################################################################
	# Constants
	###############################################################################
	
	PLC_PARAMETER_COUNT = 5
	
	
	###############################################################################
	# Helper : UTC Timestamp
	###############################################################################
	
	def getUtcTimestamp():
	
	    formatter = SimpleDateFormat(
	        "yyyy-MM-dd'T'HH:mm:ss'Z'"
	    )
	
	    formatter.setTimeZone(
	        TimeZone.getTimeZone("UTC")
	    )
	
	    return formatter.format(
	        Date()
	    )
	
	
	###############################################################################
	# Helper : JSON encode
	###############################################################################
	
	def jsonValue(value):
	
	    return system.util.jsonEncode(
	        value
	    )
	
	
	###############################################################################
	# Helper : Ordered MES response
	###############################################################################
	
	def buildResponseJson(
	    interfaceName,
	    transactionId,
	    resultFlag,
	    message
	):
	
	    responseTimestamp = getUtcTimestamp()
	
	    return (
	        "{"
	            "\"MessageHeader\":{"
	                "\"InterfaceName\":"
	                + jsonValue(interfaceName)
	                + ","
	
	                "\"TransactionId\":"
	                + jsonValue(transactionId)
	                + ","
	
	                "\"SourceSystem\":\"MES\","
	                "\"TargetSystem\":\"SCADA\","
	
	                "\"EventTimestamp\":"
	                + jsonValue(responseTimestamp)
	            + "},"
	
	            "\"RecipeDownload\":{"
	
	                "\"ResultFlag\":"
	                + jsonValue(str(resultFlag))
	                + ","
	
	                "\"Message\":"
	                + jsonValue(message)
	
	            + "}"
	        "}"
	    )
	
	
	###############################################################################
	# Helper : Safe String
	###############################################################################
	
	def safeString(value):
	
	    if value is None:
	        return ""
	
	    return str(value)
	
	
	###############################################################################
	# Helper : Safe Float
	###############################################################################
	
	def safeFloat(value):
	
	    if value is None:
	        return 0.0
	
	    try:
	
	        return float(value)
	
	    except:
	
	        return 0.0
	
	
	###############################################################################
	# Helper : Build RecipeID
	#
	# Example:
	#
	# ProcessCode     = PO_Mixing_100
	# ProcessDescription = 07
	#
	# RecipeID        = PO_Mixing_100.07
	###############################################################################
	
	def buildRecipeId(recipe):
	
	    processCode = safeString(
	        recipe.get(
	            "ProcessCode",
	            ""
	        )
	    )
	
	    processDescription = safeString(
	        recipe.get(
	            "ProcessDescription",
	            ""
	        )
	    )
	
	    if processCode != "" and processDescription != "":
	
	        return (
	            processCode
	            + "."
	            + processDescription
	        )
	
	    return processCode
	
	
	###############################################################################
	# Helper : Build PLC AGRecipeHeader
	###############################################################################
	
	def buildPlcHeader(recipe):
	
	    return {
	
	        "ProcessStep": safeString(
	            recipe.get(
	                "ProcessCode",
	                ""
	            )
	        ),
	
	        "ProductID": safeString(
	            recipe.get(
	                "ProductNo",
	                ""
	            )
	        ),
	
	        "UnitFBS": safeString(
	            recipe.get(
	                "EquipmentId",
	                ""
	            )
	        ),
	
	        "RecipeID": buildRecipeId(
	            recipe
	        )
	    }
	
	
	###############################################################################
	# Helper : Build PLC AGParameter
	###############################################################################
	
	def buildPlcParameter(parameter):
	
	    return {
	
	        "ParameterRef": safeString(
	            parameter.get(
	                "ParameterCode",
	                ""
	            )
	        ),
	
	        #######################################################################
	        # PLC ParameterType is WString.
	        # MES sends integer or string.
	        # Convert everything to String.
	        #######################################################################
	
	        "ParameterType": safeString(
	            parameter.get(
	                "ParameterType",
	                ""
	            )
	        ),
	
	        "ParameterUOM": safeString(
	            parameter.get(
	                "ParameterUom",
	                ""
	            )
	        ),
	
	        "USL": safeFloat(
	            parameter.get(
	                "UpperSpecificationLimit",
	                0.0
	            )
	        ),
	
	        "LSL": safeFloat(
	            parameter.get(
	                "LowerSpecificationLimit",
	                0.0
	            )
	        ),
	
	        "Setpoint": safeFloat(
	            parameter.get(
	                "TargetValue",
	                0.0
	            )
	        )
	    }
	
	
	###############################################################################
	# Helper : Empty PLC AGParameter
	#
	# PLC requires fixed Array[0..4].
	###############################################################################
	
	def buildEmptyPlcParameter():
	
	    return {
	
	        "ParameterRef": "",
	
	        "ParameterType": "",
	
	        "ParameterUOM": "",
	
	        "USL": 0.0,
	
	        "LSL": 0.0,
	
	        "Setpoint": 0.0
	    }
	
	
	###############################################################################
	# Default exception values
	###############################################################################
	
	interfaceName = "M2S.RecipeDownload"
	
	transactionId = ""
	
	
	###############################################################################
	# MAIN
	###############################################################################
	
	try:
	
	    ###########################################################################
	    # Step 1 : Read POST data
	    ###########################################################################
	
	    data = request[
	        "postData"
	    ]
	
	
	    ###########################################################################
	    # Step 2 : Decode when payload arrives as String
	    ###########################################################################
	
	    if isinstance(
	        data,
	        basestring
	    ):
	
	        data = system.util.jsonDecode(
	            data
	        )
	
	
	    ###########################################################################
	    # Step 3 : Validate MessageHeader
	    ###########################################################################
	
	    if "MessageHeader" not in data:
	
	        logger.warn(
	            "RecipeDownload rejected - MessageHeader missing"
	        )
	
	        request[
	            "servletResponse"
	        ].setStatus(
	            400
	        )
	
	        return {
	
	            "json": buildResponseJson(
	                interfaceName,
	                transactionId,
	                "400",
	                "MessageHeader is missing"
	            )
	        }
	
	
	    ###########################################################################
	    # Step 4 : Extract MessageHeader
	    ###########################################################################
	
	    messageHeader = data[
	        "MessageHeader"
	    ]
	
	
	    interfaceName = safeString(
	        messageHeader.get(
	            "InterfaceName",
	            "M2S.RecipeDownload"
	        )
	    )
	
	
	    transactionId = safeString(
	        messageHeader.get(
	            "TransactionId",
	            ""
	        )
	    )
	
	
	    ###########################################################################
	    # Step 5 : Validate RecipeDownload
	    ###########################################################################
	
	    if "RecipeDownload" not in data:
	
	        logger.warn(
	            "RecipeDownload rejected - RecipeDownload missing"
	        )
	
	        request[
	            "servletResponse"
	        ].setStatus(
	            400
	        )
	
	        return {
	
	            "json": buildResponseJson(
	                interfaceName,
	                transactionId,
	                "400",
	                "RecipeDownload is missing"
	            )
	        }
	
	
	    ###########################################################################
	    # Step 6 : Extract RecipeDownload
	    ###########################################################################
	
	    recipe = data[
	        "RecipeDownload"
	    ]
	
	
	    wipOrderNo = safeString(
	        recipe.get(
	            "WipOrderNo",
	            ""
	        )
	    )
	
	
	    equipmentId = safeString(
	        recipe.get(
	            "EquipmentId",
	            ""
	        )
	    )
	
	
	    ###########################################################################
	    # Step 7 : Log incoming request
	    ###########################################################################
	
	    logger.info(
	        "RecipeDownload received. "
	        "InterfaceName=%s, "
	        "TransactionId=%s, "
	        "WipOrderNo=%s, "
	        "EquipmentId=%s"
	        % (
	            interfaceName,
	            transactionId,
	            wipOrderNo,
	            equipmentId
	        )
	    )
	
	
	    ###########################################################################
	    # Step 8 : Validate MessageHeader fields
	    ###########################################################################
	
	    requiredHeaderFields = [
	
	        "InterfaceName",
	
	        "TransactionId",
	
	        "SourceSystem",
	
	        "TargetSystem",
	
	        "EventTimestamp"
	    ]
	
	
	    missingHeaderFields = []
	
	
	    for fieldName in requiredHeaderFields:
	
	        if fieldName not in messageHeader:
	
	            missingHeaderFields.append(
	                fieldName
	            )
	
	
	    if len(
	        missingHeaderFields
	    ) > 0:
	
	        errorMessage = (
	            "Missing MessageHeader fields: %s"
	            % ", ".join(
	                missingHeaderFields
	            )
	        )
	
	        logger.warn(
	            errorMessage
	        )
	
	        request[
	            "servletResponse"
	        ].setStatus(
	            400
	        )
	
	        return {
	
	            "json": buildResponseJson(
	                interfaceName,
	                transactionId,
	                "400",
	                errorMessage
	            )
	        }
	
	
	    ###########################################################################
	    # Step 9 : Validate fields required by current PLC mapping
	    ###########################################################################
	
	    requiredRecipeFields = [
	
	        "ProcessCode",
	
	        "ProcessDescription",
	
	        "ProductNo",
	
	        "EquipmentId",
	
	        "Operations"
	    ]
	
	
	    missingRecipeFields = []
	
	
	    for fieldName in requiredRecipeFields:
	
	        if fieldName not in recipe:
	
	            missingRecipeFields.append(
	                fieldName
	            )
	
	
	    if len(
	        missingRecipeFields
	    ) > 0:
	
	        errorMessage = (
	            "Missing RecipeDownload fields: %s"
	            % ", ".join(
	                missingRecipeFields
	            )
	        )
	
	        logger.warn(
	            errorMessage
	        )
	
	        request[
	            "servletResponse"
	        ].setStatus(
	            400
	        )
	
	        return {
	
	            "json": buildResponseJson(
	                interfaceName,
	                transactionId,
	                "400",
	                errorMessage
	            )
	        }
	
	
	    ###########################################################################
	    # Step 10 : Operations
	    ###########################################################################
	
	    operations = recipe.get(
	        "Operations",
	        []
	    )
	
	
	    if (
	        operations is None
	        or
	        len(operations) == 0
	    ):
	
	        logger.warn(
	            "RecipeDownload.Operations is empty. "
	            "TransactionId=%s"
	            % transactionId
	        )
	
	        request[
	            "servletResponse"
	        ].setStatus(
	            400
	        )
	
	        return {
	
	            "json": buildResponseJson(
	                interfaceName,
	                transactionId,
	                "400",
	                "RecipeDownload.Operations is empty"
	            )
	        }
	
	
	    ###########################################################################
	    # Step 11 : Build Header dictionary
	    ###########################################################################
	
	    plcHeader = buildPlcHeader(
	        recipe
	    )
	
	
	    ###########################################################################
	    # Step 12 : Build Parameters array
	    ###########################################################################
	
	    plcParameters = []
	
	
	    for operation in operations:
	
	        operationNo = safeString(
	            operation.get(
	                "OperationNo",
	                ""
	            )
	        )
	
	
	        mesParameters = operation.get(
	            "Parameters",
	            []
	        )
	
	
	        if mesParameters is None:
	
	            continue
	
	
	        for parameter in mesParameters:
	
	
	            ###################################################################
	            # PLC only supports indexes 0..4
	            ###################################################################
	
	            if len(
	                plcParameters
	            ) >= PLC_PARAMETER_COUNT:
	
	                break
	
	
	            parameterCode = safeString(
	                parameter.get(
	                    "ParameterCode",
	                    ""
	                )
	            )
	
	
	            ###################################################################
	            # Only fields existing in AGParameter are required.
	            ###################################################################
	
	            requiredParameterFields = [
	
	                "ParameterCode",
	
	                "ParameterType",
	
	                "ParameterUom",
	
	                "UpperSpecificationLimit",
	
	                "LowerSpecificationLimit",
	
	                "TargetValue"
	            ]
	
	
	            missingParameterFields = []
	
	
	            for fieldName in requiredParameterFields:
	
	                if fieldName not in parameter:
	
	                    missingParameterFields.append(
	                        fieldName
	                    )
	
	
	            if len(
	                missingParameterFields
	            ) > 0:
	
	                errorMessage = (
	                    "ParameterCode=%s missing fields: %s"
	                    % (
	                        parameterCode,
	                        ", ".join(
	                            missingParameterFields
	                        )
	                    )
	                )
	
	                logger.warn(
	                    "RecipeDownload rejected. "
	                    "TransactionId=%s, %s"
	                    % (
	                        transactionId,
	                        errorMessage
	                    )
	                )
	
	                request[
	                    "servletResponse"
	                ].setStatus(
	                    400
	                )
	
	                return {
	
	                    "json": buildResponseJson(
	                        interfaceName,
	                        transactionId,
	                        "400",
	                        errorMessage
	                    )
	                }
	
	
	            ###################################################################
	            # Map MES Parameter -> PLC AGParameter
	            ###################################################################
	
	            plcParameters.append(
	
	                buildPlcParameter(
	                    parameter
	                )
	            )
	
	
	        if len(
	            plcParameters
	        ) >= PLC_PARAMETER_COUNT:
	
	            break
	
	
	    ###########################################################################
	    # Step 13 : Require at least one parameter
	    ###########################################################################
	
	    if len(
	        plcParameters
	    ) == 0:
	
	        logger.warn(
	            "No PLC parameters generated. "
	            "TransactionId=%s"
	            % transactionId
	        )
	
	        request[
	            "servletResponse"
	        ].setStatus(
	            400
	        )
	
	        return {
	
	            "json": buildResponseJson(
	                interfaceName,
	                transactionId,
	                "400",
	                "No recipe parameters were supplied"
	            )
	        }
	
	
	    ###########################################################################
	    # Step 14 : Save real MES parameter count
	    ###########################################################################
	
	    actualParameterCount = len(
	        plcParameters
	    )
	
	
	    ###########################################################################
	    # Step 15 : Fill PLC Parameters[0..4]
	    ###########################################################################
	
	    while len(
	        plcParameters
	    ) < PLC_PARAMETER_COUNT:
	
	        plcParameters.append(
	            buildEmptyPlcParameter()
	        )
	
	
	    ###########################################################################
	    # Step 16 : Convert Siemens custom structures to JSON String
	    #
	    # Siemens method arguments are ExtensionObjects.
	    #
	    # Header custom structure and AGParameter[] must be supplied to Ignition
	    # as their JSON STRING representations.
	    #
	    # Do NOT pass plcParameters directly because it is a PyList.
	    ###########################################################################
	
	    plcHeaderJson = system.util.jsonEncode(
	        plcHeader
	    )
	
	
	    parametersJson = system.util.jsonEncode(
	        plcParameters
	    )
	
	
	    ###########################################################################
	    # Step 17 : Log final mapped PLC values
	    ###########################################################################
	
	    logger.info(
	        "PLC Header Mapping. "
	        "TransactionId=%s, "
	        "Payload=%s"
	        % (
	            transactionId,
	            plcHeaderJson
	        )
	    )
	
	
	    logger.info(
	        "PLC Parameter Mapping. "
	        "TransactionId=%s, "
	        "MESParameterCount=%s, "
	        "PLCArrayCount=%s, "
	        "Payload=%s"
	        % (
	            transactionId,
	            str(
	                actualParameterCount
	            ),
	            str(
	                len(
	                    plcParameters
	                )
	            ),
	            parametersJson
	        )
	    )
	
	
	    ###########################################################################
	    # Step 18 : Dynamic OPC UA Configuration
	    #
	    # RecipeDownload.EquipmentId is used as the PLC / equipment node prefix.
	    #
	    # Example:
	    #
	    # EquipmentId:
	    #     IN11.E123.PAE.NTC11
	    #
	    # ObjectId:
	    #     nsu=http://agratas.com/UA/;
	    #     s=IN11.E123.PAE.NTC11/AGMethods
	    #
	    # MethodId:
	    #     nsu=http://agratas.com/UA/;
	    #     s=IN11.E123.PAE.NTC11/AGMethods/SetRecipe
	    #
	    # This allows one WebDev RecipeDownload implementation to dynamically
	    # route to multiple PLC / equipment SetRecipe methods.
	    ###########################################################################
	
	    connectionName = "PLC"
	
	
	    objectId = (
	        "nsu=http://agratas.com/UA/;"
	        "s="
	        + equipmentId
	        + "/AGMethods"
	    )
	
	
	    methodId = (
	        "nsu=http://agratas.com/UA/;"
	        "s="
	        + equipmentId
	        + "/AGMethods/SetRecipe"
	    )
	
	
	    ###########################################################################
	    # Step 19 : Log dynamic OPC UA routing
	    ###########################################################################
	
	    logger.info(
	        "Dynamic OPC UA routing. "
	        "TransactionId=%s, "
	        "EquipmentId=%s, "
	        "Connection=%s, "
	        "ObjectId=%s, "
	        "MethodId=%s"
	        % (
	            transactionId,
	            equipmentId,
	            connectionName,
	            objectId,
	            methodId
	        )
	    )
	
	
	    ###########################################################################
	    # Step 20 : FINAL OPC UA INPUTS
	    #
	    # Input[0] = JSON String representing AGRecipeHeader
	    # Input[1] = JSON String representing AGParameter[5]
	    ###########################################################################
	
	    inputs = [
	
	        plcHeaderJson,
	
	        parametersJson
	    ]
	
	
	    ###########################################################################
	    # Step 21 : Diagnostic log
	    ###########################################################################
	
	    logger.info(
	        "Calling OPC UA SetRecipe. "
	        "TransactionId=%s, "
	        "EquipmentId=%s, "
	        "Connection=%s, "
	        "Object=%s, "
	        "Method=%s, "
	        "InputCount=%s, "
	        "ParameterCount=%s"
	        % (
	            transactionId,
	            equipmentId,
	            connectionName,
	            objectId,
	            methodId,
	            str(
	                len(
	                    inputs
	                )
	            ),
	            str(
	                len(
	                    plcParameters
	                )
	            )
	        )
	    )
	
	
	    logger.info(
	        "OPC UA Input[0] Header JSON=%s"
	        % plcHeaderJson
	    )
	
	
	    logger.info(
	        "OPC UA Input[1] Parameters JSON=%s"
	        % parametersJson
	    )
	
	
	    ###########################################################################
	    # Step 22 : Call PLC SetRecipe
	    ###########################################################################
	
	    result = system.opcua.callMethod(
	        connectionName,
	        objectId,
	        methodId,
	        inputs
	    )
	
	
	    ###########################################################################
	    # Step 23 : Log complete result
	    ###########################################################################
	
	    logger.info(
	        "SetRecipe OPC UA call completed. "
	        "TransactionId=%s, "
	        "EquipmentId=%s, "
	        "Result=%s"
	        % (
	            transactionId,
	            equipmentId,
	            str(
	                result
	            )
	        )
	    )
	
	
	    ###########################################################################
	    # Step 24 : Log individual result sections
	    #
	    # callMethod result:
	    #
	    # result[0] = Method StatusCode
	    # result[1] = Individual input argument StatusCodes
	    # result[2] = Output arguments
	    ###########################################################################
	
	    try:
	
	        logger.info(
	            "SetRecipe MethodStatus=%s, "
	            "InputStatus=%s, "
	            "Outputs=%s"
	            % (
	                str(
	                    result[0]
	                ),
	                str(
	                    result[1]
	                ),
	                str(
	                    result[2]
	                )
	            )
	        )
	
	    except:
	
	        pass
	
	
	    ###########################################################################
	    # Step 25 : Success
	    ###########################################################################
	
	    request[
	        "servletResponse"
	    ].setStatus(
	        200
	    )
	
	
	    responseJson = buildResponseJson(
	        interfaceName,
	        transactionId,
	        "200",
	        "Recipe downloaded to PLC successfully"
	    )
	
	
	    logger.info(
	        "RecipeDownload completed successfully. "
	        "TransactionId=%s, "
	        "EquipmentId=%s, "
	        "Response=%s"
	        % (
	            transactionId,
	            equipmentId,
	            responseJson
	        )
	    )
	
	
	    return {
	
	        "json": responseJson
	    }
	
	
	###############################################################################
	# Exception Handling
	###############################################################################
	
	except Exception as error:
	
	    logger.error(
	        "M2S.RecipeDownload failed. "
	        "TransactionId=%s, "
	        "Error=%s"
	        % (
	            str(
	                transactionId
	            ),
	            str(
	                error
	            )
	        )
	    )
	
	
	    request[
	        "servletResponse"
	    ].setStatus(
	        500
	    )
	
	
	    responseJson = buildResponseJson(
	        interfaceName,
	        transactionId,
	        "500",
	        "Recipe download failed: %s"
	        % str(
	            error
	        )
	    )
	
	
	    return {
	
	        "json": responseJson
	    }