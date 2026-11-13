def doPost(request, session):
################################################################################
# Code Description:
#   This script processes a RecipeDownload API request by validating the incoming
#   recipe payload, checking mandatory header fields, preventing duplicate recipe
#   headers and duplicate operation parameters, and storing valid recipe header
#   and parameter details into the MES database using a transaction.
#
#   Logic:
#   1) If WipOrderNo exists with Status = DOWNLOADED, No validation duplicate error.
#   2) If WipOrderNo exists with Status != DOWNLOADED, No DB Validation.
#   3) If ACK updated with 700 milli seconds.
#
# Version History:
# +-------+---------+------------+-------------+----------------------------------------+
# | Sl.No | Version | Fix        | Author      | Description                            |
# +-------+---------+------------+-------------+----------------------------------------+
# | 1     | 1.0.0   | 2026-06-04 | HariKrishna | Initial version history added          |
# | 2     | 1.0.1   | 2026-06-07 | HariKrishna | Update ACK with 700ms   |
# +-------+---------+------------+-------------+----------------------------------------+
################################################################################


	logger = system.util.getLogger("postmes-RecipeDownload")
	
	#DB = "MESDEV"
	
	try:
	    payload = request["data"]
	
	    if "RecipeDownload" not in payload:
	        return {
	            "json": {
	                "RecipeDownload": {
	                    "ResultFlag": False,
	                    "Message": "Invalid Payload: RecipeDownload missing"
	                }
	            }
	        }
	
	    recipe = payload["RecipeDownload"]
	    logger.info("Received Recipe Download Request")
	
	    # =====================================================
	    # Extract Header
	    # =====================================================
	    wipOrderNo = recipe.get("WipOrderNo")
	    equipment = recipe.get("Equipment")
	    productNo = recipe.get("ProductNo")
	    processCode = recipe.get("ProcessCode")
	    processRevision = recipe.get("ProcessRevision")
	    orderQty = recipe.get("OrderQuantity")
	    operations = recipe.get("Operations", [])
	
	    # =====================================================
	    # Mandatory Field Validation
	    # =====================================================
	    requiredFields = {
	        "WipOrderNo": wipOrderNo,
	        "Equipment": equipment,
	        "ProductNo": productNo,
	        "ProcessCode": processCode,
	        "ProcessRevision": processRevision,
	        "OrderQuantity": orderQty
	    }
	
	    missingFields = []
	    for key, value in requiredFields.items():
	        if value is None or str(value).strip() == "":
	            missingFields.append(key)
	
	    if len(missingFields) > 0:
	        return {
	            "json": {
	                "RecipeDownload": {
	                    "ResultFlag": False,
	                    "Message": "Missing mandatory field(s): " + ", ".join(missingFields)
	                }
	            }
	        }
	
	    
	    # =====================================================
	    # Duplicate Parameter Validation inside Payload
	    # =====================================================
	    seenParams = {}
	
	    for operation in operations:
	        operationNo = operation.get("OperationNo")
	
	        if operationNo is None or str(operationNo).strip() == "":
	            return {
	                "json": {
	                    "RecipeDownload": {
	                        "ResultFlag": False,
	                        "Message": "OperationNo is missing"
	                    }
	                }
	            }
	
	        for param in operation.get("Parameters", []):
	            stepSeq = param.get("StepSequenceNo")
	            paramCode = param.get("ParameterCode")
	
	            if stepSeq is None or str(stepSeq).strip() == "":
	                return {
	                    "json": {
	                        "RecipeDownload": {
	                            "ResultFlag": False,
	                            "Message": "StepSequenceNo is missing for OperationNo %s" % operationNo
	                        }
	                    }
	                }
	
	            if paramCode is None or str(paramCode).strip() == "":
	                return {
	                    "json": {
	                        "RecipeDownload": {
	                            "ResultFlag": False,
	                            "Message": "ParameterCode is missing for OperationNo %s" % operationNo
	                        }
	                    }
	                }
	
	            key = str(operationNo) + "|" + str(stepSeq) + "|" + str(paramCode)
	
	            if key in seenParams:
	                return {
	                    "json": {
	                        "RecipeDownload": {
	                            "ResultFlag": False,
	                            "Message": "Duplicate parameter found in payload: OperationNo=%s, StepSequenceNo=%s, ParameterCode=%s" %
	                                       (operationNo, stepSeq, paramCode)
	                        }
	                    }
	                }
	
	            seenParams[key] = True
	
	    
	
	    
	
	    # =====================================================
	    # Prepare Recipe Values
	    # =====================================================
	    tempSet = 0
	    pressureSet = 0
	
	    for operation in operations:
	        for param in operation.get("Parameters", []):
	            if param.get("ParameterCode") == "TEMP_SET":
	                tempSet = param.get("TargetValue")
	            elif param.get("ParameterCode") == "PRESS_SET":
	                pressureSet = param.get("TargetValue")
	
	    # =====================================================
	    # Reset ACK and Trigger before new download
	    # =====================================================
	    resetTagPaths = [
	        "[default]M2E_RecipeDownload/RecipeDownload/DownloadTrigger",
	        "[default]M2E_RecipeDownload/RecipeDownload/Ack"
	    ]
	
	    resetValues = [
	        False,
	        False
	    ]
	
	    system.tag.writeBlocking(resetTagPaths, resetValues)
	
	    import time
	    #time.sleep(1)
	
	    # =====================================================
	    # Write Recipe Values to Kepware OPC Tags
	    # =====================================================
	    tagPaths = [
	        "[default]M2E_RecipeDownload/RecipeDownload/WipOrderNo",
	        "[default]M2E_RecipeDownload/RecipeDownload/TempSet",
	        "[default]M2E_RecipeDownload/RecipeDownload/PressureSet"
	    ]
	
	    values = [
	        wipOrderNo,
	        tempSet,
	        pressureSet
	    ]
	
	    logger.info("Tag Paths: " + str(tagPaths))
	    logger.info("Tag Values: " + str(values))
	
	    writeResults = system.tag.writeBlocking(tagPaths, values)
	    logger.info("Recipe Values Written to OPC Tags: " + str(writeResults))
	
	    # Trigger download after values are written
	    system.tag.writeBlocking(
	        ["[default]M2E_RecipeDownload/RecipeDownload/DownloadTrigger"],
	        [True]
	    )
	
	    logger.info("DownloadTrigger set to TRUE")
	
	    # =====================================================
	    # Wait for PLC ACK
	    # =====================================================
	    ackTag = "[default]M2E_RecipeDownload/RecipeDownload/Ack"
	
	    timeoutSeconds = 2
	    ackReceived = False
	
	    for i in range(timeoutSeconds):
	        ackValue = system.tag.readBlocking([ackTag])[0].value
	
	        if ackValue == True:
	            ackReceived = True
	            break
	
	        #time.sleep(1)
	
	    
	
	    # Optional: Reset trigger after processing
	    
	    if ackReceived:
	        return {
	            "json": {
	                "RecipeDownload": {
	                    "ResultFlag": True,
	                    "Message": "Recipe downloaded and acknowledged by Equipment %s successfully." % equipment
	                }
	            }
	        }
	    else:
	        return {
	            "json": {
	                "RecipeDownload": {
	                    "ResultFlag": False,
	                    "Message": "PLC ACK Timeout. Status updated to FAILED for WipOrderNo %s." % wipOrderNo
	                }
	            }
	        }
	
	except Exception as e:
	    logger.error("Recipe Download Error: " + str(e))
	
	    return {
	        "json": {
	            "RecipeDownload": {
	                "ResultFlag": False,
	                "Message": str(e)
	            }
	        }
	    }