def onTagChange(initialChange, newValue, previousValue, event, executionCount):
	###############################################################################
	# Project        : AGRATAS SCADA - MES Integration
	# Interface      : S2M.OperationResult
	# Module         : Ignition Gateway Tag Change Script
	# MES Operation  : AGR_PRD_S2M_Operational_results
	#
	# Description:
	#   1. Monitors the AGSetOperationResult Handshake tag.
	#   2. Ignores the initial Ignition tag subscription event.
	#   3. Processes the PLC request when Handshake changes to 1.
	#   4. Reads RequestData and RequestAckNumber from the PLC.
	#   5. Validates PLC tag quality, JSON structure and mandatory fields.
	#   6. Maps PLC RequestData to the MES Operational Results request.
	#   7. Maps PLC SourceFBS to MES SourceEquipmentID.
	#   8. Maps PLC DestinationFBS to MES DestinationEquipmentID.
	#   9. Converts PLC ItemDetails.StepID to MES string StepID.
	#  10. Sends the mapped request to the MES REST endpoint.
	#  11. Treats HTTP status code 200 as successful processing.
	#  12. Does not parse or write MES response data back to the PLC.
	#  13. Writes StatusCode, ResponseTimestamp and ResponseAckNumber to PLC.
	#  14. Copies RequestAckNumber to ResponseAckNumber only for HTTP 200.
	#  15. Uses an empty ResponseAckNumber for every non-200 result.
	#  16. Writes Handshake last after all metadata writes are successful.
	#
	# Interface Flow:
	#   PLC / Equipment -> Ignition SCADA -> MES
	#   E2S AG Calls followed by S2M REST API
	#
	# Handshake:
	#   1 = New request from PLC
	#   2 = SCADA processing completed
	#   3 = Invalid or cancelled request
	#
	# PLC RequestData:
	# {
	#     "RecipeID": "",
	#     "WorkOrderID": "",
	#     "SourceFBS": "",
	#     "DestinationFBS": "",
	#     "ItemDetails": [
	#         {
	#             "StepID": 0,
	#             "ItemID": "",
	#             "StartTime": "",
	#             "EndTime": "",
	#             "QuantityTransferred": 0.0,
	#             "UOM": ""
	#         }
	#     ]
	# }
	#
	# PLC to MES Mapping:
	# -----------------------------------------------------------------------------
	# PLC Field                          MES Field
	# -----------------------------------------------------------------------------
	# RecipeID                           OperationResult.RecipeId
	# WorkOrderID                        OperationResult.WorkOrderId
	# SourceFBS                          OperationResult.SourceEquipmentID
	# DestinationFBS                     OperationResult.DestinationEquipmentID
	# ItemDetails[].StepID               ItemDetails[].StepID as string
	# ItemDetails[].ItemID               ItemDetails[].ItemId
	# ItemDetails[].StartTime            ItemDetails[].StartTime
	# ItemDetails[].EndTime              ItemDetails[].EndTime
	# ItemDetails[].QuantityTransferred  ItemDetails[].QuantityTransferred
	# ItemDetails[].UOM                  ItemDetails[].UoM
	#
	# MES Request:
	# {
	#     "Inputs": {
	#         "MessageHeader": {
	#             "InterfaceName": "S2M.OperationResult",
	#             "TrasanactionId": "OPR-20260724123000123",
	#             "SourceSystem": "SCADA",
	#             "TargetSystem": "MES",
	#             "EventTimestamp": "2026-07-24T12:30:00.123Z"
	#         },
	#         "OperationResult": {
	#             "WorkOrderId": "IIT_2612_17",
	#             "RecipeId": "PO_Mixing_101.01",
	#             "SourceEquipmentID": "IN11.E305.PCE.POW22",
	#             "DestinationEquipmentID": "IN NA CA IQC-0006",
	#             "ItemDetails": [
	#                 {
	#                     "StepID": "1",
	#                     "ItemId": "MIX00001",
	#                     "StartTime": "2026-07-16T16:00:00Z",
	#                     "EndTime": "2026-07-16T16:12:30Z",
	#                     "QuantityTransferred": 2,
	#                     "UoM": "EA"
	#                 }
	#             ]
	#         }
	#     }
	# }
	#
	# PLC Success Response:
	#   StatusCode        = 200
	#   ResponseTimestamp = SCADA completion timestamp
	#   ResponseAckNumber = RequestAckNumber
	#   Handshake         = 2
	#
	# PLC MES Failure Response:
	#   StatusCode        = MES HTTP status code
	#   ResponseTimestamp = SCADA completion timestamp
	#   ResponseAckNumber = empty string
	#   Handshake         = 2
	#
	# PLC Technical Failure Response:
	#   StatusCode        = 500
	#   ResponseTimestamp = SCADA failure timestamp
	#   ResponseAckNumber = empty string
	#   Handshake         = 2
	#
	# Important:
	#   There is no ResponseData tag for this interface.
	#   MES response body is not required and is not mapped to the PLC.
	#
	# Version History
	# -----------------------------------------------------------------------------
	# Version | Date       | Author | Description
	# -----------------------------------------------------------------------------
	# 1.0     | 24-Jul-2026| Hari   | Initial S2M.OperationResult implementation.
	# 1.1     | 24-Jul-2026| Hari   | Updated exact PLC RequestData mapping.
	#         |            |        | SourceFBS maps to SourceEquipmentID and
	#         |            |        | DestinationFBS maps to DestinationEquipmentID.
	# 1.2     | 24-Jul-2026| Hari   | Added direct HTTP status handling. HTTP 200 is
	#         |            |        | success; MES response body is not required.
	# 1.3     | 24-Jul-2026| Hari   | Added metadata-only PLC response handling and
	#         |            |        | handshake-last write sequence.
	###############################################################################
	
	import system
	
	from java.text import SimpleDateFormat
	from java.util import Date
	from java.util import TimeZone
	
	
	###############################################################################
	# Logger
	###############################################################################
	
	logger = system.util.getLogger(
	    "FAT_S2M_OPERATION_RESULT"
	)
	
	
	###############################################################################
	# MES Configuration
	###############################################################################
	
	MES_URL = "https://aprisomesdev.agratas.com/apriso/httpServices/operations/AGR_PRD_S2M_OperationResult"
	#MES_URL = "http://WIN-GC9744IHT64/apriso/httpServices/operations/AGR_PRD_S2M_Operational_results"
	
	INTERFACE_NAME = "S2M.OperationResult"
	SOURCE_SYSTEM = "SCADA"
	TARGET_SYSTEM = "MES"
	
	
	###############################################################################
	# PLC Tag Configuration [default]IN11_E115_PCE_MIX21/AGCalls/AGSetOperationResult/Handshake
	###############################################################################
	
	TAG_BASE_PATH = (
	    "[default]IN11_E115_PCE_MIX21/"
	)
	
	TAG_PREFIX = (
	    "AGCalls/"
	    "AGSetOperationResult/"
	)
	
	HANDSHAKE_PATH = (
	    TAG_BASE_PATH
	    + TAG_PREFIX
	    + "Handshake"
	)
	
	REQUEST_ACK_NUMBER_PATH = (
	    TAG_BASE_PATH
	    + TAG_PREFIX
	    + "RequestAckNumber"
	)
	
	REQUEST_DATA_PATH = (
	    TAG_BASE_PATH
	    + TAG_PREFIX
	    + "RequestData"
	)
	
	REQUEST_TIMESTAMP_PATH = (
	    TAG_BASE_PATH
	    + TAG_PREFIX
	    + "RequestTimestamp"
	)
	
	RESPONSE_ACK_NUMBER_PATH = (
	    TAG_BASE_PATH
	    + TAG_PREFIX
	    + "ResponseAckNumber"
	)
	
	RESPONSE_TIMESTAMP_PATH = (
	    TAG_BASE_PATH
	    + TAG_PREFIX
	    + "ResponseTimestamp"
	)
	
	SENDER_FBS_PATH = (
	    TAG_BASE_PATH
	    + TAG_PREFIX
	    + "SenderFBS"
	)
	
	STATUS_CODE_PATH = (
	    TAG_BASE_PATH
	    + TAG_PREFIX
	    + "StatusCode"
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
	# Helper: Create current UTC EventTimestamp
	###############################################################################
	
	def getUtcEventTimestamp():
	    """
	    Returns the current UTC timestamp for the MES MessageHeader.
	
	    Format:
	        yyyy-MM-dd'T'HH:mm:ss.SSS'Z'
	    """
	
	    formatter = SimpleDateFormat(
	        "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"
	    )
	
	    formatter.setTimeZone(
	        TimeZone.getTimeZone("UTC")
	    )
	
	    return formatter.format(
	        Date()
	    )
	
	
	###############################################################################
	# Helper: Create PLC ResponseTimestamp
	###############################################################################
	
	def getPLCResponseTimestamp():
	    """
	    Returns the current SCADA timestamp for the PLC ResponseTimestamp tag.
	
	    Format:
	        yyyy-MM-dd'T'HH:mm:ss.SSS
	    """
	
	    return system.date.format(
	        system.date.now(),
	        "yyyy-MM-dd'T'HH:mm:ss.SSS"
	    )
	
	
	###############################################################################
	# Helper: Generate OperationResult transaction ID
	###############################################################################
	
	def generateTransactionId():
	    """
	    Generates a unique OperationResult transaction ID.
	
	    Example:
	        OPR-20260724123000123
	    """
	
	    formatter = SimpleDateFormat(
	        "yyyyMMddHHmmssSSS"
	    )
	
	    formatter.setTimeZone(
	        TimeZone.getTimeZone("UTC")
	    )
	
	    return (
	        "OPR-"
	        + formatter.format(
	            Date()
	        )
	    )
	
	
	###############################################################################
	# Helper: Decode PLC RequestData
	###############################################################################
	
	def decodePLCRequestData(requestDataValue):
	    """
	    Decodes the PLC RequestData value.
	
	    Supported values:
	        1. Ignition Document / dictionary
	        2. JSON string
	
	    Returns:
	        Python dictionary
	    """
	
	    if requestDataValue is None:
	        raise Exception(
	            "PLC RequestData contains null"
	        )
	
	    ###########################################################################
	    # RequestData is already an Ignition Document or dictionary
	    ###########################################################################
	
	    if isinstance(
	        requestDataValue,
	        dict
	    ):
	        requestObject = requestDataValue
	
	    ###########################################################################
	    # RequestData is a JSON string
	    ###########################################################################
	
	    else:
	        requestDataString = safeUnicode(
	            requestDataValue
	        ).strip()
	
	        if requestDataString == "":
	            raise Exception(
	                "PLC RequestData contains an empty value"
	            )
	
	        try:
	            requestObject = system.util.jsonDecode(
	                requestDataString
	            )
	
	        except Exception as decodeError:
	            raise Exception(
	                "PLC RequestData contains invalid JSON. "
	                "Error=%s, RequestData=%s"
	                % (
	                    str(decodeError),
	                    requestDataString
	                )
	            )
	
	    if not isinstance(
	        requestObject,
	        dict
	    ):
	        raise Exception(
	            "PLC RequestData must be a JSON object"
	        )
	
	    return requestObject
	
	
	###############################################################################
	# Helper: Validate mandatory string field
	###############################################################################
	
	def getMandatoryString(
	    sourceObject,
	    fieldName,
	    fieldPath
	):
	    """
	    Reads and validates a mandatory string field.
	    """
	
	    if fieldName not in sourceObject:
	        raise Exception(
	            "Mandatory field %s is missing"
	            % fieldPath
	        )
	
	    fieldValue = safeUnicode(
	        sourceObject.get(
	            fieldName
	        )
	    ).strip()
	
	    if fieldValue == "":
	        raise Exception(
	            "Mandatory field %s contains an empty value"
	            % fieldPath
	        )
	
	    return fieldValue
	
	
	###############################################################################
	# Helper: Validate and convert StepID
	###############################################################################
	
	def getStepId(
	    itemObject,
	    itemIndex
	):
	    """
	    Reads PLC StepID and converts it to the MES string datatype.
	
	    PLC example:
	        1
	
	    MES result:
	        "1"
	    """
	
	    fieldPath = (
	        "ItemDetails[%s].StepID"
	        % str(itemIndex)
	    )
	
	    if "StepID" not in itemObject:
	        raise Exception(
	            "Mandatory field %s is missing"
	            % fieldPath
	        )
	
	    stepIdValue = itemObject.get(
	        "StepID"
	    )
	
	    if stepIdValue is None:
	        raise Exception(
	            "Mandatory field %s contains null"
	            % fieldPath
	        )
	
	    stepId = safeUnicode(
	        stepIdValue
	    ).strip()
	
	    if stepId == "":
	        raise Exception(
	            "Mandatory field %s contains an empty value"
	            % fieldPath
	        )
	
	    return stepId
	
	
	###############################################################################
	# Helper: Validate QuantityTransferred
	###############################################################################
	
	def getQuantityTransferred(
	    itemObject,
	    itemIndex
	):
	    """
	    Reads and validates QuantityTransferred.
	
	    The numeric value is preserved in the MES request.
	    """
	
	    fieldPath = (
	        "ItemDetails[%s].QuantityTransferred"
	        % str(itemIndex)
	    )
	
	    if "QuantityTransferred" not in itemObject:
	        raise Exception(
	            "Mandatory field %s is missing"
	            % fieldPath
	        )
	
	    quantityValue = itemObject.get(
	        "QuantityTransferred"
	    )
	
	    if quantityValue is None:
	        raise Exception(
	            "Mandatory field %s contains null"
	            % fieldPath
	        )
	
	    if isinstance(
	        quantityValue,
	        bool
	    ):
	        raise Exception(
	            "%s must be numeric and cannot be Boolean"
	            % fieldPath
	        )
	
	    ###########################################################################
	    # Existing numeric value
	    ###########################################################################
	
	    if isinstance(
	        quantityValue,
	        (int, long, float)
	    ):
	        return quantityValue
	
	    ###########################################################################
	    # Numeric value supplied as a string
	    ###########################################################################
	
	    quantityString = safeUnicode(
	        quantityValue
	    ).strip()
	
	    if quantityString == "":
	        raise Exception(
	            "Mandatory field %s contains an empty value"
	            % fieldPath
	        )
	
	    try:
	        if (
	            "." in quantityString
	            or "e" in quantityString.lower()
	        ):
	            return float(
	                quantityString
	            )
	
	        return int(
	            quantityString
	        )
	
	    except Exception:
	        raise Exception(
	            "%s must be numeric. Value=%s"
	            % (
	                fieldPath,
	                quantityString
	            )
	        )
	
	
	###############################################################################
	# Helper: Map one PLC ItemDetails record
	###############################################################################
	
	def mapItemDetail(
	    plcItemDetail,
	    itemIndex
	):
	    """
	    Maps one PLC ItemDetails record into the MES ItemDetails structure.
	
	    PLC:
	        StepID
	        ItemID
	        StartTime
	        EndTime
	        QuantityTransferred
	        UOM
	
	    MES:
	        StepID
	        ItemId
	        StartTime
	        EndTime
	        QuantityTransferred
	        UoM
	    """
	
	    if not isinstance(
	        plcItemDetail,
	        dict
	    ):
	        raise Exception(
	            "ItemDetails[%s] must be a JSON object"
	            % str(itemIndex)
	        )
	
	    stepId = getStepId(
	        plcItemDetail,
	        itemIndex
	    )
	
	    itemId = getMandatoryString(
	        plcItemDetail,
	        "ItemID",
	        "ItemDetails[%s].ItemID"
	        % str(itemIndex)
	    )
	
	    startTime = getMandatoryString(
	        plcItemDetail,
	        "StartTime",
	        "ItemDetails[%s].StartTime"
	        % str(itemIndex)
	    )
	
	    endTime = getMandatoryString(
	        plcItemDetail,
	        "EndTime",
	        "ItemDetails[%s].EndTime"
	        % str(itemIndex)
	    )
	
	    quantityTransferred = getQuantityTransferred(
	        plcItemDetail,
	        itemIndex
	    )
	
	    uom = getMandatoryString(
	        plcItemDetail,
	        "UOM",
	        "ItemDetails[%s].UOM"
	        % str(itemIndex)
	    )
	
	    return {
	        "StepID": stepId,
	        "ItemId": itemId,
	        "StartTime": startTime,
	        "EndTime": endTime,
	        "QuantityTransferred": quantityTransferred,
	        "UoM": uom
	    }
	
	
	###############################################################################
	# Helper: Map PLC RequestData to MES OperationResult
	###############################################################################
	
	def mapPLCRequestToOperationResult(
	    plcRequestObject
	):
	    """
	    Maps the exact confirmed PLC RequestData structure into the MES
	    OperationResult structure.
	    """
	
	    recipeId = getMandatoryString(
	        plcRequestObject,
	        "RecipeID",
	        "RecipeID"
	    )
	
	    workOrderId = getMandatoryString(
	        plcRequestObject,
	        "WorkOrderID",
	        "WorkOrderID"
	    )
	
	    sourceFBS = getMandatoryString(
	        plcRequestObject,
	        "SourceFBS",
	        "SourceFBS"
	    )
	
	    destinationFBS = getMandatoryString(
	        plcRequestObject,
	        "DestinationFBS",
	        "DestinationFBS"
	    )
	
	    ###########################################################################
	    # Validate ItemDetails
	    ###########################################################################
	
	    if "ItemDetails" not in plcRequestObject:
	        raise Exception(
	            "Mandatory field ItemDetails is missing"
	        )
	
	    plcItemDetails = plcRequestObject.get(
	        "ItemDetails"
	    )
	
	    if plcItemDetails is None:
	        raise Exception(
	            "Mandatory field ItemDetails contains null"
	        )
	
	    if not isinstance(
	        plcItemDetails,
	        list
	    ):
	        raise Exception(
	            "ItemDetails must be a JSON array"
	        )
	
	    if len(
	        plcItemDetails
	    ) == 0:
	        raise Exception(
	            "ItemDetails must contain at least one record"
	        )
	
	    ###########################################################################
	    # Map all ItemDetails records
	    ###########################################################################
	
	    mesItemDetails = []
	
	    for itemIndex in range(
	        len(plcItemDetails)
	    ):
	        mesItemDetails.append(
	            mapItemDetail(
	                plcItemDetails[itemIndex],
	                itemIndex
	            )
	        )
	
	    return {
	        "WorkOrderId": workOrderId,
	        "RecipeId": recipeId,
	        "SourceEquipmentID": sourceFBS,
	        "DestinationEquipmentID": destinationFBS,
	        "ItemDetails": mesItemDetails
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
	
	    Raises an exception when one or more tag writes return bad quality.
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
	# Helper: Call MES Operational Results API
	###############################################################################
	
	def postOperationResultToMES(
	    mesUrl,
	    payload
	):
	    """
	    Sends the OperationResult request to MES without authentication.
	
	    Success:
	        HTTP status code 200
	
	    Failure:
	        Any HTTP status code other than 200
	
	    MES response body is logged for troubleshooting only.
	    It is not parsed and is not written to the PLC.
	
	    Returns:
	        {
	            "statusCode": integer,
	            "responseBody": string
	        }
	    """
	
	    client = system.net.httpClient()
	
	    headers = {
	        "Content-Type": "application/json",
	        "Accept": "application/json"
	    }
	
	    payloadJson = system.util.jsonEncode(
	        payload
	    )
	
	    logger.info(
	        "Sending MES Operational Results request. "
	        "URL=%s, Payload=%s"
	        % (
	            mesUrl,
	            payloadJson
	        )
	    )
	
	    ###########################################################################
	    # Execute REST POST
	    ###########################################################################
	
	    response = client.post(
	        url=mesUrl,
	        headers=headers,
	        data=payloadJson
	    )
	
	    if response is None:
	        raise Exception(
	            "MES HTTP client returned a null response"
	        )
	
	    ###########################################################################
	    # Read HTTP status code
	    ###########################################################################
	
	    httpStatusCode = int(
	        response.getStatusCode()
	    )
	
	    ###########################################################################
	    # MES response body is not required, but log it when available
	    ###########################################################################
	
	    responseBody = ""
	
	    try:
	        responseBody = safeUnicode(
	            response.getText()
	        )
	
	    except Exception as responseBodyError:
	        logger.warn(
	            "Unable to read MES response body. Error=%s"
	            % str(responseBodyError)
	        )
	
	    logger.info(
	        "MES Operational Results HTTP response received. "
	        "StatusCode=%s, ResponseBody=%s"
	        % (
	            str(httpStatusCode),
	            responseBody
	        )
	    )
	
	    return {
	        "statusCode": httpStatusCode,
	        "responseBody": responseBody
	    }
	
	
	###############################################################################
	# Helper: Write response metadata to PLC
	###############################################################################
	
	def writePLCResponseMetadata(
	    statusCode,
	    responseTimestamp,
	    responseAckNumber,
	    handshake
	):
	    """
	    Writes OperationResult response metadata to the PLC.
	
	    There is no ResponseData write for this interface.
	
	    Write sequence:
	        1. StatusCode
	        2. ResponseTimestamp
	        3. ResponseAckNumber
	        4. Validate all metadata writes
	        5. Write Handshake last
	
	    ResponseAckNumber:
	        StatusCode 200    -> RequestAckNumber
	        Any other status -> empty string
	    """
	
	    ###########################################################################
	    # Determine final ResponseAckNumber
	    ###########################################################################
	
	    if int(
	        statusCode
	    ) == 200:
	        finalResponseAckNumber = safeUnicode(
	            responseAckNumber
	        ).strip()
	
	    else:
	        finalResponseAckNumber = ""
	
	    logger.info(
	        "Writing PLC OperationResult response metadata. "
	        "StatusCode=%s, ResponseTimestamp=%s, "
	        "ResponseAckNumber=%s, Handshake=%s"
	        % (
	            str(statusCode),
	            safeUnicode(responseTimestamp),
	            finalResponseAckNumber,
	            str(handshake)
	        )
	    )
	
	    ###########################################################################
	    # Step 1: Write metadata
	    ###########################################################################
	
	    writePaths = [
	        STATUS_CODE_PATH,
	        RESPONSE_TIMESTAMP_PATH,
	        RESPONSE_ACK_NUMBER_PATH
	    ]
	
	    writeValues = [
	        int(statusCode),
	        safeUnicode(responseTimestamp),
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
	    # Step 2: Write Handshake last
	    ###########################################################################
	
	    logger.info(
	        "Writing OperationResult Handshake last. "
	        "Path=%s, Value=%s"
	        % (
	            HANDSHAKE_PATH,
	            str(handshake)
	        )
	    )
	
	    handshakeResult = system.tag.writeBlocking(
	        [HANDSHAKE_PATH],
	        [int(handshake)]
	    )[0]
	
	    if not handshakeResult.isGood():
	        raise Exception(
	            "PLC Handshake write failed. "
	            "Path=%s, Value=%s, Quality=%s"
	            % (
	                HANDSHAKE_PATH,
	                str(handshake),
	                str(handshakeResult)
	            )
	        )
	
	    logger.info(
	        "PLC Handshake write successful. "
	        "Path=%s, Value=%s, Quality=%s"
	        % (
	            HANDSHAKE_PATH,
	            str(handshake),
	            str(handshakeResult)
	        )
	    )
	
	
	###############################################################################
	# Helper: Final fallback metadata write
	###############################################################################
	
	def writePLCFailureMetadata(
	    statusCode,
	    responseTimestamp,
	    handshake
	):
	    """
	    Writes the final failure metadata when the normal response metadata write
	    encounters an exception.
	
	    ResponseAckNumber is always empty.
	    Handshake is written last.
	    """
	
	    metadataPaths = [
	        STATUS_CODE_PATH,
	        RESPONSE_TIMESTAMP_PATH,
	        RESPONSE_ACK_NUMBER_PATH
	    ]
	
	    metadataValues = [
	        int(statusCode),
	        safeUnicode(responseTimestamp),
	        ""
	    ]
	
	    logger.info(
	        "Writing PLC OperationResult failure metadata. "
	        "StatusCode=%s, ResponseTimestamp=%s, "
	        "ResponseAckNumber=<empty>"
	        % (
	            str(statusCode),
	            safeUnicode(responseTimestamp)
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
	    # Write Handshake last
	    ###########################################################################
	
	    handshakeResult = system.tag.writeBlocking(
	        [HANDSHAKE_PATH],
	        [int(handshake)]
	    )[0]
	
	    if not handshakeResult.isGood():
	        raise Exception(
	            "PLC failure Handshake write failed. "
	            "Path=%s, Value=%s, Quality=%s"
	            % (
	                HANDSHAKE_PATH,
	                str(handshake),
	                str(handshakeResult)
	            )
	        )
	
	    logger.info(
	        "PLC failure Handshake write successful. "
	        "Path=%s, Value=%s, Quality=%s"
	        % (
	            HANDSHAKE_PATH,
	            str(handshake),
	            str(handshakeResult)
	        )
	    )
	
	
	###############################################################################
	# Main Tag Change Script
	###############################################################################
	
	try:
	    logger.info(
	        "S2M OperationResult tag change script started"
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
	        # Step 2: Read current Handshake value
	        #######################################################################
	
	        handshakeValue = int(
	            newValue.value
	        )
	
	        logger.info(
	            "OperationResult Handshake value received: %s"
	            % str(handshakeValue)
	        )
	
	        #######################################################################
	        # Step 3: Handshake 2 means request already processed
	        #######################################################################
	
	        if handshakeValue == 2:
	            logger.info(
	                "Handshake is 2. OperationResult request is already "
	                "processed. No MES call or PLC write will be performed."
	            )
	
	        #######################################################################
	        # Step 4: Handshake 1 means process new request
	        #######################################################################
	
	        elif handshakeValue == 1:
	            logger.info(
	                "Valid OperationResult request Handshake received"
	            )
	
	            requestAckNumber = ""
	            transactionId = ""
	
	            try:
	                ###############################################################
	                # Read PLC RequestData and RequestAckNumber together
	                #
	                # RequestTimestamp and SenderFBS tags are not required for MES
	                # mapping because EventTimestamp is created by SCADA and the
	                # equipment values come from RequestData.SourceFBS and
	                # RequestData.DestinationFBS.
	                ###############################################################
	
	                requestPaths = [
	                    REQUEST_DATA_PATH,
	                    REQUEST_ACK_NUMBER_PATH
	                ]
	
	                logger.info(
	                    "Reading PLC OperationResult request tags. "
	                    "RequestDataPath=%s, RequestAckNumberPath=%s"
	                    % (
	                        REQUEST_DATA_PATH,
	                        REQUEST_ACK_NUMBER_PATH
	                    )
	                )
	
	                requestResults = system.tag.readBlocking(
	                    requestPaths
	                )
	
	                requestDataResult = requestResults[0]
	                requestAckNumberResult = requestResults[1]
	
	                logger.info(
	                    "PLC OperationResult request tags read completed. "
	                    "RequestDataQuality=%s, RequestAckNumberQuality=%s"
	                    % (
	                        str(requestDataResult.quality),
	                        str(requestAckNumberResult.quality)
	                    )
	                )
	
	                ###############################################################
	                # Validate RequestData quality
	                ###############################################################
	
	                if not requestDataResult.quality.isGood():
	                    raise Exception(
	                        "PLC RequestData tag quality is bad. "
	                        "Path=%s, Quality=%s"
	                        % (
	                            REQUEST_DATA_PATH,
	                            str(requestDataResult.quality)
	                        )
	                    )
	
	                ###############################################################
	                # Validate RequestAckNumber quality
	                ###############################################################
	
	                if not requestAckNumberResult.quality.isGood():
	                    raise Exception(
	                        "PLC RequestAckNumber tag quality is bad. "
	                        "Path=%s, Quality=%s"
	                        % (
	                            REQUEST_ACK_NUMBER_PATH,
	                            str(requestAckNumberResult.quality)
	                        )
	                    )
	
	                ###############################################################
	                # Validate RequestAckNumber value
	                ###############################################################
	
	                if requestAckNumberResult.value is None:
	                    raise Exception(
	                        "PLC RequestAckNumber tag contains null. "
	                        "Path=%s"
	                        % REQUEST_ACK_NUMBER_PATH
	                    )
	
	                requestAckNumber = safeUnicode(
	                    requestAckNumberResult.value
	                ).strip()
	
	                if requestAckNumber == "":
	                    raise Exception(
	                        "PLC RequestAckNumber tag contains an empty value. "
	                        "Path=%s"
	                        % REQUEST_ACK_NUMBER_PATH
	                    )
	
	                logger.info(
	                    "PLC RequestAckNumber received: %s"
	                    % requestAckNumber
	                )
	
	                ###############################################################
	                # Decode PLC RequestData
	                ###############################################################
	
	                plcRequestObject = decodePLCRequestData(
	                    requestDataResult.value
	                )
	
	                logger.info(
	                    "PLC OperationResult RequestData received: %s"
	                    % system.util.jsonEncode(
	                        plcRequestObject
	                    )
	                )
	
	                ###############################################################
	                # Map PLC RequestData to MES OperationResult
	                ###############################################################
	
	                operationResult = mapPLCRequestToOperationResult(
	                    plcRequestObject
	                )
	
	                ###############################################################
	                # Generate MES transaction values
	                ###############################################################
	
	                transactionId = generateTransactionId()
	                eventTimestamp = getUtcEventTimestamp()
	
	                ###############################################################
	                # Build MES request
	                #
	                # "TrasanactionId" spelling is intentionally retained.
	                ###############################################################
	
	                payload = {
	                    "Inputs": {
	                        "MessageHeader": {
	                            "InterfaceName": INTERFACE_NAME,
	                            "TrasanactionId": transactionId,
	                            "SourceSystem": SOURCE_SYSTEM,
	                            "TargetSystem": TARGET_SYSTEM,
	                            "EventTimestamp": eventTimestamp
	                        },
	                        "OperationResult": operationResult
	                    }
	                }
	
	                logger.info(
	                    "Mapped MES Operational Results request. "
	                    "TransactionId=%s, RequestAckNumber=%s, Payload=%s"
	                    % (
	                        transactionId,
	                        requestAckNumber,
	                        system.util.jsonEncode(
	                            payload
	                        )
	                    )
	                )
	
	                ###############################################################
	                # Call MES
	                ###############################################################
	
	                mesResult = postOperationResultToMES(
	                    MES_URL,
	                    payload
	                )
	
	                mesStatusCode = int(
	                    mesResult.get(
	                        "statusCode"
	                    )
	                )
	
	                ###############################################################
	                # Determine processing result
	                ###############################################################
	
	                responseTimestamp = getPLCResponseTimestamp()
	                responseHandshake = 2
	
	                if mesStatusCode == 200:
	                    ###########################################################
	                    # Successful MES processing
	                    ###########################################################
	
	                    writePLCResponseMetadata(
	                        200,
	                        responseTimestamp,
	                        requestAckNumber,
	                        responseHandshake
	                    )
	
	                    logger.info(
	                        "S2M OperationResult completed successfully. "
	                        "TransactionId=%s, RequestAckNumber=%s, "
	                        "ResponseAckNumber=%s, StatusCode=200, "
	                        "ResponseTimestamp=%s, Handshake=2, "
	                        "WorkOrderId=%s, RecipeId=%s, "
	                        "SourceEquipmentID=%s, "
	                        "DestinationEquipmentID=%s, "
	                        "ItemDetailsCount=%s"
	                        % (
	                            transactionId,
	                            requestAckNumber,
	                            requestAckNumber,
	                            responseTimestamp,
	                            operationResult.get(
	                                "WorkOrderId"
	                            ),
	                            operationResult.get(
	                                "RecipeId"
	                            ),
	                            operationResult.get(
	                                "SourceEquipmentID"
	                            ),
	                            operationResult.get(
	                                "DestinationEquipmentID"
	                            ),
	                            str(
	                                len(
	                                    operationResult.get(
	                                        "ItemDetails"
	                                    )
	                                )
	                            )
	                        )
	                    )
	
	                else:
	                    ###########################################################
	                    # MES returned non-200
	                    #
	                    # Write the MES HTTP status code to the PLC.
	                    # ResponseAckNumber remains empty.
	                    ###########################################################
	
	                    writePLCResponseMetadata(
	                        mesStatusCode,
	                        responseTimestamp,
	                        "",
	                        responseHandshake
	                    )
	
	                    logger.error(
	                        "S2M OperationResult MES request failed. "
	                        "TransactionId=%s, RequestAckNumber=%s, "
	                        "MESStatusCode=%s, PLCStatusCode=%s, "
	                        "ResponseAckNumber=<empty>, Handshake=2"
	                        % (
	                            transactionId,
	                            requestAckNumber,
	                            str(mesStatusCode),
	                            str(mesStatusCode)
	                        )
	                    )
	
	            except Exception as processingError:
	                logger.error(
	                    "S2M OperationResult processing failed. "
	                    "TransactionId=%s, RequestAckNumber=%s, Error=%s"
	                    % (
	                        transactionId,
	                        requestAckNumber,
	                        str(processingError)
	                    )
	                )
	
	                ###############################################################
	                # Technical or validation failure
	                ###############################################################
	
	                failureResponseTimestamp = getPLCResponseTimestamp()
	
	                try:
	                    writePLCResponseMetadata(
	                        410,
	                        failureResponseTimestamp,
	                        "",
	                        2
	                    )
	
	                except Exception as failureWriteError:
	                    logger.error(
	                        "Failed to write OperationResult PLC failure "
	                        "metadata: %s"
	                        % str(failureWriteError)
	                    )
	
	                    ###########################################################
	                    # Final fallback
	                    ###########################################################
	
	                    try:
	                        writePLCFailureMetadata(
	                            410,
	                            failureResponseTimestamp,
	                            2
	                        )
	
	                    except Exception as fallbackWriteError:
	                        logger.error(
	                            "Final OperationResult PLC failure metadata "
	                            "write failed: %s"
	                            % str(fallbackWriteError)
	                        )
	
	        #######################################################################
	        # Step 5: Handshake 3 means invalid or cancelled request
	        #######################################################################
	
	        elif handshakeValue == 3:
	            logger.warn(
	                "OperationResult Handshake 3 received. MES call skipped."
	            )
	
	            cancelledResponseTimestamp = getPLCResponseTimestamp()
	
	            try:
	                writePLCResponseMetadata(
	                    510,
	                    cancelledResponseTimestamp,
	                    "",
	                    3
	                )
	
	            except Exception as cancelledWriteError:
	                logger.error(
	                    "Failed to write cancelled OperationResult metadata: %s"
	                    % str(cancelledWriteError)
	                )
	
	                try:
	                    writePLCFailureMetadata(
	                        510,
	                        cancelledResponseTimestamp,
	                        3
	                    )
	
	                except Exception as cancelledFallbackError:
	                    logger.error(
	                        "Failed to write cancelled OperationResult fallback "
	                        "metadata: %s"
	                        % str(cancelledFallbackError)
	                    )
	
	        #######################################################################
	        # Step 6: Unsupported Handshake
	        #######################################################################
	
	        else:
	            logger.warn(
	                "Unsupported OperationResult Handshake value received: %s"
	                % str(handshakeValue)
	            )
	
	            unsupportedResponseTimestamp = getPLCResponseTimestamp()
	
	            try:
	                writePLCResponseMetadata(
	                    510,
	                    unsupportedResponseTimestamp,
	                    "",
	                    handshakeValue
	                )
	
	            except Exception as unsupportedWriteError:
	                logger.error(
	                    "Failed to write unsupported OperationResult Handshake "
	                    "metadata: %s"
	                    % str(unsupportedWriteError)
	                )
	
	                try:
	                    writePLCFailureMetadata(
	                        510,
	                        unsupportedResponseTimestamp,
	                        handshakeValue
	                    )
	
	                except Exception as unsupportedFallbackError:
	                    logger.error(
	                        "Failed to write unsupported OperationResult fallback "
	                        "metadata: %s"
	                        % str(unsupportedFallbackError)
	                    )
	
	
	except Exception as scriptError:
	    logger.error(
	        "S2M OperationResult tag change script failed: %s"
	        % str(scriptError)
	    )