def onTagChange(initialChange, newValue, previousValue, event, executionCount):
	###############################################################################
	# Project        : AGRATAS SCADA - MES Integration
	# Interface      : S2M.MaterialInfo
	# Module         : Ignition Gateway Tag Change Script
	# MES Operation  : AGR_PRD_S2M_MaterialInfo
	#
	# Description:
	#   1. Monitors AGSetItemInfo Handshake tags for multiple PLC/equipment folders.
	#   2. Determines the PLC/equipment dynamically from the triggering tag path.
	#   3. Processes the request when Handshake changes to 1.
	#   4. Reads RequestData and RequestAckNumber from the triggering PLC.
	#   5. Maps PLC request to MES MaterialInfo request.
	#   6. Calls MES.
	#   7. Maps MES response into PLC AGItemResponse.
	#   8. Writes ResponseData, StatusCode, ResponseTimestamp and
	#      ResponseAckNumber back to the SAME triggering PLC.
	#   9. Writes Handshake LAST.
	#
	# DYNAMIC EQUIPMENT ROUTING
	# -----------------------------------------------------------------------------
	#
	# The equipment is NOT hard-coded.
	#
	# The equipment folder is derived from the Gateway Tag Change event path:
	#
	#     event.getTagPath()
	#
	# Supported examples:
	#
	#   [default]IN11_E123_PAE_NTC11/AGCalls/AGSetItemInfo/Handshake
	#	[default]IN11_E123_PCE_NTC11/AGCalls/AGSetItemInfo/Handshake
	#	[default]IN11_B118_PPF_WRP11/AGCalls/AGSetItemInfo/Handshake
	#	[default]IN11_E112_PCE_CLD21/AGCalls/AGSetItemInfo/Handshake
	#	[default]IN11_E117_PCE_COT21/AGCalls/AGSetItemInfo/Handshake
	#
	# Example 1:
	#
	# Trigger:
	#   [default]IN11_E123_PAE_NTC11/AGCalls/AGSetItemInfo/Handshake
	#
	# Derived values:
	#
	#   equipment       = IN11_E123_PAE_NTC11
	#   feedingLocation = IN11_E123_PAE_NTC11
	#
	# Dynamic base path:
	#
	#   [default]IN11_E123_PAE_NTC11/AGCalls/AGSetItemInfo
	#
	#
	# Example 2:
	#
	# Trigger:
	#   [default]IN11_E123_PCE_NTC11/AGCalls/AGSetItemInfo/Handshake
	#
	# Derived values:
	#
	#   equipment       = IN11_E123_PCE_NTC11
	#   feedingLocation = IN11_E123_PCE_NTC11
	#
	# Dynamic base path:
	#
	#   [default]IN11_E123_PCE_NTC11/AGCalls/AGSetItemInfo
	#
	#
	# The following paths are generated dynamically:
	#
	#   RequestData
	#   RequestAckNumber
	#   ResponseData
	#   StatusCode
	#   ResponseTimestamp
	#   ResponseAckNumber
	#   Handshake
	#
	#
	# IMPORTANT - GATEWAY TAG CHANGE SCRIPT
	# -----------------------------------------------------------------------------
	#
	# Use:
	#
	#     event.getTagPath()
	#
	# to determine which configured Handshake tag triggered this script.
	#
	#
	# IMPORTANT - RESPONSE TIMESTAMP
	# -----------------------------------------------------------------------------
	#
	# ResponseTimestamp is an Ignition Date/DateTime tag.
	#
	# CORRECT:
	#
	#     responseTime = system.date.now()
	#     system.tag.writeBlocking([path], [responseTime])
	#
	# WRONG:
	#
	#     responseTime = system.date.format(...)
	#
	# Do not convert ResponseTimestamp to String before writing it to PLC.
	#
	#
	# HANDSHAKE RULE
	# -----------------------------------------------------------------------------
	#
	# Handshake = 0 -> Ignore
	# Handshake = 1 -> Process request
	# Handshake = 2 -> Ignore
	# Handshake = 3 -> MES skipped / error response
	#
	# For processing response:
	#
	#     ResponseData
	#     StatusCode
	#     ResponseTimestamp
	#     ResponseAckNumber
	#
	# are written first.
	#
	# Handshake is written LAST.
	#
	#
	# Version History
	# -----------------------------------------------------------------------------
	# Version | Date        | Description
	# -----------------------------------------------------------------------------
	# 1.0     | 19-Aug-2026 | Initial implementation
	# 1.9     | 21-Aug-2026 | Handshake written last
	# 2.0     | 23-Aug-2026 | Fixed ResponseTimestamp Date type conversion
	# 2.1     | 25-Aug-2026 | Dynamic equipment routing from Handshake tag path
	# 2.2     | 25-Aug-2026 | Use event.getTagPath() for Gateway Tag Change script
	# 2.3     | 25-Aug-2026 | New Node sets added - Coating / Caleder / Wraping
	###############################################################################
	
	
	import system
	import mesclient_noauth
	
	from java.text import SimpleDateFormat
	from java.util import Date
	from java.util import TimeZone
	
	
	###############################################################################
	# Logger
	###############################################################################
	
	logger = system.util.getLogger(
	    "FAT2_S2M_MATERIAL_INFO"
	)
	
	
	###############################################################################
	# Helper: Safely convert value to Unicode
	###############################################################################
	
	def safeUnicode(value, defaultValue=""):
	
	    if value is None:
	
	        return unicode(
	            defaultValue
	        )
	
	    try:
	
	        return unicode(
	            value
	        )
	
	    except Exception:
	
	        return unicode(
	            defaultValue
	        )
	
	
	###############################################################################
	# Helper: Extract Equipment from Gateway Tag Change event path
	#
	# Example input:
	#
	# [default]IN11_E123_PAE_NTC11/AGCalls/AGSetItemInfo/Handshake
	#
	# Output:
	#
	# providerPrefix = [default]
	# equipmentName  = IN11_E123_PAE_NTC11
	#
	###############################################################################
	
	def getEquipmentFromTagPath(triggerTagPath):
	
	    triggerPathString = safeUnicode(
	        triggerTagPath
	    ).strip()
	
	
	    if triggerPathString == "":
	
	        raise Exception(
	            "Trigger tag path is empty"
	        )
	
	
	    ###########################################################################
	    # Get first path section:
	    #
	    # [default]IN11_E123_PAE_NTC11
	    ###########################################################################
	
	    firstSlashIndex = triggerPathString.find(
	        "/"
	    )
	
	
	    if firstSlashIndex < 0:
	
	        raise Exception(
	            "Invalid trigger tag path. "
	            "Unable to find equipment section. "
	            "TagPath=%s"
	            % triggerPathString
	        )
	
	
	    firstPathSegment = triggerPathString[
	        :firstSlashIndex
	    ]
	
	
	    ###########################################################################
	    # Separate Tag Provider from equipment
	    #
	    # Input:
	    # [default]IN11_E123_PAE_NTC11
	    #
	    # Output:
	    # providerPrefix = [default]
	    # equipmentName  = IN11_E123_PAE_NTC11
	    ###########################################################################
	
	    closingBracketIndex = firstPathSegment.find(
	        "]"
	    )
	
	
	    if closingBracketIndex >= 0:
	
	        providerPrefix = firstPathSegment[
	            :closingBracketIndex + 1
	        ]
	
	        equipmentName = firstPathSegment[
	            closingBracketIndex + 1:
	        ]
	
	
	    else:
	
	        #######################################################################
	        # Fallback if provider is not included
	        #######################################################################
	
	        providerPrefix = "[default]"
	
	        equipmentName = firstPathSegment
	
	
	    equipmentName = safeUnicode(
	        equipmentName
	    ).strip()
	
	
	    if equipmentName == "":
	
	        raise Exception(
	            "Equipment name could not be extracted. "
	            "TagPath=%s"
	            % triggerPathString
	        )
	
	
	    return {
	
	        "triggerTagPath": triggerPathString,
	
	        "providerPrefix": providerPrefix,
	
	        "equipmentName": equipmentName
	    }
	
	
	###############################################################################
	# Helper: Format Java Date for logging only
	###############################################################################
	
	def formatDateForLog(dateValue):
	
	    if dateValue is None:
	
	        return ""
	
	
	    try:
	
	        return system.date.format(
	            dateValue,
	            "yyyy-MM-dd'T'HH:mm:ss.SSS"
	        )
	
	    except Exception:
	
	        return str(
	            dateValue
	        )
	
	
	###############################################################################
	# Helper: Convert MES value to Boolean
	###############################################################################
	
	def convertToBoolean(value):
	
	    if value is None:
	
	        return False
	
	
	    if isinstance(
	        value,
	        basestring
	    ):
	
	        normalizedValue = safeUnicode(
	            value
	        ).strip().lower()
	
	
	        return normalizedValue in [
	
	            "true",
	
	            "1",
	
	            "yes",
	
	            "y",
	
	            "pass",
	
	            "passed",
	
	            "good",
	
	            "ok",
	
	            "success",
	
	            "authorized"
	        ]
	
	
	    return bool(
	        value
	    )
	
	
	###############################################################################
	# Helper: Convert MES QualityStatus to PLC Boolean
	###############################################################################
	
	def convertQualityStatusToBoolean(value):
	
	    if value is None:
	
	        return False
	
	
	    try:
	
	        normalizedValue = safeUnicode(
	            value
	        ).strip().lower()
	
	    except Exception:
	
	        return False
	
	
	    return normalizedValue == "pass"
	
	
	###############################################################################
	# Helper: Create Empty PLC Response
	###############################################################################
	
	def createEmptyPLCResponse():
	
	    return {
	
	        "ItemID": "",
	
	        "BatchID": "",
	
	        "ExpiryDate": "",
	
	        "QualityStatus": False,
	
	        "Authorized": False,
	
	        "RecipeId": "",
	
	        "WorkOrderID": ""
	    }
	
	
	###############################################################################
	# Helper: Validate PLC Tag Writes
	###############################################################################
	
	def validateWriteResults(
	    writePaths,
	    writeValues,
	    writeResults
	):
	
	    failedWrites = []
	
	
	    for index in range(
	        len(writeResults)
	    ):
	
	        qualityCode = writeResults[
	            index
	        ]
	
	
	        if qualityCode.isGood():
	
	            logger.info(
	                "PLC tag write successful. "
	                "Path=%s, "
	                "Value=%s, "
	                "Quality=%s"
	                % (
	                    writePaths[index],
	                    str(
	                        writeValues[index]
	                    ),
	                    str(
	                        qualityCode
	                    )
	                )
	            )
	
	
	        else:
	
	            failedWrites.append(
	                "%s=%s"
	                % (
	                    writePaths[index],
	                    str(
	                        qualityCode
	                    )
	                )
	            )
	
	
	            logger.error(
	                "PLC tag write failed. "
	                "Path=%s, "
	                "Value=%s, "
	                "Quality=%s"
	                % (
	                    writePaths[index],
	                    str(
	                        writeValues[index]
	                    ),
	                    str(
	                        qualityCode
	                    )
	                )
	            )
	
	
	    if len(
	        failedWrites
	    ) > 0:
	
	        raise Exception(
	            "One or more PLC tag writes failed: %s"
	            % ", ".join(
	                failedWrites
	            )
	        )
	
	
	###############################################################################
	# Helper: Write PLC Response
	###############################################################################
	
	def writePLCResponse(
	    responseDataPath,
	    statusCodePath,
	    responseTimePath,
	    responseAckNumberPath,
	    handshakePath,
	    responseData,
	    statusCode,
	    responseTime,
	    responseAckNumber,
	    handshake
	):
	
	    ###########################################################################
	    # Determine ResponseAckNumber
	    ###########################################################################
	
	    if int(
	        statusCode
	    ) == 200:
	
	        finalResponseAckNumber = responseAckNumber
	
	
	    else:
	
	        finalResponseAckNumber = ""
	
	
	    if finalResponseAckNumber is None:
	
	        finalResponseAckNumber = ""
	
	
	    finalResponseAckNumber = safeUnicode(
	        finalResponseAckNumber
	    ).strip()
	
	
	    ###########################################################################
	    # Ensure ResponseTimestamp is a Java Date
	    ###########################################################################
	
	    if responseTime is None:
	
	        responseTime = system.date.now()
	
	
	    ###########################################################################
	    # Build PLC ResponseData
	    ###########################################################################
	
	    plcResponseDocument = {
	
	        "ItemID": safeUnicode(
	            responseData.get(
	                "ItemID",
	                ""
	            )
	        ).strip(),
	
	        "BatchID": safeUnicode(
	            responseData.get(
	                "BatchID",
	                ""
	            )
	        ).strip(),
	
	        "ExpiryDate": safeUnicode(
	            responseData.get(
	                "ExpiryDate",
	                ""
	            )
	        ).strip(),
	
	        "QualityStatus": bool(
	            responseData.get(
	                "QualityStatus",
	                False
	            )
	        ),
	
	        "Authorized": bool(
	            responseData.get(
	                "Authorized",
	                False
	            )
	        ),
	
	        "RecipeId": safeUnicode(
	            responseData.get(
	                "RecipeId",
	                ""
	            )
	        ).strip(),
	
	        "WorkOrderID": safeUnicode(
	            responseData.get(
	                "WorkOrderID",
	                ""
	            )
	        ).strip()
	    }
	
	
	    ###########################################################################
	    # Convert Dictionary to Ignition Document
	    ###########################################################################
	
	    responseDataJson = system.util.jsonEncode(
	        plcResponseDocument
	    )
	
	
	    responseDataDocument = system.util.jsonDecode(
	        responseDataJson
	    )
	
	
	    ###########################################################################
	    # Log PLC Response
	    ###########################################################################
	
	    logger.info(
	        "Writing PLC response data and metadata. "
	        "ResponseData=%s, "
	        "StatusCode=%s, "
	        "ResponseTime=%s, "
	        "ResponseAckNumber=%s"
	        % (
	            responseDataJson,
	            str(
	                statusCode
	            ),
	            formatDateForLog(
	                responseTime
	            ),
	            finalResponseAckNumber
	        )
	    )
	
	
	    ###########################################################################
	    # Write ResponseData + Metadata
	    #
	    # IMPORTANT:
	    #
	    # responseTime is java.util.Date.
	    ###########################################################################
	
	    writePaths = [
	
	        responseDataPath,
	
	        statusCodePath,
	
	        responseTimePath,
	
	        responseAckNumberPath
	    ]
	
	
	    writeValues = [
	
	        responseDataDocument,
	
	        int(
	            statusCode
	        ),
	
	        responseTime,
	
	        finalResponseAckNumber
	    ]
	
	
	    writeResults = system.tag.writeBlocking(
	        writePaths,
	        writeValues
	    )
	
	
	    validateWriteResults(
	        writePaths,
	        writeValues,
	        writeResults
	    )
	
	
	    ###########################################################################
	    # Write Handshake LAST
	    ###########################################################################
	
	    logger.info(
	        "Writing PLC Handshake last. "
	        "Path=%s, "
	        "Value=%s"
	        % (
	            handshakePath,
	            str(
	                handshake
	            )
	        )
	    )
	
	
	    handshakeResult = system.tag.writeBlocking(
	
	        [
	            handshakePath
	        ],
	
	        [
	            int(
	                handshake
	            )
	        ]
	
	    )[0]
	
	
	    if not handshakeResult.isGood():
	
	        raise Exception(
	            "PLC Handshake write failed. "
	            "Path=%s, "
	            "Value=%s, "
	            "Quality=%s"
	            % (
	                handshakePath,
	                str(
	                    handshake
	                ),
	                str(
	                    handshakeResult
	                )
	            )
	        )
	
	
	    logger.info(
	        "PLC Handshake write successful. "
	        "Path=%s, "
	        "Value=%s, "
	        "Quality=%s"
	        % (
	            handshakePath,
	            str(
	                handshake
	            ),
	            str(
	                handshakeResult
	            )
	        )
	    )
	
	
	    return {
	
	        "writeResults": writeResults,
	
	        "handshakeResult": handshakeResult
	    }
	
	
	###############################################################################
	# Helper: Write PLC Failure Metadata
	###############################################################################
	
	def writePLCFailureMetadata(
	    statusCodePath,
	    responseTimePath,
	    responseAckNumberPath,
	    handshakePath,
	    statusCode,
	    responseTime,
	    handshake
	):
	
	    ###########################################################################
	    # Ensure Java Date
	    ###########################################################################
	
	    if responseTime is None:
	
	        responseTime = system.date.now()
	
	
	    metadataPaths = [
	
	        statusCodePath,
	
	        responseTimePath,
	
	        responseAckNumberPath
	    ]
	
	
	    metadataValues = [
	
	        int(
	            statusCode
	        ),
	
	        responseTime,
	
	        ""
	    ]
	
	
	    logger.info(
	        "Writing PLC failure metadata. "
	        "StatusCode=%s, "
	        "ResponseTime=%s, "
	        "ResponseAckNumber=<empty>"
	        % (
	            str(
	                statusCode
	            ),
	            formatDateForLog(
	                responseTime
	            )
	        )
	    )
	
	
	    metadataResults = system.tag.writeBlocking(
	        metadataPaths,
	        metadataValues
	    )
	
	
	    validateWriteResults(
	        metadataPaths,
	        metadataValues,
	        metadataResults
	    )
	
	
	    ###########################################################################
	    # Handshake LAST
	    ###########################################################################
	
	    handshakeResult = system.tag.writeBlocking(
	
	        [
	            handshakePath
	        ],
	
	        [
	            int(
	                handshake
	            )
	        ]
	
	    )[0]
	
	
	    if not handshakeResult.isGood():
	
	        raise Exception(
	            "PLC failure Handshake write failed. "
	            "Path=%s, "
	            "Value=%s, "
	            "Quality=%s"
	            % (
	                handshakePath,
	                str(
	                    handshake
	                ),
	                str(
	                    handshakeResult
	                )
	            )
	        )
	
	
	    logger.info(
	        "PLC failure Handshake write successful. "
	        "Path=%s, "
	        "Value=%s, "
	        "Quality=%s"
	        % (
	            handshakePath,
	            str(
	                handshake
	            ),
	            str(
	                handshakeResult
	            )
	        )
	    )
	
	
	###############################################################################
	# MAIN TAG CHANGE SCRIPT
	###############################################################################
	
	try:
	
	    logger.info(
	        "S2M MaterialInfo Gateway Tag Change script started"
	    )
	
	
	    ###########################################################################
	    # Ignore Initial Subscription
	    ###########################################################################
	
	    if initialChange:
	
	        logger.info(
	            "Initial tag change ignored"
	        )
	
	
	    else:
	
	        #######################################################################
	        # Step 1
	        #
	        # Get actual Handshake path that triggered this Gateway Tag Change.
	        #
	        # IMPORTANT:
	        #
	        # Use event.getTagPath().
	        #
	        # Do not use an undefined global variable named tagPath here.
	        #######################################################################
	
	        triggerTagPath = safeUnicode(
	            event.getTagPath()
	        ).strip()
	
	
	        logger.info(
	            "MaterialInfo Handshake event received. "
	            "TriggerTagPath=%s"
	            % triggerTagPath
	        )
	
	
	        #######################################################################
	        # Step 2
	        #
	        # Extract Equipment dynamically.
	        #
	        # Example:
	        #
	        # [default]IN11_E123_PAE_NTC11/AGCalls/AGSetItemInfo/Handshake
	        #
	        # ->
	        #
	        # Equipment = IN11_E123_PAE_NTC11
	        #######################################################################
	
	        equipmentInfo = getEquipmentFromTagPath(
	            triggerTagPath
	        )
	
	
	        providerPrefix = equipmentInfo[
	            "providerPrefix"
	        ]
	
	
	        equipmentName = equipmentInfo[
	            "equipmentName"
	        ]
	
	
	        #######################################################################
	        # Step 3
	        #
	        # Dynamic MES Values
	        #######################################################################
	
	        equipment = equipmentName
	
	        feedingLocation = equipmentName
	
	        employeeNo = "ADMIN"
	
	
	        logger.info(
	            "Dynamic equipment resolved. "
	            "TriggerTagPath=%s, "
	            "Provider=%s, "
	            "Equipment=%s, "
	            "FeedingLocation=%s"
	            % (
	                triggerTagPath,
	                providerPrefix,
	                equipment,
	                feedingLocation
	            )
	        )
	
	
	        #######################################################################
	        # Step 4
	        #
	        # Build dynamic AGSetItemInfo base path.
	        #######################################################################
	
	        agSetItemInfoBasePath = (
	            providerPrefix
	            + equipmentName
	            + "/AGCalls/AGSetItemInfo"
	        )
	
	
	        #######################################################################
	        # Step 5
	        #
	        # Build all PLC tag paths dynamically.
	        #######################################################################
	
	        requestDataPath = (
	            agSetItemInfoBasePath
	            + "/RequestData"
	        )
	
	
	        requestAckNumberPath = (
	            agSetItemInfoBasePath
	            + "/RequestAckNumber"
	        )
	
	
	        responseDataPath = (
	            agSetItemInfoBasePath
	            + "/ResponseData"
	        )
	
	
	        statusCodePath = (
	            agSetItemInfoBasePath
	            + "/StatusCode"
	        )
	
	
	        responseTimePath = (
	            agSetItemInfoBasePath
	            + "/ResponseTimestamp"
	        )
	
	
	        responseAckNumberPath = (
	            agSetItemInfoBasePath
	            + "/ResponseAckNumber"
	        )
	
	
	        handshakePath = (
	            agSetItemInfoBasePath
	            + "/Handshake"
	        )
	
	
	        #######################################################################
	        # Step 6
	        #
	        # Log dynamic routing.
	        #######################################################################
	
	        logger.info(
	            "Dynamic AGSetItemInfo routing resolved. "
	            "Equipment=%s, "
	            "BasePath=%s"
	            % (
	                equipment,
	                agSetItemInfoBasePath
	            )
	        )
	
	
	        logger.info(
	            "Dynamic PLC paths. "
	            "RequestData=%s, "
	            "RequestAckNumber=%s, "
	            "ResponseData=%s, "
	            "StatusCode=%s, "
	            "ResponseTimestamp=%s, "
	            "ResponseAckNumber=%s, "
	            "Handshake=%s"
	            % (
	                requestDataPath,
	                requestAckNumberPath,
	                responseDataPath,
	                statusCodePath,
	                responseTimePath,
	                responseAckNumberPath,
	                handshakePath
	            )
	        )
	
	
	        #######################################################################
	        # Step 7
	        #
	        # Read Handshake value from event.
	        #######################################################################
	
	        handshakeValue = int(
	            newValue.value
	        )
	
	
	        logger.info(
	            "Handshake value received. "
	            "Equipment=%s, "
	            "Handshake=%s"
	            % (
	                equipment,
	                str(
	                    handshakeValue
	                )
	            )
	        )
	
	
	        #######################################################################
	        # MES Configuration
	        #######################################################################
	
	        mesUrl = "https://aprisomesdev.agratas.com/apriso/httpServices/operations/AGR_PRD_S2M_MaterialInfo"
	        #mesUrl = "http://WIN-1CK15FVAFIR/apriso/httpServices/operations/AGR_PRD_S2M_MaterialInfo"
	
	
	        interfaceName = "S2M.MaterialInfo"
	
	        sourceSystem = "SCADA"
	
	        targetSystem = "MES"
	
	
	        #######################################################################
	        # Initialize RequestAckNumber
	        #######################################################################
	
	        requestAckNumber = ""
	
	
	        #######################################################################
	        # Handshake 0 or 2
	        #
	        # Ignore
	        #######################################################################
	
	        if handshakeValue in (
	            0,
	            2
	        ):
	
	            logger.info(
	                "Handshake=%s ignored. "
	                "Equipment=%s. "
	                "No MES call or PLC response write."
	                % (
	                    str(
	                        handshakeValue
	                    ),
	                    equipment
	                )
	            )
	
	
	        #######################################################################
	        # Handshake 1
	        #
	        # Process Request
	        #######################################################################
	
	        elif handshakeValue == 1:
	
	            logger.info(
	                "Valid MaterialInfo request received. "
	                "Equipment=%s"
	                % equipment
	            )
	
	
	            ###################################################################
	            # ResponseTimestamp must remain Java Date
	            ###################################################################
	
	            responseTime = system.date.now()
	
	
	            try:
	
	                ###############################################################
	                # Read PLC RequestData + RequestAckNumber
	                ###############################################################
	
	                logger.info(
	                    "Reading PLC request tags. "
	                    "Equipment=%s, "
	                    "RequestDataPath=%s, "
	                    "RequestAckNumberPath=%s"
	                    % (
	                        equipment,
	                        requestDataPath,
	                        requestAckNumberPath
	                    )
	                )
	
	
	                requestTagResults = system.tag.readBlocking([
	
	                    requestDataPath,
	
	                    requestAckNumberPath
	                ])
	
	
	                requestTagResult = requestTagResults[
	                    0
	                ]
	
	
	                requestAckNumberResult = requestTagResults[
	                    1
	                ]
	
	
	                logger.info(
	                    "PLC request tag read completed. "
	                    "Equipment=%s, "
	                    "RequestDataQuality=%s, "
	                    "RequestAckNumberQuality=%s"
	                    % (
	                        equipment,
	                        str(
	                            requestTagResult.quality
	                        ),
	                        str(
	                            requestAckNumberResult.quality
	                        )
	                    )
	                )
	
	
	                ###############################################################
	                # Validate RequestData Quality
	                ###############################################################
	
	                if not requestTagResult.quality.isGood():
	
	                    raise Exception(
	                        "PLC RequestData tag quality is bad. "
	                        "Equipment=%s, "
	                        "Path=%s, "
	                        "Quality=%s"
	                        % (
	                            equipment,
	                            requestDataPath,
	                            str(
	                                requestTagResult.quality
	                            )
	                        )
	                    )
	
	
	                ###############################################################
	                # Validate RequestAckNumber Quality
	                ###############################################################
	
	                if not requestAckNumberResult.quality.isGood():
	
	                    raise Exception(
	                        "PLC RequestAckNumber tag quality is bad. "
	                        "Equipment=%s, "
	                        "Path=%s, "
	                        "Quality=%s"
	                        % (
	                            equipment,
	                            requestAckNumberPath,
	                            str(
	                                requestAckNumberResult.quality
	                            )
	                        )
	                    )
	
	
	                ###############################################################
	                # Validate RequestData
	                ###############################################################
	
	                if requestTagResult.value is None:
	
	                    raise Exception(
	                        "PLC RequestData tag contains null. "
	                        "Path=%s"
	                        % requestDataPath
	                    )
	
	
	                plcRequestString = safeUnicode(
	                    requestTagResult.value
	                ).strip()
	
	
	                if plcRequestString == "":
	
	                    raise Exception(
	                        "PLC RequestData tag contains empty value. "
	                        "Path=%s"
	                        % requestDataPath
	                    )
	
	
	                ###############################################################
	                # Validate RequestAckNumber
	                ###############################################################
	
	                if requestAckNumberResult.value is None:
	
	                    raise Exception(
	                        "PLC RequestAckNumber tag contains null. "
	                        "Path=%s"
	                        % requestAckNumberPath
	                    )
	
	
	                requestAckNumber = safeUnicode(
	                    requestAckNumberResult.value
	                ).strip()
	
	
	                if requestAckNumber == "":
	
	                    raise Exception(
	                        "PLC RequestAckNumber tag contains empty value. "
	                        "Path=%s"
	                        % requestAckNumberPath
	                    )
	
	
	                logger.info(
	                    "PLC RequestData received. "
	                    "Equipment=%s, "
	                    "RequestData=%s"
	                    % (
	                        equipment,
	                        plcRequestString
	                    )
	                )
	
	
	                logger.info(
	                    "PLC RequestAckNumber received. "
	                    "Equipment=%s, "
	                    "RequestAckNumber=%s"
	                    % (
	                        equipment,
	                        requestAckNumber
	                    )
	                )
	
	
	                ###############################################################
	                # Decode PLC RequestData
	                ###############################################################
	
	                try:
	
	                    plcRequestObject = system.util.jsonDecode(
	                        plcRequestString
	                    )
	
	
	                except Exception as decodeError:
	
	                    raise Exception(
	                        "Invalid PLC RequestData JSON. "
	                        "Equipment=%s, "
	                        "Error=%s, "
	                        "Value=%s"
	                        % (
	                            equipment,
	                            str(
	                                decodeError
	                            ),
	                            plcRequestString
	                        )
	                    )
	
	
	                if not isinstance(
	                    plcRequestObject,
	                    dict
	                ):
	
	                    raise Exception(
	                        "PLC RequestData must be a JSON object"
	                    )
	
	
	                ###############################################################
	                # Extract PLC Request Values
	                ###############################################################
	
	                itemId = safeUnicode(
	                    plcRequestObject.get(
	                        "ItemID",
	                        ""
	                    )
	                ).strip()
	
	
	                recipeId = safeUnicode(
	                    plcRequestObject.get(
	                        "RecipeId",
	                        ""
	                    )
	                ).strip()
	
	
	                workOrderId = safeUnicode(
	                    plcRequestObject.get(
	                        "WorkOrderID",
	                        ""
	                    )
	                ).strip()
	
	
	                ###############################################################
	                # Mandatory Field Validation
	                ###############################################################
	
	                if itemId == "":
	
	                    raise Exception(
	                        "Mandatory field ItemID is missing"
	                    )
	
	
	                if recipeId == "":
	
	                    raise Exception(
	                        "Mandatory field RecipeId is missing"
	                    )
	
	
	                if workOrderId == "":
	
	                    raise Exception(
	                        "Mandatory field WorkOrderID is missing"
	                    )
	
	
	                ###############################################################
	                # Build MES UTC EventTimestamp
	                #
	                # MES receives STRING.
	                #
	                # PLC ResponseTimestamp remains Java Date.
	                ###############################################################
	
	                utcFormatter = SimpleDateFormat(
	                    "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"
	                )
	
	
	                utcFormatter.setTimeZone(
	                    TimeZone.getTimeZone(
	                        "UTC"
	                    )
	                )
	
	
	                eventTimestamp = utcFormatter.format(
	                    Date()
	                )
	
	
	                ###############################################################
	                # Transaction ID
	                ###############################################################
	
	                transactionFormatter = SimpleDateFormat(
	                    "yyyyMMddHHmmssSSS"
	                )
	
	
	                transactionFormatter.setTimeZone(
	                    TimeZone.getTimeZone(
	                        "UTC"
	                    )
	                )
	
	
	                transactionId = (
	                    "MAT-"
	                    + transactionFormatter.format(
	                        Date()
	                    )
	                )
	
	
	                ###############################################################
	                # Build MES Payload
	                #
	                # Equipment       = Dynamic equipment derived from tag path
	                # FeedingLocation = Dynamic equipment derived from tag path
	                ###############################################################
	
	                payload = {
	
	                    "Inputs": {
	
	                        "MessageHeader": {
	
	                            "InterfaceName": interfaceName,
	
	                            "TransactionId": transactionId,
	
	                            "SourceSystem": sourceSystem,
	
	                            "TargetSystem": targetSystem,
	
	                            "EventTimestamp": eventTimestamp,
	
	                            "Equipment": equipment,
	
	                            "EmployeeNo": employeeNo
	                        },
	
	
	                        "MaterialInfo": {
	                        	"OperationFlag": 1,
	
	                            "HuContainer": itemId,
	
	                            "FeedingLocation": feedingLocation,
	
	                            "WorkOrder": workOrderId,
	
	                            "RecipeID": recipeId
	                        }
	                    }
	                }
	
	
	                logger.info(
	                    "Calling MES MaterialInfo. "
	                    "Equipment=%s, "
	                    "TransactionId=%s, "
	                    "Payload=%s"
	                    % (
	                        equipment,
	                        transactionId,
	                        system.util.jsonEncode(
	                            payload
	                        )
	                    )
	                )
	
	
	                ###############################################################
	                # Call MES
	                ###############################################################
	
	                mesResponse = (
	                    mesclient_noauth.postToMESNoAuth(
	                        mesUrl,
	                        payload
	                    )
	                )
	
	
	                if mesResponse is None:
	
	                    raise Exception(
	                        "MES returned an empty response"
	                    )
	
	
	                logger.info(
	                    "MES raw response. "
	                    "Equipment=%s, "
	                    "TransactionId=%s, "
	                    "Response=%s"
	                    % (
	                        equipment,
	                        transactionId,
	                        str(
	                            mesResponse
	                        )
	                    )
	                )
	
	
	                ###############################################################
	                # Decode Outer MES Response
	                ###############################################################
	
	                if isinstance(
	                    mesResponse,
	                    basestring
	                ):
	
	                    try:
	
	                        mesOuterResponse = system.util.jsonDecode(
	                            safeUnicode(
	                                mesResponse
	                            )
	                        )
	
	
	                    except Exception as outerDecodeError:
	
	                        raise Exception(
	                            "MES outer response is invalid JSON. "
	                            "Error=%s, "
	                            "Response=%s"
	                            % (
	                                str(
	                                    outerDecodeError
	                                ),
	                                str(
	                                    mesResponse
	                                )
	                            )
	                        )
	
	
	                elif isinstance(
	                    mesResponse,
	                    dict
	                ):
	
	                    mesOuterResponse = mesResponse
	
	
	                else:
	
	                    raise Exception(
	                        "Unsupported MES response type: %s"
	                        % str(
	                            type(
	                                mesResponse
	                            )
	                        )
	                    )
	
	
	                ###############################################################
	                # Validate Outputs
	                ###############################################################
	
	                if "Outputs" not in mesOuterResponse:
	
	                    raise Exception(
	                        "MES response is missing Outputs"
	                    )
	
	
	                outputs = mesOuterResponse[
	                    "Outputs"
	                ]
	
	
	                if not isinstance(
	                    outputs,
	                    dict
	                ):
	
	                    raise Exception(
	                        "MES Outputs must be a JSON object"
	                    )
	
	
	                if "ResponseJSON" not in outputs:
	
	                    raise Exception(
	                        "MES response is missing Outputs.ResponseJSON"
	                    )
	
	
	                responseJsonValue = outputs[
	                    "ResponseJSON"
	                ]
	
	
	                if responseJsonValue is None:
	
	                    raise Exception(
	                        "MES Outputs.ResponseJSON is null"
	                    )
	
	
	                ###############################################################
	                # Decode ResponseJSON
	                ###############################################################
	
	                if isinstance(
	                    responseJsonValue,
	                    dict
	                ):
	
	                    mesInnerResponse = responseJsonValue
	
	
	                    responseJsonString = system.util.jsonEncode(
	                        responseJsonValue
	                    )
	
	
	                else:
	
	                    responseJsonString = safeUnicode(
	                        responseJsonValue
	                    ).strip()
	
	
	                    if responseJsonString == "":
	
	                        raise Exception(
	                            "MES Outputs.ResponseJSON is empty"
	                        )
	
	
	                    logger.info(
	                        "MES ResponseJSON received. "
	                        "Equipment=%s, "
	                        "ResponseJSON=%s"
	                        % (
	                            equipment,
	                            responseJsonString
	                        )
	                    )
	
	
	                    normalizedResponseJson = (
	                        responseJsonString
	                        .replace(
	                            ":False",
	                            ":false"
	                        )
	                        .replace(
	                            ":True",
	                            ":true"
	                        )
	                        .replace(
	                            ": False",
	                            ": false"
	                        )
	                        .replace(
	                            ": True",
	                            ": true"
	                        )
	                    )
	
	
	                    try:
	
	                        mesInnerResponse = system.util.jsonDecode(
	                            normalizedResponseJson
	                        )
	
	
	                    except Exception as innerDecodeError:
	
	                        raise Exception(
	                            "MES ResponseJSON is invalid JSON. "
	                            "Error=%s, "
	                            "ResponseJSON=%s"
	                            % (
	                                str(
	                                    innerDecodeError
	                                ),
	                                responseJsonString
	                            )
	                        )
	
	
	                if not isinstance(
	                    mesInnerResponse,
	                    dict
	                ):
	
	                    raise Exception(
	                        "MES ResponseJSON must be a JSON object"
	                    )
	
	
	                ###############################################################
	                # Validate MaterialInfo
	                ###############################################################
	
	                if "MaterialInfo" not in mesInnerResponse:
	
	                    raise Exception(
	                        "MES ResponseJSON is missing MaterialInfo"
	                    )
	
	
	                mesMaterialInfo = mesInnerResponse[
	                    "MaterialInfo"
	                ]
	
	
	                if not isinstance(
	                    mesMaterialInfo,
	                    dict
	                ):
	
	                    raise Exception(
	                        "MES MaterialInfo must be a JSON object"
	                    )
	
	
	                ###############################################################
	                # Authorization
	                ###############################################################
	
	                authorizationValue = mesMaterialInfo.get(
	                    "Authorization",
	                    False
	                )
	
	
	                authorized = convertToBoolean(
	                    authorizationValue
	                )
	
	
	                ###############################################################
	                # QualityStatus
	                ###############################################################
	
	                qualityStatusValue = mesMaterialInfo.get(
	                    "QualityStatus",
	                    None
	                )
	
	
	                qualityStatus = convertQualityStatusToBoolean(
	                    qualityStatusValue
	                )
	
	
	                ###############################################################
	                # RecipeID
	                ###############################################################
	
	                mesRecipeId = safeUnicode(
	                    mesMaterialInfo.get(
	                        "RecipeID",
	                        ""
	                    )
	                ).strip()
	
	
	                ###############################################################
	                # WorkOrder
	                ###############################################################
	
	                mesWorkOrderId = safeUnicode(
	                    mesMaterialInfo.get(
	                        "WorkOrder",
	                        ""
	                    )
	                ).strip()
	
	
	                logger.info(
	                    "MES business values mapped. "
	                    "Equipment=%s, "
	                    "AuthorizationRaw=%s, "
	                    "AuthorizedPLC=%s, "
	                    "QualityStatusRaw=%s, "
	                    "QualityStatusPLC=%s, "
	                    "RecipeID=%s, "
	                    "WorkOrder=%s"
	                    % (
	                        equipment,
	                        str(
	                            authorizationValue
	                        ),
	                        str(
	                            authorized
	                        ),
	                        str(
	                            qualityStatusValue
	                        ),
	                        str(
	                            qualityStatus
	                        ),
	                        mesRecipeId,
	                        mesWorkOrderId
	                    )
	                )
	
	
	                ###############################################################
	                # Build PLC AGItemResponse
	                ###############################################################
	
	                plcResponseObject = {
	
	                    "ItemID": safeUnicode(
	                        mesMaterialInfo.get(
	                            "HuContainer",
	                            itemId
	                        )
	                    ).strip(),
	
	                    "BatchID": safeUnicode(
	                        mesMaterialInfo.get(
	                            "BatchID",
	                            ""
	                        )
	                    ).strip(),
	
	                    "ExpiryDate": safeUnicode(
	                        mesMaterialInfo.get(
	                            "ExpiryDate",
	                            ""
	                        )
	                    ).strip(),
	
	                    "QualityStatus": bool(
	                        qualityStatus
	                    ),
	
	                    "Authorized": bool(
	                        authorized
	                    ),
	
	                    "RecipeId": mesRecipeId,
	
	                    "WorkOrderID": mesWorkOrderId
	                }
	
	
	                logger.info(
	                    "Mapped PLC AGItemResponse. "
	                    "Equipment=%s, "
	                    "Response=%s"
	                    % (
	                        equipment,
	                        system.util.jsonEncode(
	                            plcResponseObject
	                        )
	                    )
	                )
	
	
	                ###############################################################
	                # Successful MES Processing
	                ###############################################################
	
	                plcStatusCode = 200
	
	                responseHandshake = 2
	
	
	                ###############################################################
	                # Final PLC Response Timestamp
	                #
	                # Java Date - NOT STRING
	                ###############################################################
	
	                responseTime = system.date.now()
	
	
	                ###############################################################
	                # Write Response to SAME Triggering PLC
	                ###############################################################
	
	                writePLCResponse(
	                    responseDataPath,
	                    statusCodePath,
	                    responseTimePath,
	                    responseAckNumberPath,
	                    handshakePath,
	                    plcResponseObject,
	                    plcStatusCode,
	                    responseTime,
	                    requestAckNumber,
	                    responseHandshake
	                )
	
	
	                logger.info(
	                    "S2M MaterialInfo completed successfully. "
	                    "Equipment=%s, "
	                    "TransactionId=%s, "
	                    "RequestAckNumber=%s, "
	                    "ResponseAckNumber=%s, "
	                    "StatusCode=%s, "
	                    "Handshake=%s, "
	                    "Authorized=%s, "
	                    "QualityStatus=%s, "
	                    "RecipeId=%s, "
	                    "WorkOrderID=%s"
	                    % (
	                        equipment,
	                        transactionId,
	                        requestAckNumber,
	                        requestAckNumber,
	                        str(
	                            plcStatusCode
	                        ),
	                        str(
	                            responseHandshake
	                        ),
	                        str(
	                            authorized
	                        ),
	                        str(
	                            qualityStatus
	                        ),
	                        mesRecipeId,
	                        mesWorkOrderId
	                    )
	                )
	
	
	            ###################################################################
	            # Processing Failure
	            ###################################################################
	
	            except Exception as processingError:
	
	                logger.error(
	                    "S2M MaterialInfo processing failed. "
	                    "Equipment=%s, "
	                    "Error=%s"
	                    % (
	                        equipment,
	                        str(
	                            processingError
	                        )
	                    )
	                )
	
	
	                ###############################################################
	                # Empty PLC Response
	                ###############################################################
	
	                plcResponseObject = createEmptyPLCResponse()
	
	
	                plcStatusCode = 410
	
	                responseHandshake = 2
	
	
	                ###############################################################
	                # Java Date
	                ###############################################################
	
	                failureResponseTime = system.date.now()
	
	
	                ###############################################################
	                # Write Full Failure Response
	                ###############################################################
	
	                try:
	
	                    writePLCResponse(
	                        responseDataPath,
	                        statusCodePath,
	                        responseTimePath,
	                        responseAckNumberPath,
	                        handshakePath,
	                        plcResponseObject,
	                        plcStatusCode,
	                        failureResponseTime,
	                        "",
	                        responseHandshake
	                    )
	
	
	                except Exception as failureWriteError:
	
	                    logger.error(
	                        "Failed to write complete PLC failure response. "
	                        "Equipment=%s, "
	                        "Error=%s"
	                        % (
	                            equipment,
	                            str(
	                                failureWriteError
	                            )
	                        )
	                    )
	
	
	                    ###########################################################
	                    # Failure Metadata Fallback
	                    ###########################################################
	
	                    try:
	
	                        writePLCFailureMetadata(
	                            statusCodePath,
	                            responseTimePath,
	                            responseAckNumberPath,
	                            handshakePath,
	                            410,
	                            failureResponseTime,
	                            2
	                        )
	
	
	                    except Exception as metadataWriteError:
	
	                        logger.error(
	                            "Failed to write PLC failure metadata. "
	                            "Equipment=%s, "
	                            "Error=%s"
	                            % (
	                                equipment,
	                                str(
	                                    metadataWriteError
	                                )
	                            )
	                        )
	
	
	        #######################################################################
	        # Handshake 3
	        #######################################################################
	
	        elif handshakeValue == 3:
	
	            logger.warn(
	                "Handshake 3 received. "
	                "Equipment=%s. "
	                "MES call skipped."
	                % equipment
	            )
	
	
	            plcResponseObject = createEmptyPLCResponse()
	
	
	            ###################################################################
	            # Java Date
	            ###################################################################
	
	            responseTime = system.date.now()
	
	
	            try:
	
	                writePLCResponse(
	                    responseDataPath,
	                    statusCodePath,
	                    responseTimePath,
	                    responseAckNumberPath,
	                    handshakePath,
	                    plcResponseObject,
	                    510,
	                    responseTime,
	                    "",
	                    3
	                )
	
	
	            except Exception as cancelledWriteError:
	
	                logger.error(
	                    "Failed to write Handshake 3 PLC response. "
	                    "Equipment=%s, "
	                    "Error=%s"
	                    % (
	                        equipment,
	                        str(
	                            cancelledWriteError
	                        )
	                    )
	                )
	
	
	                try:
	
	                    writePLCFailureMetadata(
	                        statusCodePath,
	                        responseTimePath,
	                        responseAckNumberPath,
	                        handshakePath,
	                        510,
	                        responseTime,
	                        3
	                    )
	
	
	                except Exception as cancelledMetadataError:
	
	                    logger.error(
	                        "Failed to write Handshake 3 metadata. "
	                        "Equipment=%s, "
	                        "Error=%s"
	                        % (
	                            equipment,
	                            str(
	                                cancelledMetadataError
	                            )
	                        )
	                    )
	
	
	        #######################################################################
	        # Unsupported Handshake
	        #######################################################################
	
	        else:
	
	            logger.warn(
	                "Unsupported Handshake received. "
	                "Equipment=%s, "
	                "Handshake=%s"
	                % (
	                    equipment,
	                    str(
	                        handshakeValue
	                    )
	                )
	            )
	
	
	            plcResponseObject = createEmptyPLCResponse()
	
	
	            ###################################################################
	            # Java Date
	            ###################################################################
	
	            responseTime = system.date.now()
	
	
	            try:
	
	                writePLCResponse(
	                    responseDataPath,
	                    statusCodePath,
	                    responseTimePath,
	                    responseAckNumberPath,
	                    handshakePath,
	                    plcResponseObject,
	                    510,
	                    responseTime,
	                    "",
	                    handshakeValue
	                )
	
	
	            except Exception as unsupportedWriteError:
	
	                logger.error(
	                    "Failed to write unsupported Handshake response. "
	                    "Equipment=%s, "
	                    "Handshake=%s, "
	                    "Error=%s"
	                    % (
	                        equipment,
	                        str(
	                            handshakeValue
	                        ),
	                        str(
	                            unsupportedWriteError
	                        )
	                    )
	                )
	
	
	                try:
	
	                    writePLCFailureMetadata(
	                        statusCodePath,
	                        responseTimePath,
	                        responseAckNumberPath,
	                        handshakePath,
	                        510,
	                        responseTime,
	                        handshakeValue
	                    )
	
	
	                except Exception as unsupportedMetadataError:
	
	                    logger.error(
	                        "Failed to write unsupported Handshake metadata. "
	                        "Equipment=%s, "
	                        "Error=%s"
	                        % (
	                            equipment,
	                            str(
	                                unsupportedMetadataError
	                            )
	                        )
	                    )
	
	
	###############################################################################
	# OUTER SCRIPT EXCEPTION
	###############################################################################
	
	except Exception as scriptError:
	
	    ###########################################################################
	    # Try to capture triggering tag path safely.
	    #
	    # Do NOT directly reference tagPath here.
	    ###########################################################################
	
	    try:
	
	        errorTriggerTagPath = safeUnicode(
	            event.getTagPath()
	        ).strip()
	
	
	    except Exception:
	
	        errorTriggerTagPath = "UNKNOWN"
	
	
	    logger.error(
	        "S2M MaterialInfo Gateway Tag Change script failed. "
	        "TriggerTagPath=%s, "
	        "Error=%s"
	        % (
	            errorTriggerTagPath,
	            str(
	                scriptError
	            )
	        )
	    )