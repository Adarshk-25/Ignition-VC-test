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
	#   8. Maps MES Authorization dynamically to PLC Authorized.
	#   9. Maps MES QualityStatus dynamically to PLC QualityStatus.
	#  10. Copies PLC RequestAckNumber to ResponseAckNumber when StatusCode is 200.
	#  11. Writes ResponseData, StatusCode, ResponseTime, ResponseAckNumber and
	#      Handshake to PLC tags.
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
	# PLC ResponseData / AGItemResponse:
	# {
	#     "ItemID": "HUCO-006",
	#     "BatchID": "",
	#     "ExpiryDate": "1900-01-01T00:00:00Z",
	#     "QualityStatus": "Fail",
	#     "Authorized": false
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
	# Helper: Convert value to Boolean
	###############################################################################
	
	def convertToBoolean(value):
	    """
	    Converts MES Boolean, number or string values into a Python Boolean.
	    """
	
	    if value is None:
	        return False
	
	    if isinstance(value, basestring):
	        normalizedValue = unicode(
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
	# Helper: Create empty PLC response
	###############################################################################
	
	def createEmptyPLCResponse():
	    """
	    Returns the default AGItemResponse structure used for technical failures.
	    """
	
	    return {
	        "ItemID": "",
	        "BatchID": "",
	        "ExpiryDate": "",
	        "QualityStatus": "",
	        "Authorized": False
	    }
	
	
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
	    Writes the response values to PLC tags.
	
	    ResponseAckNumber is populated with RequestAckNumber only for a successful
	    StatusCode 200 response. For failure responses, an empty value is written.
	    """
	
	    responseDataJson = system.util.jsonEncode(
	        responseData
	    )
	
	    if int(statusCode) == 200:
	        finalResponseAckNumber = responseAckNumber
	    else:
	        finalResponseAckNumber = ""
	
	    if finalResponseAckNumber is None:
	        finalResponseAckNumber = ""
	
	    finalResponseAckNumber = unicode(
	        finalResponseAckNumber
	    ).strip()
	
	    writePaths = [
	        responseDataPath,
	        statusCodePath,
	        responseTimePath,
	        responseAckNumberPath,
	        handshakePath
	    ]
	
	    writeValues = [
	        responseDataJson,
	        int(statusCode),
	        unicode(responseTime),
	        finalResponseAckNumber,
	        int(handshake)
	    ]
	
	    logger.info(
	        "Writing PLC response. "
	        "ResponseData=%s, StatusCode=%s, ResponseTime=%s, "
	        "ResponseAckNumber=%s, Handshake=%s"
	        % (
	            responseDataJson,
	            str(statusCode),
	            unicode(responseTime),
	            finalResponseAckNumber,
	            str(handshake)
	        )
	    )
	
	    writeResults = system.tag.writeBlocking(
	        writePaths,
	        writeValues
	    )
	
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
	
	    return writeResults
	
	
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
	        # Step 2: Read current handshake value
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
	
	        mesUrl = "http://WIN-GC9744IHT64/apriso/httpServices/operations/AGR_PRD_S2M_MaterialInfo"
	
	        interfaceName = "S2M.MaterialInfo"
	        sourceSystem = "SCADA"
	        targetSystem = "MES"
	
	        equipment = "EQ_Mixing"
	        feedingLocation = "EQ_Mixing"
	        employeeNo = "657681"
	
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
	            "AGCalls_AGSetItemInfo_ResponseTime"
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
	
	        if handshakeValue == 2:
	            logger.info(
	                "Handshake is 2. Request already processed. "
	                "No MES call or PLC write will be performed."
	            )
	
	        #######################################################################
	        # Step 6: Handshake = 1 means process request
	        #######################################################################
	
	        elif handshakeValue == 1:
	            logger.info(
	                "Valid request handshake received"
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
	
	                plcRequestString = unicode(
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
	
	                requestAckNumber = unicode(
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
	
	                itemId = unicode(
	                    plcRequestObject.get(
	                        "ItemID",
	                        ""
	                    )
	                ).strip()
	
	                recipeId = unicode(
	                    plcRequestObject.get(
	                        "RecipeId",
	                        ""
	                    )
	                ).strip()
	
	                workOrderId = unicode(
	                    plcRequestObject.get(
	                        "WorkOrderID",
	                        ""
	                    )
	                ).strip()
	
	                ################################################################
	                # Validate required fields
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
	                            unicode(mesResponse)
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
	                    responseJsonString = unicode(
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
	                # Read Authorization dynamically from MES
	                ################################################################
	
	                authorized = convertToBoolean(
	                    mesMaterialInfo.get(
	                        "Authorization",
	                        False
	                    )
	                )
	
	                ################################################################
	                # Read QualityStatus dynamically from MES
	                ################################################################
	
	                qualityStatusValue = mesMaterialInfo.get(
	                    "QualityStatus",
	                    ""
	                )
	
	                if qualityStatusValue is None:
	                    qualityStatus = ""
	                else:
	                    qualityStatus = unicode(
	                        qualityStatusValue
	                    ).strip()
	
	                logger.info(
	                    "MES business values mapped. "
	                    "Authorization=%s, QualityStatus=%s"
	                    % (
	                        str(authorized),
	                        qualityStatus
	                    )
	                )
	
	                ################################################################
	                # Build Siemens AGItemResponse
	                ################################################################
	
	                plcResponseObject = {
	                    "ItemID": unicode(
	                        mesMaterialInfo.get(
	                            "HuContainer",
	                            itemId
	                        )
	                    ).strip(),
	
	                    "BatchID": unicode(
	                        mesMaterialInfo.get(
	                            "BatchID",
	                            ""
	                        )
	                    ).strip(),
	
	                    "ExpiryDate": unicode(
	                        mesMaterialInfo.get(
	                            "ExpiryDate",
	                            ""
	                        )
	                    ).strip(),
	
	                    "QualityStatus": qualityStatus,
	
	                    "Authorized": bool(
	                        authorized
	                    )
	                }
	
	                logger.info(
	                    "Mapped AGItemResponse: %s"
	                    % system.util.jsonEncode(
	                        plcResponseObject
	                    )
	                )
	
	                ################################################################
	                # MES communication completed successfully
	                ################################################################
	
	                plcStatusCode = 200
	                responseHandshake = 2
	
	                ################################################################
	                # Write successful response to PLC
	                #
	                # RequestAckNumber is copied into ResponseAckNumber because
	                # StatusCode is 200.
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
	                    "ResponseAckNumber=%s, StatusCode=%s, Handshake=%s"
	                    % (
	                        transactionId,
	                        requestAckNumber,
	                        requestAckNumber,
	                        str(plcStatusCode),
	                        str(responseHandshake)
	                    )
	                )
	
	            except Exception as processingError:
	                logger.error(
	                    "S2M MaterialInfo processing failed: %s"
	                    % str(processingError)
	                )
	
	                ################################################################
	                # Build PLC technical failure response
	                ################################################################
	
	                plcResponseObject = createEmptyPLCResponse()
	
	                plcStatusCode = 500
	                responseHandshake = 2
	
	                failureResponseTime = system.date.format(
	                    system.date.now(),
	                    "yyyy-MM-dd'T'HH:mm:ss.SSS"
	                )
	
	                ################################################################
	                # Write failure response to PLC
	                #
	                # ResponseAckNumber is cleared because StatusCode is not 200.
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
	                        "Failed to write PLC failure response: %s"
	                        % str(failureWriteError)
	                    )
	
	        #######################################################################
	        # Step 7: Handshake = 3
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
	
	            writePLCResponse(
	                responseDataPath,
	                statusCodePath,
	                responseTimePath,
	                responseAckNumberPath,
	                handshakePath,
	                plcResponseObject,
	                410,
	                responseTime,
	                "",
	                3
	            )
	
	        #######################################################################
	        # Step 8: Unsupported handshake
	        #######################################################################
	
	        else:
	            logger.warn(
	                "Unsupported handshake value received: %s"
	                % str(handshakeValue)
	            )
	
	            plcResponseObject = createEmptyPLCResponse()
	
	            responseTime = system.date.format(
	                system.date.now(),
	                "yyyy-MM-dd'T'HH:mm:ss.SSS"
	            )
	
	            writePLCResponse(
	                responseDataPath,
	                statusCodePath,
	                responseTimePath,
	                responseAckNumberPath,
	                handshakePath,
	                plcResponseObject,
	                410,
	                responseTime,
	                "",
	                handshakeValue
	            )
	
	
	except Exception as scriptError:
	    logger.error(
	        "S2M MaterialInfo tag change script failed: %s"
	        % str(scriptError)
	    )