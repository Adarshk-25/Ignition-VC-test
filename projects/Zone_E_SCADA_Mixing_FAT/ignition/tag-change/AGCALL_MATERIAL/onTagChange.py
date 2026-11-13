def onTagChange(initialChange, newValue, previousValue, event, executionCount):
	# ============================================================
	# AG Calls Tag Change Script
	#
	# Handshake = 1:
	#   1. Sends hardcoded payload to MES.
	#   2. Reads MES response status.
	#   3. Writes MES status, response time and response data to PLC.
	#
	# MES success:
	#   StatusCode = 200
	#
	# MES failure / status 500 / exception:
	#   StatusCode = 500
	#
	# PLC tag types:
	#   Handshake     : Integer
	#   StatusCode    : Integer
	#   ResponseTime  : String
	#   ResponseData  : String
	# ============================================================
	
	import system
	import mesClient
	
	logger = system.util.getLogger("MES_MATERIAL_DOWNLOAD")
	
	try:
	    logger.info("AG Calls tag change script started")
	
	    # Ignore initial tag subscription
	    if initialChange:
	        logger.info("Initial tag change ignored")
	
	    else:
	        handshakeValue = int(newValue.value)
	
	        # PLC expects response time as String
	        responseTime = system.date.format(
	            system.date.now(),
	            "yyyy-MM-dd'T'HH:mm:ss.SSS"
	        )
	
	        # ====================================================
	        # PLC tag paths
	        # ====================================================
	
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
	
	        # Update this path with the actual IBS/ResponseData PLC tag.
	        # Currently using the SenderFBS tag supplied earlier.
	        responseDataPath = (
	            "[default]IN11_E305_PCE_POW22_Data/IN11_E305_PCE_POW22_IN11_E305_PCE_CMS21_AGAdmin_LastRecipeID"
	        )
	
	        # Default values
	        plcStatusCode = 500
	        plcResponseData = ""
	
	        # ====================================================
	        # Process valid handshake
	        # ====================================================
	
	        if handshakeValue == 1:
	            logger.info("Valid handshake received: 1")
	
	            try:
	                mesUrl = (
	                    "https://aprisomesdev.agratas.com/"
	                    "apriso/httpServices/operations/"
	                    "SCADAInboundExecution"
	                )
	
	                # --------------------------------------------
	                # Inner RequestJSON object
	                # --------------------------------------------
	
	                requestJsonObject = {
	                    "MaterialLoad": {
	                        "EmployeeNo": "EMP-8842",
	                        "EquipmentID": "MIXER-01",
	                        "OrderNo": "WO12345678890",
	                        "OperationNo": "0010",
	                        "MaterialInfos": [
	                            {
	                                "MaterialID": "POWDER-A1",
	                                "LotNo": "LOT-10025",
	                                "Location": "BIN-A",
	                                "UomCode": "KG",
	                                "Quantity": 50
	                            }
	                        ]
	                    }
	                }
	
	                # MES expects Inputs.RequestJSON as a String
	                requestJsonString = system.util.jsonEncode(
	                    requestJsonObject
	                )
	
	                # Outer payload remains a Python dictionary.
	                # mesClient performs jsonEncode(payload).
	                payload = {
	                    "Inputs": {
	                        "RequestJSON": requestJsonString
	                    },
	                    "ExecutionMode": 1,
	                    "JobPool": "",
	                    "Retries": 1,
	                    "SleepTime": 1000,
	                    "SynchronuousQueue": "",
	                    "Timeout": 5000
	                }
	
	                logger.info(
	                    "Calling MES with payload: %s"
	                    % system.util.jsonEncode(payload)
	                )
	
	                # --------------------------------------------
	                # MES API call
	                # --------------------------------------------
	
	                mesResponse = mesClient.postToMES(
	                    mesUrl,
	                    payload
	                )
	
	                logger.info(
	                    "MES response type: %s"
	                    % str(type(mesResponse))
	                )
	
	                logger.info(
	                    "MES raw response: %s"
	                    % str(mesResponse)
	                )
	
	                if mesResponse is None:
	                    raise Exception("MES returned an empty response")
	
	                # --------------------------------------------
	                # Convert MES response to PLC String
	                # --------------------------------------------
	
	                if isinstance(mesResponse, basestring):
	                    plcResponseData = mesResponse
	
	                    # Try to decode the response to inspect status
	                    try:
	                        decodedResponse = system.util.jsonDecode(
	                            mesResponse
	                        )
	                    except:
	                        decodedResponse = None
	
	                else:
	                    decodedResponse = mesResponse
	                    plcResponseData = system.util.jsonEncode(
	                        mesResponse
	                    )
	
	                # --------------------------------------------
	                # Determine MES status
	                # --------------------------------------------
	
	                mesStatusCode = 200
	                resultFlag = True
	
	                if isinstance(decodedResponse, dict):
	
	                    # Check common MES status-code fields
	                    if "StatusCode" in decodedResponse:
	                        mesStatusCode = int(
	                            decodedResponse["StatusCode"]
	                        )
	
	                    elif "statusCode" in decodedResponse:
	                        mesStatusCode = int(
	                            decodedResponse["statusCode"]
	                        )
	
	                    elif "HttpStatus" in decodedResponse:
	                        mesStatusCode = int(
	                            decodedResponse["HttpStatus"]
	                        )
	
	                    elif "httpStatus" in decodedResponse:
	                        mesStatusCode = int(
	                            decodedResponse["httpStatus"]
	                        )
	
	                    elif "status" in decodedResponse:
	                        try:
	                            mesStatusCode = int(
	                                decodedResponse["status"]
	                            )
	                        except:
	                            pass
	
	                    # Check common result flag fields
	                    if "ResultFlag" in decodedResponse:
	                        resultFlag = bool(
	                            decodedResponse["ResultFlag"]
	                        )
	
	                    elif "resultFlag" in decodedResponse:
	                        resultFlag = bool(
	                            decodedResponse["resultFlag"]
	                        )
	
	                    elif "Success" in decodedResponse:
	                        resultFlag = bool(
	                            decodedResponse["Success"]
	                        )
	
	                    elif "success" in decodedResponse:
	                        resultFlag = bool(
	                            decodedResponse["success"]
	                        )
	
	                # --------------------------------------------
	                # MES failure response
	                # --------------------------------------------
	
	                if mesStatusCode >= 400 or resultFlag is False:
	                    plcStatusCode = 500
	
	                    logger.error(
	                        "MES returned failure. "
	                        "MESStatusCode=%s, ResultFlag=%s, "
	                        "Response=%s"
	                        % (
	                            str(mesStatusCode),
	                            str(resultFlag),
	                            plcResponseData
	                        )
	                    )
	
	                # --------------------------------------------
	                # MES success response
	                # --------------------------------------------
	
	                else:
	                    plcStatusCode = 200
	
	                    logger.info(
	                        "MES call successful. "
	                        "MESStatusCode=%s, Response=%s"
	                        % (
	                            str(mesStatusCode),
	                            plcResponseData
	                        )
	                    )
	
	            except Exception as mesError:
	                # mesClient may raise an exception for HTTP 500
	                plcStatusCode = 500
	
	                plcResponseData = (
	                    "MES API Error: %s"
	                    % str(mesError)
	                )
	
	                logger.error(plcResponseData)
	
	        else:
	            # Invalid handshake
	            plcStatusCode = 500
	
	            plcResponseData = (
	                "Invalid handshake value: %s"
	                % str(handshakeValue)
	            )
	
	            logger.warn(plcResponseData)
	
	        # ====================================================
	        # Write MES result to PLC
	        # ====================================================
	
	        writePaths = [
	            statusCodePath,
	            responseTimePath,
	            responseDataPath
	        ]
	
	        writeValues = [
	            plcStatusCode,
	            responseTime,
	            plcResponseData
	        ]
	
	        writeResults = system.tag.writeBlocking(
	            writePaths,
	            writeValues
	        )
	
	        # Validate each PLC write
	        for index in range(len(writeResults)):
	
	            if writeResults[index].isGood():
	                logger.info(
	                    "PLC tag write successful. "
	                    "Path=%s, Value=%s, Quality=%s"
	                    % (
	                        writePaths[index],
	                        str(writeValues[index]),
	                        str(writeResults[index])
	                    )
	                )
	
	            else:
	                logger.error(
	                    "PLC tag write failed. "
	                    "Path=%s, Value=%s, Quality=%s"
	                    % (
	                        writePaths[index],
	                        str(writeValues[index]),
	                        str(writeResults[index])
	                    )
	                )
	
	        logger.info(
	            "AG Calls processing completed. "
	            "Handshake=%s, PLCStatusCode=%s, "
	            "ResponseTime=%s, ResponseData=%s"
	            % (
	                str(handshakeValue),
	                str(plcStatusCode),
	                responseTime,
	                plcResponseData
	            )
	        )
	
	except Exception as e:
	    logger.error(
	        "AG Calls tag change script error: %s"
	        % str(e)
	    )