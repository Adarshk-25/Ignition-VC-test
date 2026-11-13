def onTagChange(initialChange, newValue, previousValue, event, executionCount):
	###############################################################################
	# Project        : AGRATAS SCADA - MES Integration
	# Interface      : S2M.MaterialInfo
	# Module         : Ignition Gateway Tag Change Script
	# MES Operation  : AGR_PRD_S2M_MaterialInfo
	#
	# Description:
	#
	#   1. Monitors AGSetItemInfo Handshake tags for multiple PLC/equipment folders.
	#   2. Determines the PLC/equipment folder dynamically from the triggering path.
	#   3. Processes request only when Handshake = 1.
	#   4. Reads:
	#
	#         RequestData
	#         RequestAckNumber
	#         RequestTimestamp
	#         SenderFBS
	#
	#   5. Uses the triggering Ignition provider for ALL tag reads/writes.
	#
	#         Example:
	#
	#         providerPrefix = [default]
	#
	#   6. SenderFBS is NOT an Ignition Tag Provider.
	#
	#         Example:
	#
	#         SenderFBS = IN11.E117.PCE.COT21
	#
	#   7. MES mapping:
	#
	#         MessageHeader.Equipment
	#             <- SenderFBS
	#
	#         MaterialInfo.FeedingLocation
	#             <- SenderFBS
	#
	#   8. equipmentName remains the Ignition PLC folder:
	#
	#         IN11_E117_PCE_COT21
	#
	#      and is used only for tag paths.
	#
	#   9. Calls MES.
	#  10. Maps MES GradeInfo into PLC CellInfo[0..1].
	#  11. Writes ResponseData, StatusCode, ResponseTimestamp and
	#      ResponseAckNumber back to the SAME triggering PLC.
	#  12. RequestTimestamp is read/validated for audit metadata.
	#  13. Writes Handshake LAST.
	#
	#
	# IMPORTANT MAPPING
	# -----------------------------------------------------------------------------
	#
	# Trigger path:
	#
	# [default]IN11_E117_PCE_COT21/AGCalls/AGSetItemInfo/Handshake
	#
	# Therefore:
	#
	# providerPrefix = [default]
	# equipmentName  = IN11_E117_PCE_COT21
	#
	#
	# SenderFBS tag value:
	#
	# IN11.E117.PCE.COT21
	#
	#
	# MES:
	#
	# Equipment       = IN11.E117.PCE.COT21
	# FeedingLocation = IN11.E117.PCE.COT21
	#
	#
	# PLC paths STILL use:
	#
	# [default]IN11_E117_PCE_COT21/AGCalls/AGSetItemInfo/...
	#
	#
	# HANDSHAKE RULE
	# -----------------------------------------------------------------------------
	#
	# Handshake = 0 -> Ignore
	# Handshake = 1 -> Process
	# Handshake = 2 -> Ignore
	# Handshake = 3 -> MES skipped / error response
	#
	#
	# RESPONSE TIMESTAMP
	# -----------------------------------------------------------------------------
	#
	# ResponseTimestamp must remain java.util.Date.
	#
	# CORRECT:
	#
	#     system.date.now()
	#
	# WRONG:
	#
	#     system.date.format(...)
	#
	#
	# Version History
	# -----------------------------------------------------------------------------
	# Version | Date        | Description
	# -----------------------------------------------------------------------------
	# 1.0     | 19-Aug-2026 | Initial implementation
	# 1.9     | 21-Aug-2026 | Handshake written last
	# 2.0     | 23-Aug-2026 | Fixed ResponseTimestamp Date conversion
	# 2.1     | 25-Aug-2026 | Dynamic equipment routing
	# 2.2     | 25-Aug-2026 | Use event.getTagPath()
	# 2.3     | 25-Aug-2026 | Additional equipment nodes
	# 2.4     | 02-Sep-2026 | Read SenderFBS as separate AGCalls tag
	# 2.5     | 02-Sep-2026 | Keep provider from triggering tag
	# 2.6     | 02-Sep-2026 | SenderFBS -> MES Equipment
	# 2.7     | 02-Sep-2026 | SenderFBS -> MES FeedingLocation
	# 2.9     | 07-Sep-2026 | Film Wrapping request/response mapping update
	# 2.9     | 07-Sep-2026 | CellInfo fixed-array response mapping
	# 3.0     | 07-Sep-2026 | Accept RecipeID/RecipeId; error path writes metadata only
	# 3.1     | 07-Sep-2026 | Align AGItemResponse with PLC UDT: ItemAuthorized + CellInfo[0..1]
	# 3.2     | 07-Sep-2026 | Film Wrapping: OperationFlag=2; MES GradeInfo -> PLC CellInfo[0..1]; top-level QualityStatus applied to each cell
	    # 3.3     | 07-Sep-2026 | Deduplicate MES GradeInfo by SerialNo; map first 2 unique cells to PLC ARRAY[0..1]
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
	# Helper: Extract provider + equipment folder from Gateway Tag Change path
	#
	# Example:
	#
	# [default]IN11_E117_PCE_COT21/AGCalls/AGSetItemInfo/Handshake
	#
	# Output:
	#
	# providerPrefix = [default]
	# equipmentName  = IN11_E117_PCE_COT21
	###############################################################################
	
	def getEquipmentFromTagPath(triggerTagPath):
	
	    triggerPathString = safeUnicode(
	        triggerTagPath
	    ).strip()
	
	
	    if triggerPathString == "":
	
	        raise Exception(
	            "Trigger tag path is empty"
	        )
	
	
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
	
	        providerPrefix = "[default]"
	
	        equipmentName = firstPathSegment
	
	
	    providerPrefix = safeUnicode(
	        providerPrefix
	    ).strip()
	
	
	    equipmentName = safeUnicode(
	        equipmentName
	    ).strip()
	
	
	    if providerPrefix == "":
	
	        providerPrefix = "[default]"
	
	
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
	
	    # This object is retained only as an internal placeholder.
	    # Non-200 paths do NOT write structured ResponseData to the PLC.
	    # PLC AGItemResponse exact structure:
	    #   ItemID         : WString
	    #   ItemAuthorized : Bool
	    #   CellInfo       : ARRAY[0..1] OF AGCellInfo
	    return {
	
	        "ItemID": "",
	
	        "ItemAuthorized": False,
	
	        "CellInfo": [
	            {
	                "QualityStatus": False,
	                "CellID": "",
	                "CellGrade": ""
	            },
	            {
	                "QualityStatus": False,
	                "CellID": "",
	                "CellGrade": ""
	            }
	        ]
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
	    # IMPORTANT - failure path
	    #
	    # ResponseData is a Siemens OPC UA structured value (AGItemResponse).
	    # Do NOT write a synthetic/empty Python object on failures. In particular,
	    # an incorrectly shaped CellInfo array or wrong member names/types can
	    # produce Bad_EncodingError.
	    #
	    # On non-200 responses write only the scalar metadata and Handshake.
	    ###########################################################################
	
	    if int(statusCode) != 200:
	
	        logger.info(
	            "Non-success PLC response. Skipping structured ResponseData write "
	            "and writing failure metadata only. StatusCode=%s"
	            % str(statusCode)
	        )
	
	        writePLCFailureMetadata(
	            statusCodePath,
	            responseTimePath,
	            responseAckNumberPath,
	            handshakePath,
	            statusCode,
	            responseTime,
	            handshake
	        )
	
	        return
	
	
	    ###########################################################################
	    # ResponseAckNumber
	    ###########################################################################
	
	    if int(
	        statusCode
	    ) == 200:
	
	        try:
	            finalResponseAckNumber = int(responseAckNumber)
	        except Exception:
	            raise Exception(
	                "ResponseAckNumber must be numeric for PLC Int tag. Value=%s"
	                % str(responseAckNumber)
	            )
	
	    else:
	
	        finalResponseAckNumber = 0
	
	
	    ###########################################################################
	    # ResponseTimestamp must stay Java Date
	    ###########################################################################
	
	    if responseTime is None:
	
	        responseTime = system.date.now()
	
	
	    ###########################################################################
	    # Build PLC response
	    ###########################################################################
	
	    plcCellInfo = responseData.get(
	        "CellInfo",
	        None
	    )
	
	    if not isinstance(plcCellInfo, list):
	        raise Exception(
	            "PLC ResponseData.CellInfo must be a list for AGItemResponse"
	        )
	
	    if len(plcCellInfo) != 2:
	        raise Exception(
	            "PLC ResponseData.CellInfo must contain exactly 2 elements "
	            "for ARRAY[0..1]. Received=%s"
	            % str(len(plcCellInfo))
	        )
	
	    normalizedCellInfo = []
	
	    for cellIndex in range(2):
	
	        cell = plcCellInfo[cellIndex]
	
	        if not isinstance(cell, dict):
	            raise Exception(
	                "PLC ResponseData.CellInfo[%s] must be an object"
	                % str(cellIndex)
	            )
	
	        normalizedCellInfo.append({
	            "QualityStatus": bool(
	                cell.get(
	                    "QualityStatus",
	                    False
	                )
	            ),
	            "CellID": safeUnicode(
	                cell.get(
	                    "CellID",
	                    ""
	                )
	            ).strip(),
	            "CellGrade": safeUnicode(
	                cell.get(
	                    "CellGrade",
	                    ""
	                )
	            ).strip()
	        })
	
	    plcResponseDocument = {
	
	        "ItemID": safeUnicode(
	            responseData.get(
	                "ItemID",
	                ""
	            )
	        ).strip(),
	
	        "ItemAuthorized": bool(
	            responseData.get(
	                "ItemAuthorized",
	                False
	            )
	        ),
	
	        "CellInfo": normalizedCellInfo
	    }
	
	
	    responseDataJson = system.util.jsonEncode(
	        plcResponseDocument
	    )
	
	
	    responseDataDocument = system.util.jsonDecode(
	        responseDataJson
	    )
	
	
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
	    # Write structured ResponseData FIRST and validate it independently.
	    #
	    # This prevents a structured OPC UA encoding failure from making the scalar
	    # metadata writes appear to fail in the same batch.
	    ###########################################################################
	
	    responseWriteResult = system.tag.writeBlocking(
	        [responseDataPath],
	        [responseDataDocument]
	    )[0]
	
	    if not responseWriteResult.isGood():
	        raise Exception(
	            "PLC ResponseData write failed. "
	            "Path=%s, Quality=%s, ResponseData=%s"
	            % (
	                responseDataPath,
	                str(responseWriteResult),
	                responseDataJson
	            )
	        )
	
	    logger.info(
	        "PLC structured ResponseData write successful. "
	        "Path=%s, Quality=%s, ResponseData=%s"
	        % (
	            responseDataPath,
	            str(responseWriteResult),
	            responseDataJson
	        )
	    )
	
	    ###########################################################################
	    # Write scalar metadata after ResponseData succeeds
	    ###########################################################################
	
	    writePaths = [
	        statusCodePath,
	        responseTimePath,
	        responseAckNumberPath
	    ]
	
	    writeValues = [
	        int(statusCode),
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
	    # Handshake LAST
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
	
	        0
	    ]
	
	
	    logger.info(
	        "Writing PLC failure metadata. "
	        "StatusCode=%s, "
	        "ResponseTime=%s, "
	        "ResponseAckNumber=0"
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
	        # Step 1 - Trigger path
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
	        # Step 2 - Extract Tag Provider + equipment folder
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
	        # IMPORTANT
	        #
	        # equipmentName is used ONLY for Ignition tag paths.
	        #
	        # Do not send equipmentName to MES after SenderFBS has been read.
	        #######################################################################
	
	        equipment = equipmentName
	
	        senderFBS = ""
	
	        feedingLocation = ""
	
	        employeeNo = "ADMIN"
	
	
	        logger.info(
	            "Dynamic PLC equipment resolved. "
	            "TriggerTagPath=%s, "
	            "ProviderPrefix=%s, "
	            "EquipmentFolder=%s"
	            % (
	                triggerTagPath,
	                providerPrefix,
	                equipmentName
	            )
	        )
	
	
	        #######################################################################
	        # Step 3 - Build AGSetItemInfo base path
	        #######################################################################
	
	        agSetItemInfoBasePath = (
	            providerPrefix
	            + equipmentName
	            + "/AGCalls/AGSetItemInfo"
	        )
	
	
	        #######################################################################
	        # Request tag paths
	        #######################################################################
	
	        requestDataPath = (
	            agSetItemInfoBasePath
	            + "/RequestData"
	        )
	
	
	        requestAckNumberPath = (
	            agSetItemInfoBasePath
	            + "/RequestAckNumber"
	        )
	
	
	        requestTimestampPath = (
	            agSetItemInfoBasePath
	            + "/RequestTimestamp"
	        )
	
	
	        senderFBSPath = (
	            agSetItemInfoBasePath
	            + "/SenderFBS"
	        )
	
	
	        #######################################################################
	        # Response tag paths
	        #######################################################################
	
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
	
	
	        logger.info(
	            "Dynamic AGSetItemInfo routing resolved. "
	            "ProviderPrefix=%s, "
	            "EquipmentFolder=%s, "
	            "BasePath=%s"
	            % (
	                providerPrefix,
	                equipmentName,
	                agSetItemInfoBasePath
	            )
	        )
	
	
	        logger.info(
	            "Dynamic PLC paths. "
	            "RequestData=%s, "
	            "RequestAckNumber=%s, "
	            "RequestTimestamp=%s, "
	            "SenderFBS=%s, "
	            "ResponseData=%s, "
	            "StatusCode=%s, "
	            "ResponseTimestamp=%s, "
	            "ResponseAckNumber=%s, "
	            "Handshake=%s"
	            % (
	                requestDataPath,
	                requestAckNumberPath,
	                requestTimestampPath,
	                senderFBSPath,
	                responseDataPath,
	                statusCodePath,
	                responseTimePath,
	                responseAckNumberPath,
	                handshakePath
	            )
	        )
	
	
	        #######################################################################
	        # Step 4 - Handshake
	        #######################################################################
	
	        handshakeValue = int(
	            newValue.value
	        )
	
	
	        logger.info(
	            "Handshake value received. "
	            "EquipmentFolder=%s, "
	            "Handshake=%s"
	            % (
	                equipmentName,
	                str(
	                    handshakeValue
	                )
	            )
	        )
	
	
	        #######################################################################
	        # MES Configuration
	        #######################################################################
	
	        mesUrl = (
	            "https://aprisomesdev.agratas.com/"
	            "apriso/httpServices/operations/"
	            "AGR_PRD_S2M_MaterialInfo"
	        )
	
	
	        interfaceName = "S2M.MaterialInfo"
	
	        sourceSystem = "SCADA"
	
	        targetSystem = "MES"
	
	
	        #######################################################################
	        # Initialize
	        #######################################################################
	
	        requestAckNumber = ""
	
	
	        #######################################################################
	        # Handshake 0 or 2 -> Ignore
	        #######################################################################
	
	        if handshakeValue in (
	            0,
	            2
	        ):
	
	            logger.info(
	                "Handshake=%s ignored. "
	                "EquipmentFolder=%s. "
	                "No MES call or PLC response write."
	                % (
	                    str(
	                        handshakeValue
	                    ),
	                    equipmentName
	                )
	            )
	
	
	        #######################################################################
	        # Handshake 1 -> Process
	        #######################################################################
	
	        elif handshakeValue == 1:
	
	            logger.info(
	                "Valid MaterialInfo request received. "
	                "EquipmentFolder=%s"
	                % equipmentName
	            )
	
	
	            responseTime = system.date.now()
	
	
	            try:
	
	                ###############################################################
	                # Read RequestData + RequestAckNumber + RequestTimestamp + SenderFBS
	                ###############################################################
	
	                logger.info(
	                    "Reading PLC request tags. "
	                    "EquipmentFolder=%s, "
	                    "RequestData=%s, "
	                    "RequestAckNumber=%s, "
	                    "RequestTimestamp=%s, "
	                    "SenderFBS=%s"
	                    % (
	                        equipmentName,
	                        requestDataPath,
	                        requestAckNumberPath,
	                        requestTimestampPath,
	                        senderFBSPath
	                    )
	                )
	
	
	                requestTagResults = system.tag.readBlocking([
	
	                    requestDataPath,
	
	                    requestAckNumberPath,
	
	                    requestTimestampPath,
	
	                    senderFBSPath
	                ])
	
	
	                requestTagResult = requestTagResults[
	                    0
	                ]
	
	
	                requestAckNumberResult = requestTagResults[
	                    1
	                ]
	
	
	                requestTimestampResult = requestTagResults[
	                    2
	                ]
	
	
	                senderFBSResult = requestTagResults[
	                    3
	                ]
	
	
	                ###############################################################
	                # Log read qualities
	                ###############################################################
	
	                logger.info(
	                    "PLC request tag read completed. "
	                    "EquipmentFolder=%s, "
	                    "RequestDataQuality=%s, "
	                    "RequestAckNumberQuality=%s, "
	                    "RequestTimestampQuality=%s, "
	                    "SenderFBSQuality=%s"
	                    % (
	                        equipmentName,
	                        str(
	                            requestTagResult.quality
	                        ),
	                        str(
	                            requestAckNumberResult.quality
	                        ),
	                        str(
	                            requestTimestampResult.quality
	                        ),
	                        str(
	                            senderFBSResult.quality
	                        )
	                    )
	                )
	
	
	                ###############################################################
	                # RequestData quality
	                ###############################################################
	
	                if not requestTagResult.quality.isGood():
	
	                    raise Exception(
	                        "PLC RequestData tag quality is bad. "
	                        "EquipmentFolder=%s, "
	                        "Path=%s, "
	                        "Quality=%s"
	                        % (
	                            equipmentName,
	                            requestDataPath,
	                            str(
	                                requestTagResult.quality
	                            )
	                        )
	                    )
	
	
	                ###############################################################
	                # RequestAckNumber quality
	                ###############################################################
	
	                if not requestAckNumberResult.quality.isGood():
	
	                    raise Exception(
	                        "PLC RequestAckNumber tag quality is bad. "
	                        "EquipmentFolder=%s, "
	                        "Path=%s, "
	                        "Quality=%s"
	                        % (
	                            equipmentName,
	                            requestAckNumberPath,
	                            str(
	                                requestAckNumberResult.quality
	                            )
	                        )
	                    )
	
	
	                ###############################################################
	                # RequestTimestamp quality
	                ###############################################################
	
	                if not requestTimestampResult.quality.isGood():
	
	                    raise Exception(
	                        "PLC RequestTimestamp tag quality is bad. "
	                        "EquipmentFolder=%s, "
	                        "Path=%s, "
	                        "Quality=%s"
	                        % (
	                            equipmentName,
	                            requestTimestampPath,
	                            str(
	                                requestTimestampResult.quality
	                            )
	                        )
	                    )
	
	
	                ###############################################################
	                # SenderFBS quality
	                ###############################################################
	
	                if not senderFBSResult.quality.isGood():
	
	                    raise Exception(
	                        "PLC SenderFBS tag quality is bad. "
	                        "EquipmentFolder=%s, "
	                        "Path=%s, "
	                        "Quality=%s"
	                        % (
	                            equipmentName,
	                            senderFBSPath,
	                            str(
	                                senderFBSResult.quality
	                            )
	                        )
	                    )
	
	
	                ###############################################################
	                # RequestData value
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
	                # RequestAckNumber
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
	
	
	                ###############################################################
	                # RequestTimestamp
	                #
	                # PLC datatype: DateTime. Keep the java.util.Date value as-is.
	                # It is audit/diagnostic metadata and is not sent to MES because
	                # MES MessageHeader.EventTimestamp is generated by SCADA.
	                ###############################################################
	
	                requestTimestamp = requestTimestampResult.value
	
	                if requestTimestamp is None:
	
	                    raise Exception(
	                        "PLC RequestTimestamp tag contains null. "
	                        "EquipmentFolder=%s, "
	                        "Path=%s"
	                        % (
	                            equipmentName,
	                            requestTimestampPath
	                        )
	                    )
	
	                logger.info(
	                    "PLC RequestTimestamp read successfully. "
	                    "EquipmentFolder=%s, "
	                    "RequestTimestamp=%s"
	                    % (
	                        equipmentName,
	                        formatDateForLog(
	                            requestTimestamp
	                        )
	                    )
	                )
	
	
	                ###############################################################
	                # SenderFBS
	                ###############################################################
	
	                if senderFBSResult.value is None:
	
	                    raise Exception(
	                        "PLC SenderFBS tag contains null. "
	                        "Path=%s"
	                        % senderFBSPath
	                    )
	
	
	                senderFBS = safeUnicode(
	                    senderFBSResult.value
	                ).strip()
	
	
	                if senderFBS == "":
	
	                    raise Exception(
	                        "PLC SenderFBS tag contains empty value. "
	                        "Path=%s"
	                        % senderFBSPath
	                    )
	
	
	                ###############################################################
	                # CORRECT MES MAPPING
	                #
	                # SenderFBS -> Equipment
	                # SenderFBS -> FeedingLocation
	                #
	                # Example:
	                #
	                # SenderFBS      = IN11.E117.PCE.COT21
	                # Equipment      = IN11.E117.PCE.COT21
	                # FeedingLocation= IN11.E117.PCE.COT21
	                ###############################################################
	
	                equipment = senderFBS
	
	                feedingLocation = senderFBS
	
	
	                logger.info(
	                    "SenderFBS mapped to MES values. "
	                    "EquipmentFolder=%s, "
	                    "ProviderPrefix=%s, "
	                    "SenderFBS=%s, "
	                    "MESEquipment=%s, "
	                    "FeedingLocation=%s"
	                    % (
	                        equipmentName,
	                        providerPrefix,
	                        senderFBS,
	                        equipment,
	                        feedingLocation
	                    )
	                )
	
	
	                ###############################################################
	                # Incoming PLC request log
	                ###############################################################
	
	                logger.info(
	                    "PLC request received. "
	                    "EquipmentFolder=%s, "
	                    "SenderFBS=%s, "
	                    "RequestAckNumber=%s, "
	                    "RequestData=%s"
	                    % (
	                        equipmentName,
	                        senderFBS,
	                        requestAckNumber,
	                        plcRequestString
	                    )
	                )
	
	
	                ###############################################################
	                # Decode RequestData
	                ###############################################################
	
	                try:
	
	                    plcRequestObject = system.util.jsonDecode(
	                        plcRequestString
	                    )
	
	
	                except Exception as decodeError:
	
	                    raise Exception(
	                        "Invalid PLC RequestData JSON. "
	                        "EquipmentFolder=%s, "
	                        "Error=%s, "
	                        "Value=%s"
	                        % (
	                            equipmentName,
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
	                # Extract PLC RequestData values
	                ###############################################################
	
	                itemId = safeUnicode(
	                    plcRequestObject.get(
	                        "ItemID",
	                        ""
	                    )
	                ).strip()
	
	
	                # PLC projects currently exist with both spellings:
	                #   RecipeID  (new Film Wrapping contract)
	                #   RecipeId  (legacy/current PLC UDT value seen in FAT)
	                # Prefer RecipeID, but fall back to RecipeId so the interface
	                # remains backward-compatible during PLC rollout.
	                recipeId = safeUnicode(
	                    plcRequestObject.get(
	                        "RecipeID",
	                        plcRequestObject.get(
	                            "RecipeId",
	                            ""
	                        )
	                    )
	                ).strip()
	
	
	                workOrderId = safeUnicode(
	                    plcRequestObject.get(
	                        "WorkOrderID",
	                        ""
	                    )
	                ).strip()
	
	
	                ###############################################################
	                # Mandatory fields
	                ###############################################################
	
	                if itemId == "":
	
	                    raise Exception(
	                        "Mandatory field ItemID is missing"
	                    )
	
	
	                if recipeId == "":
	
	                    raise Exception(
	                        "Mandatory field RecipeID is missing"
	                    )
	
	
	                if workOrderId == "":
	
	                    raise Exception(
	                        "Mandatory field WorkOrderID is missing"
	                    )
	
	
	                logger.info(
	                    "PLC request mapping validated. "
	                    "ItemID=%s, RecipeID=%s, WorkOrderID=%s"
	                    % (
	                        itemId,
	                        recipeId,
	                        workOrderId
	                    )
	                )
	
	
	                ###############################################################
	                # MES UTC EventTimestamp
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
	                # Build MES Request Payload
	                #
	                # The Film Wrapping payload supplied by MES is handled as the
	                # MES response under Outputs.ResponseJSON.
	                #
	                # Film Wrapping PLC -> MES request mapping:
	                # PLC.ItemID      -> MES.HuContainer
	                # PLC.senderFBS   -> MES.FeedingLocation
	                # PLC.WorkOrderID -> MES.WorkOrder
	                # PLC.RecipeID    -> MES.RecipeID
	                #
	                # senderFBS and FeedingLocation are intentionally identical.
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
	
	                            "OperationFlag": 2,
	
	                            "HuContainer": itemId,
	
	                            "FeedingLocation": feedingLocation,
	
	                            "WorkOrder": workOrderId,
	
	                            "RecipeID": recipeId
	                        }
	                    }
	                }
	
	
	                ###############################################################
	                # MES request log
	                ###############################################################
	
	                logger.info(
	                    "Calling MES MaterialInfo. "
	                    "EquipmentFolder=%s, "
	                    "Equipment=%s, "
	                    "ProviderPrefix=%s, "
	                    "SenderFBS=%s, "
	                    "FeedingLocation=%s, "
	                    "TransactionId=%s, "
	                    "Payload=%s"
	                    % (
	                        equipmentName,
	                        equipment,
	                        providerPrefix,
	                        senderFBS,
	                        feedingLocation,
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
	                # Film Wrapping MES -> PLC response mapping
	                #
	                # Actual PLC AGItemResponse UDT from TIA/OPC UA:
	                #
	                #   ItemID         : WString
	                #   ItemAuthorized : Bool
	                #   CellInfo       : ARRAY[0..1] OF AGCellInfo
	                #
	                #   AGCellInfo:
	                #       QualityStatus : Bool
	                #       CellID        : WString
	                #       CellGrade     : WString
	                #
	                # Mapping:
	                # MES.HuContainer        -> PLC.ItemID
	                # MES.Authorization      -> PLC.ItemAuthorized
	                # MES.CellInfo[]         -> PLC.CellInfo[]
	                # MES.CellInfo.SerialNo  -> PLC.CellInfo.CellID
	                # MES.CellInfo.Grade     -> PLC.CellInfo.CellGrade
	                # MES.QualityStatus      -> PLC.CellInfo.QualityStatus (Bool)
	                #
	                # GradeInfo is accepted only as a temporary MES alias because an
	                # earlier Film Wrapping payload used that name. CellInfo is the
	                # preferred/final contract.
	                ###############################################################
	
	                authorizationValue = mesMaterialInfo.get(
	                    "Authorization",
	                    False
	                )
	
	                itemAuthorized = convertToBoolean(
	                    authorizationValue
	                )
	
	                ###################################################################
	                # Actual Apriso Film Wrapping response:
	                #   MaterialInfo.GradeInfo[] -> PLC CellInfo[]
	                #   MaterialInfo.QualityStatus -> each PLC CellInfo.QualityStatus
	                #
	                # MES can return many GradeInfo rows, including duplicate SerialNo
	                # values. PLC AGItemResponse.CellInfo is fixed ARRAY[0..1].
	                #
	                # Mapping rule used here:
	                #   1. Ignore rows with blank SerialNo.
	                #   2. Deduplicate by SerialNo, preserving MES order.
	                #   3. Take the first two UNIQUE SerialNo records for PLC [0] and [1].
	                #   4. If fewer than two unique cells are returned, pad the remaining
	                #      PLC element with a valid empty AGCellInfo structure.
	                #
	                # This prevents duplicate MES rows such as SN-001-01 repeated many
	                # times from filling both PLC positions with the same CellID.
	                ###################################################################
	
	                if "GradeInfo" not in mesMaterialInfo:
	                    raise Exception(
	                        "MES Film Wrapping response is missing MaterialInfo.GradeInfo. "
	                        "MaterialInfo=%s"
	                        % system.util.jsonEncode(mesMaterialInfo)
	                    )
	
	                mesGradeInfo = mesMaterialInfo.get("GradeInfo")
	
	                if mesGradeInfo is None:
	                    raise Exception("MES MaterialInfo.GradeInfo is null")
	
	                if not isinstance(mesGradeInfo, list):
	                    raise Exception("MES MaterialInfo.GradeInfo must be an array/list")
	
	                # MES currently returns QualityStatus once at MaterialInfo level.
	                # PLC requires one Bool in every CellInfo element, so apply the same
	                # transaction-level status to each mapped PLC cell.
	                mesQualityStatusValue = mesMaterialInfo.get(
	                    "QualityStatus",
	                    False
	                )
	
	                plcQualityStatus = convertQualityStatusToBoolean(
	                    mesQualityStatusValue
	                )
	
	                ###################################################################
	                # Deduplicate MES GradeInfo by SerialNo
	                ###################################################################
	
	                uniqueMesCells = []
	                seenSerialNumbers = {}
	
	                for mesGradeIndex in range(len(mesGradeInfo)):
	
	                    gradeRow = mesGradeInfo[mesGradeIndex]
	
	                    if not isinstance(gradeRow, dict):
	                        logger.warn(
	                            "Ignoring MES GradeInfo row because it is not an object. "
	                            "Equipment=%s, Index=%s, Value=%s"
	                            % (
	                                equipment,
	                                str(mesGradeIndex),
	                                str(gradeRow)
	                            )
	                        )
	                        continue
	
	                    serialNo = safeUnicode(
	                        gradeRow.get("SerialNo", "")
	                    ).strip()
	
	                    if serialNo == "":
	                        logger.warn(
	                            "Ignoring MES GradeInfo row because SerialNo is empty. "
	                            "Equipment=%s, Index=%s"
	                            % (
	                                equipment,
	                                str(mesGradeIndex)
	                            )
	                        )
	                        continue
	
	                    if serialNo in seenSerialNumbers:
	                        logger.info(
	                            "Ignoring duplicate MES GradeInfo SerialNo. "
	                            "Equipment=%s, Index=%s, SerialNo=%s"
	                            % (
	                                equipment,
	                                str(mesGradeIndex),
	                                serialNo
	                            )
	                        )
	                        continue
	
	                    seenSerialNumbers[serialNo] = True
	                    uniqueMesCells.append(gradeRow)
	
	                logger.info(
	                    "MES GradeInfo normalized for PLC fixed array. "
	                    "Equipment=%s, RawCount=%s, UniqueSerialCount=%s, "
	                    "PLCArrayCapacity=2"
	                    % (
	                        equipment,
	                        str(len(mesGradeInfo)),
	                        str(len(uniqueMesCells))
	                    )
	                )
	
	                if len(uniqueMesCells) > 2:
	                    ignoredSerials = []
	
	                    for ignoredIndex in range(2, len(uniqueMesCells)):
	                        ignoredSerials.append(
	                            safeUnicode(
	                                uniqueMesCells[ignoredIndex].get("SerialNo", "")
	                            ).strip()
	                        )
	
	                    logger.warn(
	                        "MES returned more unique Film Wrapping cells than PLC can store. "
	                        "Only first 2 unique SerialNo records will be written. "
	                        "Equipment=%s, UniqueCount=%s, IgnoredSerialNos=%s"
	                        % (
	                            equipment,
	                            str(len(uniqueMesCells)),
	                            ",".join(ignoredSerials)
	                        )
	                    )
	
	                plcCellInfo = []
	
	                ###################################################################
	                # Map maximum 2 unique cells into PLC CellInfo[0..1]
	                ###################################################################
	
	                cellsToMap = min(
	                    len(uniqueMesCells),
	                    2
	                )
	
	                for cellIndex in range(cellsToMap):
	
	                    cellRow = uniqueMesCells[cellIndex]
	
	                    cellId = safeUnicode(
	                        cellRow.get("SerialNo", "")
	                    ).strip()
	
	                    cellGrade = safeUnicode(
	                        cellRow.get("Grade", "")
	                    ).strip()
	
	                    plcCellInfo.append({
	                        "QualityStatus": bool(plcQualityStatus),
	                        "CellID": cellId,
	                        "CellGrade": cellGrade
	                    })
	
	                    logger.info(
	                        "Mapped unique MES GradeInfo to PLC CellInfo. "
	                        "Equipment=%s, PLCIndex=%s, CellID=%s, CellGrade=%s, "
	                        "MESQualityStatus=%s, PLCQualityStatus=%s"
	                        % (
	                            equipment,
	                            str(cellIndex),
	                            cellId,
	                            cellGrade,
	                            safeUnicode(mesQualityStatusValue),
	                            str(bool(plcQualityStatus))
	                        )
	                    )
	
	                ###################################################################
	                # PLC is fixed ARRAY[0..1]. Pad missing elements with correct types.
	                ###################################################################
	
	                while len(plcCellInfo) < 2:
	
	                    plcCellInfo.append({
	                        "QualityStatus": False,
	                        "CellID": "",
	                        "CellGrade": ""
	                    })
	
	                    logger.warn(
	                        "MES returned fewer than 2 unique cells. "
	                        "Padding PLC CellInfo[%s] with an empty AGCellInfo. "
	                        "Equipment=%s"
	                        % (
	                            str(len(plcCellInfo) - 1),
	                            equipment
	                        )
	                    )
	
	                ###############################################################
	                # Build exact PLC AGItemResponse structure
	                ###############################################################
	
	                plcResponseObject = {
	
	                    "ItemID": safeUnicode(
	                        mesMaterialInfo.get(
	                            "HuContainer",
	                            itemId
	                        )
	                    ).strip(),
	
	                    "ItemAuthorized": bool(
	                        itemAuthorized
	                    ),
	
	                    "CellInfo": plcCellInfo
	                }
	
	                logger.info(
	                    "Mapped Film Wrapping PLC AGItemResponse. "
	                    "EquipmentFolder=%s, ItemID=%s, ItemAuthorized=%s, "
	                    "CellInfoCount=%s, Response=%s"
	                    % (
	                        equipmentName,
	                        plcResponseObject.get("ItemID", ""),
	                        str(plcResponseObject.get("ItemAuthorized", False)),
	                        str(len(plcCellInfo)),
	                        system.util.jsonEncode(
	                            plcResponseObject
	                        )
	                    )
	                )
	
	                ###############################################################
	                # Success
	                ###############################################################
	
	                plcStatusCode = 200
	
	                responseHandshake = 2
	
	
	                responseTime = system.date.now()
	
	
	                ###############################################################
	                # Write response back to SAME triggering PLC
	                #
	                # IMPORTANT:
	                #
	                # Uses:
	                #
	                # providerPrefix + equipmentName
	                #
	                # NOT SenderFBS.
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
	                    "EquipmentFolder=%s, "
	                    "Equipment=%s, "
	                    "SenderFBS=%s, "
	                    "FeedingLocation=%s, "
	                    "ProviderPrefix=%s, "
	                    "TransactionId=%s, "
	                    "RequestAckNumber=%s, "
	                    "ResponseAckNumber=%s, "
	                    "StatusCode=%s, "
	                    "Handshake=%s, "
	                    "ItemAuthorized=%s, "
	                    "CellInfoCount=%s"
	                    % (
	                        equipmentName,
	                        equipment,
	                        senderFBS,
	                        feedingLocation,
	                        providerPrefix,
	                        transactionId,
	                        requestAckNumber,
	                        requestAckNumber,
	                        str(plcStatusCode),
	                        str(responseHandshake),
	                        str(itemAuthorized),
	                        str(len(plcCellInfo))
	                    )
	                )
	
	
	            ###################################################################
	            # Processing Failure
	            ###################################################################
	
	            except Exception as processingError:
	
	                logger.error(
	                    "S2M MaterialInfo processing failed. "
	                    "EquipmentFolder=%s, "
	                    "Equipment=%s, "
	                    "SenderFBS=%s, "
	                    "ProviderPrefix=%s, "
	                    "Error=%s"
	                    % (
	                        equipmentName,
	                        equipment,
	                        senderFBS,
	                        providerPrefix,
	                        str(
	                            processingError
	                        )
	                    )
	                )
	
	
	                plcResponseObject = createEmptyPLCResponse()
	
	
	                plcStatusCode = 410
	
	                responseHandshake = 2
	
	
	                failureResponseTime = system.date.now()
	
	
	                ###############################################################
	                # Write complete failure response
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
	                        "EquipmentFolder=%s, "
	                        "ProviderPrefix=%s, "
	                        "Error=%s"
	                        % (
	                            equipmentName,
	                            providerPrefix,
	                            str(
	                                failureWriteError
	                            )
	                        )
	                    )
	
	
	                    ###########################################################
	                    # Failure metadata fallback
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
	                            "EquipmentFolder=%s, "
	                            "ProviderPrefix=%s, "
	                            "Error=%s"
	                            % (
	                                equipmentName,
	                                providerPrefix,
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
	                "EquipmentFolder=%s. "
	                "MES call skipped."
	                % equipmentName
	            )
	
	
	            plcResponseObject = createEmptyPLCResponse()
	
	
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
	                    "EquipmentFolder=%s, "
	                    "Error=%s"
	                    % (
	                        equipmentName,
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
	                        "EquipmentFolder=%s, "
	                        "Error=%s"
	                        % (
	                            equipmentName,
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
	                "EquipmentFolder=%s, "
	                "Handshake=%s"
	                % (
	                    equipmentName,
	                    str(
	                        handshakeValue
	                    )
	                )
	            )
	
	
	            plcResponseObject = createEmptyPLCResponse()
	
	
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
	                    "EquipmentFolder=%s, "
	                    "Handshake=%s, "
	                    "Error=%s"
	                    % (
	                        equipmentName,
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
	                        "EquipmentFolder=%s, "
	                        "Error=%s"
	                        % (
	                            equipmentName,
	                            str(
	                                unsupportedMetadataError
	                            )
	                        )
	                    )
	
	
	###############################################################################
	# OUTER SCRIPT EXCEPTION
	###############################################################################
	
	except Exception as scriptError:
	
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