def onTagChange(initialChange, newValue, previousValue, event, executionCount):
	###############################################################################
	# Project        : AGRATAS SCADA - MES Integration
	# Interface      : S2M.MaterialInfo
	# Module         : Ignition Gateway Tag Change Script
	# MES Operation  : AGR_PRD_S2M_MaterialInfo
	#
	# Description:
	#   1. Monitors the AGSetItemInfo Handshake tag.
	#   2. Processes the request when Handshake changes to 1.
	#   3. Reads RequestData and RequestAckNumber from the Siemens PLC.
	#   4. Maps PLC request fields into the MES MaterialInfo request.
	#   5. Sends MessageHeader and MaterialInfo directly under Inputs.
	#   6. Receives and decodes Outputs.ResponseJSON from MES.
	#   7. Maps MES MaterialInfo values into the PLC AGItemResponse structure.
	#   8. Maps MES Authorization dynamically to PLC Authorized Boolean.
	#   9. Maps MES QualityStatus:
	#          Pass -> True
	#          Fail -> False
	#          Missing/Null/Unknown -> False
	#  10. Maps MES RecipeID to PLC RecipeId for StatusCode 200.
	#  11. Maps MES WorkOrder to PLC WorkOrderID for StatusCode 200.
	#  12. Uses empty RecipeId and WorkOrderID for every non-200 response.
	#  13. Copies PLC RequestAckNumber to ResponseAckNumber when StatusCode is 200.
	#  14. Writes ResponseData, StatusCode, ResponseTimestamp and
	#      ResponseAckNumber first.
	#  15. Writes Handshake last, only after all response writes succeed.
	#
	# Handshake:
	#   1 = New request from PLC
	#   2 = SCADA processing completed
	#   3 = Invalid or cancelled request
	#
	# PLC RequestData:
	# {
	#     "ItemID": "HUCO-006",
	#     "RecipeId": "PO_Mixing_100.07",
	#     "WorkOrderID": "AGR_Mixing_0406_01"
	# }
	#
	# MES Request:
	# {
	#     "Inputs": {
	#         "MessageHeader": {
	#             "InterfaceName": "S2M.MaterialInfo",
	#             "TransactionId": "MAT-20260722113821537",
	#             "SourceSystem": "SCADA",
	#             "TargetSystem": "MES",
	#             "EventTimestamp": "2026-07-22T11:38:21.537Z",
	#             "Equipment": "EQ_Mixing",
	#             "EmployeeNo": "657681"
	#         },
	#         "MaterialInfo": {
	#             "HuContainer": "HUCO-006",
	#             "FeedingLocation": "EQ_Mixing",
	#             "WorkOrder": "AGR_Mixing_0406_01",
	#             "RecipeID": "PO_Mixing_100.07"
	#         }
	#     }
	# }
	#
	# MES to PLC Response Mapping:
	# -----------------------------------------------------------------------------
	# MES Field        | PLC Field       | PLC Datatype
	# -----------------------------------------------------------------------------
	# HuContainer      | ItemID          | WString
	# BatchID          | BatchID         | WString
	# ExpiryDate       | ExpiryDate      | WString
	# QualityStatus    | QualityStatus   | Bool
	# Authorization    | Authorized      | Bool
	# RecipeID         | RecipeId        | WString
	# WorkOrder        | WorkOrderID     | WString
	#
	# Positive PLC ResponseData / AGItemResponse:
	# {
	#     "ItemID": "HUCO-006",
	#     "BatchID": "BATCH-001",
	#     "ExpiryDate": "2027-01-01T00:00:00Z",
	#     "QualityStatus": true,
	#     "Authorized": true,
	#     "RecipeId": "PO_Mixing_100.07",
	#     "WorkOrderID": "AGR_Mixing_0406_01"
	# }
	#
	# Technical Failure / Non-200 PLC ResponseData:
	# {
	#     "ItemID": "",
	#     "BatchID": "",
	#     "ExpiryDate": "",
	#     "QualityStatus": false,
	#     "Authorized": false,
	#     "RecipeId": "",
	#     "WorkOrderID": ""
	# }
	#
	# Version History
	# -----------------------------------------------------------------------------
	# Version | Date       | Author | Description
	# -----------------------------------------------------------------------------
	# 1.0     | 22-Jul-2026| Hari   | Initial MaterialInfo implementation
	# 1.1     | 22-Jul-2026| Hari   | Added dynamic MES request and response mapping
	# 1.2     | 22-Jul-2026| Hari   | Corrected MES Inputs request structure
	# 1.3     | 22-Jul-2026| Hari   | Removed OPC UA method call and changed
	#         |            |        | ResponseData to normal PLC tag write
	# 1.4     | 22-Jul-2026| Hari   | Added RequestAckNumber read and copied it to
	#         |            |        | ResponseAckNumber for successful responses
	# 1.5     | 22-Jul-2026| Hari   | Mapped MES Authorization and QualityStatus
	#         |            |        | dynamically into the PLC response
	# 1.6     | 23-Jul-2026| Hari   | Changed PLC QualityStatus datatype to Boolean.
	#         |            |        | MES Pass maps to True. Fail, null, missing or
	#         |            |        | unknown values map to False.
	# 1.7     | 24-Jul-2026| Hari   | Added MES RecipeID to PLC RecipeId mapping and
	#         |            |        | MES WorkOrder to PLC WorkOrderID mapping.
	# 1.8     | 24-Jul-2026| Hari   | Ensured all non-200 responses use empty string
	#         |            |        | fields and False Boolean fields.
	# 1.9     | 24-Jul-2026| Hari   | Changed PLC completion Handshake write to occur
	#         |            |        | only after response data and metadata succeed.
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
	    "FAT_S2M_MATERIAL_INFO"
	)
	
	
	###############################################################################
	# Helper: Safely convert a value to Unicode
	###############################################################################
	
	def safeUnicode(value, defaultValue=""):
	    """
	    Safely converts a value to Unicode.
	
	    Null or unconvertible values return the supplied default value.
	    """
	
	    if value is None:
	        return unicode(defaultValue)
	
	    try:
	        return unicode(value)
	
	    except Exception:
	        return unicode(defaultValue)
	
	
	###############################################################################
	# Helper: Convert generic MES value to Boolean
	###############################################################################
	
	def convertToBoolean(value):
	    """
	    Converts MES Boolean, numeric or string values into a Python Boolean.
	
	    Positive values:
	        true, 1, yes, y, pass, passed, good, ok, success, authorized
	
	    Missing, null and all unrecognized values return False.
	    """
	
	    if value is None:
	        return False
	
	    if isinstance(value, basestring):
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
	
	    return bool(value)
	
	
	###############################################################################
	# Helper: Convert MES QualityStatus to PLC Boolean
	###############################################################################
	
	def convertQualityStatusToBoolean(value):
	    """
	    Converts MES QualityStatus into the PLC Boolean value.
	
	    Mapping:
	        MES "Pass" -> True
	        MES "Fail" -> False
	
	    Default:
	        None, empty, missing and unknown values -> False
	    """
	
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
	# Helper: Create empty PLC response
	###############################################################################
	
	def createEmptyPLCResponse():
	    """
	    Returns the safe default AGItemResponse structure.
	
	    This response is used for every non-200 scenario:
	        - MES communication failure
	        - MES invalid response
	        - PLC request validation failure
	        - Handshake 3
	        - Unsupported handshake
	        - Internal SCADA exception
	
	    All WString fields are empty.
	    All Boolean fields are False.
	    """
	
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
	# Helper: Validate PLC tag write results
	###############################################################################
	
	def validateWriteResults(
	    writePaths,
	    writeValues,
	    writeResults
	):
	    """
	    Validates and logs all PLC tag write results.
	
	    Raises an exception when one or more writes return bad quality.
	    """
	
	    failedWrites = []
	
	    for index in range(
	        len(writeResults)
	    ):
	        qualityCode = writeResults[index]
	
	        if qualityCode.isGood():
	            logger.info(
	                "PLC tag write successful. "
	                "Path=%s, Value=%s, Quality=%s"
	                % (
	                    writePaths[index],
	                    str(writeValues[index]),
	                    str(qualityCode)
	                )
	            )
	
	        else:
	            failedWrites.append(
	                "%s=%s"
	                % (
	                    writePaths[index],
	                    str(qualityCode)
	                )
	            )
	
	            logger.error(
	                "PLC tag write failed. "
	                "Path=%s, Value=%s, Quality=%s"
	                % (
	                    writePaths[index],
	                    str(writeValues[index]),
	                    str(qualityCode)
	                )
	            )
	
	    if len(failedWrites) > 0:
	        raise Exception(
	            "One or more PLC tag writes failed: %s"
	            % ", ".join(failedWrites)
	        )
	
	
	###############################################################################
	# Helper: Write values to PLC
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
	    """
	    Writes the response to the Siemens PLC.
	
	    ResponseData is an Ignition Document tag mapped to the Siemens
	    AGItemResponse structured datatype.
	
	    Processing:
	        1. Build exact seven-field AGItemResponse document.
	        2. Write ResponseData, StatusCode, ResponseTimestamp and
	           ResponseAckNumber.
	        3. Validate all write qualities.
	        4. Write Handshake last.
	
	    ResponseAckNumber:
	        StatusCode 200     -> copy PLC RequestAckNumber
	        Any other status  -> empty string
	
	    Non-200 response:
	        The caller must supply createEmptyPLCResponse().
	    """
	
	    ###########################################################################
	    # Determine ResponseAckNumber
	    ###########################################################################
	
	    if int(statusCode) == 200:
	        finalResponseAckNumber = responseAckNumber
	    else:
	        finalResponseAckNumber = ""
	
	    if finalResponseAckNumber is None:
	        finalResponseAckNumber = ""
	
	    finalResponseAckNumber = safeUnicode(
	        finalResponseAckNumber
	    ).strip()
	
	    ###########################################################################
	    # Create exact Siemens AGItemResponse document structure
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
	    # Convert dictionary to an Ignition-compatible Document object
	    ###########################################################################
	
	    responseDataJson = system.util.jsonEncode(
	        plcResponseDocument
	    )
	
	    responseDataDocument = system.util.jsonDecode(
	        responseDataJson
	    )
	
	    logger.info(
	        "Writing PLC response data and metadata. "
	        "ResponseData=%s, StatusCode=%s, ResponseTime=%s, "
	        "ResponseAckNumber=%s"
	        % (
	            responseDataJson,
	            str(statusCode),
	            safeUnicode(responseTime),
	            finalResponseAckNumber
	        )
	    )
	
	    ###########################################################################
	    # Step 1: Write response data and metadata
	    #
	    # Handshake is deliberately excluded and written only after these succeed.
	    ###########################################################################
	
	    writePaths = [
	        responseDataPath,
	        statusCodePath,
	        responseTimePath,
	        responseAckNumberPath
	    ]
	
	    writeValues = [
	        responseDataDocument,
	        int(statusCode),
	        safeUnicode(responseTime),
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
	    # Step 2: Write completion Handshake last
	    ###########################################################################
	
	    logger.info(
	        "Writing PLC Handshake last. "
	        "Path=%s, Value=%s"
	        % (
	            handshakePath,
	            str(handshake)
	        )
	    )
	
	    handshakeResult = system.tag.writeBlocking(
	        [handshakePath],
	        [int(handshake)]
	    )[0]
	
	    if not handshakeResult.isGood():
	        raise Exception(
	            "PLC Handshake write failed. "
	            "Path=%s, Value=%s, Quality=%s"
	            % (
	                handshakePath,
	                str(handshake),
	                str(handshakeResult)
	            )
	        )
	
	    logger.info(
	        "PLC Handshake write successful. "
	        "Path=%s, Value=%s, Quality=%s"
	        % (
	            handshakePath,
	            str(handshake),
	            str(handshakeResult)
	        )
	    )
	
	    return {
	        "writeResults": writeResults,
	        "handshakeResult": handshakeResult
	    }
	
	
	###############################################################################
	# Helper: Write technical failure metadata
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
	    """
	    Writes failure metadata when the complete PLC response document cannot be
	    written.
	
	    This provides a final fallback:
	        StatusCode        = supplied failure status
	        ResponseTimestamp = supplied failure timestamp
	        ResponseAckNumber = empty
	        Handshake         = written last
	    """
	
	    metadataPaths = [
	        statusCodePath,
	        responseTimePath,
	        responseAckNumberPath
	    ]
	
	    metadataValues = [
	        int(statusCode),
	        safeUnicode(responseTime),
	        ""
	    ]
	
	    logger.info(
	        "Writing PLC failure metadata. "
	        "StatusCode=%s, ResponseTime=%s, ResponseAckNumber=<empty>"
	        % (
	            str(statusCode),
	            safeUnicode(responseTime)
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
	
	    handshakeResult = system.tag.writeBlocking(
	        [handshakePath],
	        [int(handshake)]
	    )[0]
	
	    if not handshakeResult.isGood():
	        raise Exception(
	            "PLC failure Handshake write failed. "
	            "Path=%s, Value=%s, Quality=%s"
	            % (
	                handshakePath,
	                str(handshake),
	                str(handshakeResult)
	            )
	        )
	
	    logger.info(
	        "PLC failure Handshake write successful. "
	        "Path=%s, Value=%s, Quality=%s"
	        % (
	            handshakePath,
	            str(handshake),
	            str(handshakeResult)
	        )
	    )
	
	
	###############################################################################
	# Main Tag Change Script
	###############################################################################
	
	try:
	    logger.info(
	        "S2M MaterialInfo tag change script started"
	    )
	
	    ###########################################################################
	    # Step 1: Ignore initial tag subscription event
	    ###########################################################################
	
	    if initialChange:
	        logger.info(
	            "Initial tag change ignored"
	        )
	
	    else:
	        #######################################################################
	        # Step 2: Read current Handshake
	        #######################################################################
	
	        handshakeValue = int(
	            newValue.value
	        )
	
	        logger.info(
	            "Handshake value received: %s"
	            % str(handshakeValue)
	        )
	
	        #######################################################################
	        # Step 3: Define MES configuration
	        #######################################################################
	
	        mesUrl = "https://aprisomesdev.agratas.com/apriso/httpServices/operations/AGR_PRD_S2M_MaterialInfo"
	
	        interfaceName = "S2M.MaterialInfo"
	        sourceSystem = "SCADA"
	        targetSystem = "MES"
	
	        equipment = "IN11.E305.PCE.POW22"
	        feedingLocation = "IN11.E305.PCE.POW22"
	        employeeNo = "ADMIN"
	
	        #######################################################################
	        # Step 4: Define PLC tag paths
	        #######################################################################
	
	        requestDataPath = (
	            "[default]IN11_E305_PCE_POW22_Data/"
	            "IN11_E305_PCE_POW22_IN11_E305_PCE_CMS21_"
	            "AGCalls_AGSetItemInfo_RequestData"
	        )
	
	        requestAckNumberPath = (
	            "[default]IN11_E305_PCE_POW22_Data/"
	            "IN11_E305_PCE_POW22_IN11_E305_PCE_CMS21_"
	            "AGCalls_AGSetItemInfo_RequestAckNumber"
	        )
	
	        responseDataPath = (
	            "[default]IN11_E305_PCE_POW22_Data/"
	            "IN11_E305_PCE_POW22_IN11_E305_PCE_CMS21_"
	            "AGCalls_AGSetItemInfo_ResponseData"
	        )
	
	        statusCodePath = (
	            "[default]IN11_E305_PCE_POW22_Data/"
	            "IN11_E305_PCE_POW22_IN11_E305_PCE_CMS21_"
	            "AGCalls_AGSetItemInfo_StatusCode"
	        )
	
	        responseTimePath = (
	            "[default]IN11_E305_PCE_POW22_Data/"
	            "IN11_E305_PCE_POW22_IN11_E305_PCE_CMS21_"
	            "AGCalls_AGSetItemInfo_ResponseTimestamp"
	        )
	
	        responseAckNumberPath = (
	            "[default]IN11_E305_PCE_POW22_Data/"
	            "IN11_E305_PCE_POW22_IN11_E305_PCE_CMS21_"
	            "AGCalls_AGSetItemInfo_ResponseAckNumber"
	        )
	
	        handshakePath = (
	            "[default]IN11_E305_PCE_POW22_Data/"
	            "IN11_E305_PCE_POW22_IN11_E305_PCE_CMS21_"
	            "AGCalls_AGSetItemInfo_Handshake"
	        )
	
	        #######################################################################
	        # Initialize RequestAckNumber
	        #######################################################################
	
	        requestAckNumber = ""
	
	        #######################################################################
	        # Step 5: Handshake = 2 means already processed
	        #######################################################################
	
	        if handshakeValue in (0, 2):
	            logger.info(
	                "Handshake is 2. Request already processed. "
	                "No MES call or PLC write will be performed."
	            )
	
	        #######################################################################
	        # Step 6: Handshake = 1 means process the request
	        #######################################################################
	
	        elif handshakeValue == 1:
	            logger.info(
	                "Valid request Handshake received"
	            )
	
	            responseTime = system.date.format(
	                system.date.now(),
	                "yyyy-MM-dd'T'HH:mm:ss.SSS"
	            )
	
	            try:
	                ################################################################
	                # Read PLC RequestData and RequestAckNumber together
	                ################################################################
	
	                logger.info(
	                    "Reading PLC request tags. "
	                    "RequestDataPath=%s, RequestAckNumberPath=%s"
	                    % (
	                        requestDataPath,
	                        requestAckNumberPath
	                    )
	                )
	
	                requestTagResults = system.tag.readBlocking([
	                    requestDataPath,
	                    requestAckNumberPath
	                ])
	
	                requestTagResult = requestTagResults[0]
	                requestAckNumberResult = requestTagResults[1]
	
	                logger.info(
	                    "PLC request tags read completed. "
	                    "RequestDataQuality=%s, RequestAckNumberQuality=%s"
	                    % (
	                        str(requestTagResult.quality),
	                        str(requestAckNumberResult.quality)
	                    )
	                )
	
	                ################################################################
	                # Validate RequestData tag quality
	                ################################################################
	
	                if not requestTagResult.quality.isGood():
	                    raise Exception(
	                        "PLC RequestData tag quality is bad. "
	                        "Path=%s, Quality=%s"
	                        % (
	                            requestDataPath,
	                            str(requestTagResult.quality)
	                        )
	                    )
	
	                ################################################################
	                # Validate RequestAckNumber tag quality
	                ################################################################
	
	                if not requestAckNumberResult.quality.isGood():
	                    raise Exception(
	                        "PLC RequestAckNumber tag quality is bad. "
	                        "Path=%s, Quality=%s"
	                        % (
	                            requestAckNumberPath,
	                            str(requestAckNumberResult.quality)
	                        )
	                    )
	
	                ################################################################
	                # Validate RequestData value
	                ################################################################
	
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
	                        "PLC RequestData tag contains an empty value. "
	                        "Path=%s"
	                        % requestDataPath
	                    )
	
	                ################################################################
	                # Read and validate RequestAckNumber
	                ################################################################
	
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
	                        "PLC RequestAckNumber tag contains an empty value. "
	                        "Path=%s"
	                        % requestAckNumberPath
	                    )
	
	                logger.info(
	                    "PLC RequestData received: %s"
	                    % plcRequestString
	                )
	
	                logger.info(
	                    "PLC RequestAckNumber received: %s"
	                    % requestAckNumber
	                )
	
	                ################################################################
	                # Decode PLC RequestData JSON
	                ################################################################
	
	                try:
	                    plcRequestObject = system.util.jsonDecode(
	                        plcRequestString
	                    )
	
	                except Exception as decodeError:
	                    raise Exception(
	                        "Invalid PLC RequestData JSON. "
	                        "Error=%s, Value=%s"
	                        % (
	                            str(decodeError),
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
	
	                ################################################################
	                # Extract PLC request fields
	                ################################################################
	
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
	
	                ################################################################
	                # Validate mandatory request fields
	                ################################################################
	
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
	
	                ################################################################
	                # Generate UTC EventTimestamp
	                ################################################################
	
	                utcFormatter = SimpleDateFormat(
	                    "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"
	                )
	
	                utcFormatter.setTimeZone(
	                    TimeZone.getTimeZone("UTC")
	                )
	
	                eventTimestamp = utcFormatter.format(
	                    Date()
	                )
	
	                ################################################################
	                # Generate unique TransactionId
	                ################################################################
	
	                transactionFormatter = SimpleDateFormat(
	                    "yyyyMMddHHmmssSSS"
	                )
	
	                transactionFormatter.setTimeZone(
	                    TimeZone.getTimeZone("UTC")
	                )
	
	                transactionId = (
	                    "MAT-"
	                    + transactionFormatter.format(
	                        Date()
	                    )
	                )
	
	                ################################################################
	                # Build MES request
	                ################################################################
	
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
	                            "HuContainer": itemId,
	                            "FeedingLocation": feedingLocation,
	                            "WorkOrder": workOrderId,
	                            "RecipeID": recipeId
	                        }
	                    }
	                }
	
	                logger.info(
	                    "Calling MES with payload: %s"
	                    % system.util.jsonEncode(
	                        payload
	                    )
	                )
	
	                ################################################################
	                # Call MES
	                ################################################################
	
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
	                    "MES raw response: %s"
	                    % str(mesResponse)
	                )
	
	                ################################################################
	                # Decode MES outer response
	                ################################################################
	
	                if isinstance(
	                    mesResponse,
	                    basestring
	                ):
	                    try:
	                        mesOuterResponse = system.util.jsonDecode(
	                            safeUnicode(mesResponse)
	                        )
	
	                    except Exception as outerDecodeError:
	                        raise Exception(
	                            "MES outer response is invalid JSON. "
	                            "Error=%s, Response=%s"
	                            % (
	                                str(outerDecodeError),
	                                str(mesResponse)
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
	                        % str(type(mesResponse))
	                    )
	
	                ################################################################
	                # Validate MES Outputs
	                ################################################################
	
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
	
	                ################################################################
	                # Decode MES inner ResponseJSON
	                ################################################################
	
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
	                        "MES ResponseJSON received: %s"
	                        % responseJsonString
	                    )
	
	                    normalizedResponseJson = (
	                        responseJsonString
	                        .replace(":False", ":false")
	                        .replace(":True", ":true")
	                        .replace(": False", ": false")
	                        .replace(": True", ": true")
	                    )
	
	                    try:
	                        mesInnerResponse = system.util.jsonDecode(
	                            normalizedResponseJson
	                        )
	
	                    except Exception as innerDecodeError:
	                        raise Exception(
	                            "MES ResponseJSON is invalid JSON. "
	                            "Error=%s, ResponseJSON=%s"
	                            % (
	                                str(innerDecodeError),
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
	
	                ################################################################
	                # Validate MES MaterialInfo
	                ################################################################
	
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
	
	                ################################################################
	                # Read MES Authorization
	                ################################################################
	
	                authorizationValue = mesMaterialInfo.get(
	                    "Authorization",
	                    False
	                )
	
	                authorized = convertToBoolean(
	                    authorizationValue
	                )
	
	                ################################################################
	                # Read and map MES QualityStatus
	                ################################################################
	
	                qualityStatusValue = mesMaterialInfo.get(
	                    "QualityStatus",
	                    None
	                )
	
	                qualityStatus = convertQualityStatusToBoolean(
	                    qualityStatusValue
	                )
	
	                ################################################################
	                # Read MES RecipeID and WorkOrder
	                #
	                # MES RecipeID  -> PLC RecipeId
	                # MES WorkOrder -> PLC WorkOrderID
	                ################################################################
	
	                mesRecipeId = safeUnicode(
	                    mesMaterialInfo.get(
	                        "RecipeID",
	                        ""
	                    )
	                ).strip()
	
	                mesWorkOrderId = safeUnicode(
	                    mesMaterialInfo.get(
	                        "WorkOrder",
	                        ""
	                    )
	                ).strip()
	
	                logger.info(
	                    "MES business values mapped. "
	                    "AuthorizationRaw=%s, AuthorizedPLC=%s, "
	                    "QualityStatusRaw=%s, QualityStatusPLC=%s, "
	                    "RecipeID=%s, WorkOrder=%s"
	                    % (
	                        str(authorizationValue),
	                        str(authorized),
	                        str(qualityStatusValue),
	                        str(qualityStatus),
	                        mesRecipeId,
	                        mesWorkOrderId
	                    )
	                )
	
	                ################################################################
	                # Build Siemens AGItemResponse for StatusCode 200
	                ################################################################
	
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
	                    "Mapped PLC AGItemResponse: %s"
	                    % system.util.jsonEncode(
	                        plcResponseObject
	                    )
	                )
	
	                ################################################################
	                # MES response processed successfully
	                ################################################################
	
	                plcStatusCode = 200
	                responseHandshake = 2
	
	                ################################################################
	                # Write successful response to PLC
	                ################################################################
	
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
	                    "TransactionId=%s, RequestAckNumber=%s, "
	                    "ResponseAckNumber=%s, StatusCode=%s, Handshake=%s, "
	                    "Authorized=%s, QualityStatus=%s, RecipeId=%s, "
	                    "WorkOrderID=%s"
	                    % (
	                        transactionId,
	                        requestAckNumber,
	                        requestAckNumber,
	                        str(plcStatusCode),
	                        str(responseHandshake),
	                        str(authorized),
	                        str(qualityStatus),
	                        mesRecipeId,
	                        mesWorkOrderId
	                    )
	                )
	
	            except Exception as processingError:
	                logger.error(
	                    "S2M MaterialInfo processing failed: %s"
	                    % str(processingError)
	                )
	
	                ################################################################
	                # Build empty PLC response for all technical failures
	                ################################################################
	
	                plcResponseObject = createEmptyPLCResponse()
	
	                plcStatusCode = 410
	                responseHandshake = 2
	
	                failureResponseTime = system.date.format(
	                    system.date.now(),
	                    "yyyy-MM-dd'T'HH:mm:ss.SSS"
	                )
	
	                ################################################################
	                # Write technical failure response
	                ################################################################
	
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
	                        "Failed to write complete PLC failure response: %s"
	                        % str(failureWriteError)
	                    )
	
	                    ################################################################
	                    # Final fallback when ResponseData cannot be written
	                    ################################################################
	
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
	                            "Failed to write PLC failure metadata: %s"
	                            % str(metadataWriteError)
	                        )
	
	        #######################################################################
	        # Step 7: Handshake = 3 means invalid or cancelled request
	        #######################################################################
	
	        elif handshakeValue == 3:
	            logger.warn(
	                "Handshake 3 received. MES call skipped."
	            )
	
	            plcResponseObject = createEmptyPLCResponse()
	
	            responseTime = system.date.format(
	                system.date.now(),
	                "yyyy-MM-dd'T'HH:mm:ss.SSS"
	            )
	
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
	                    "Failed to write cancelled PLC response: %s"
	                    % str(cancelledWriteError)
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
	                        "Failed to write cancelled PLC metadata: %s"
	                        % str(cancelledMetadataError)
	                    )
	
	        #######################################################################
	        # Step 8: Unsupported Handshake
	        #######################################################################
	
	        else:
	            logger.warn(
	                "Unsupported Handshake value received: %s"
	                % str(handshakeValue)
	            )
	
	            plcResponseObject = createEmptyPLCResponse()
	
	            responseTime = system.date.format(
	                system.date.now(),
	                "yyyy-MM-dd'T'HH:mm:ss.SSS"
	            )
	
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
	                    "Failed to write unsupported Handshake response: %s"
	                    % str(unsupportedWriteError)
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
	                        "Failed to write unsupported Handshake metadata: %s"
	                        % str(unsupportedMetadataError)
	                    )
	
	
	except Exception as scriptError:
	    logger.error(
	        "S2M MaterialInfo tag change script failed: %s"
	        % str(scriptError)
	    )