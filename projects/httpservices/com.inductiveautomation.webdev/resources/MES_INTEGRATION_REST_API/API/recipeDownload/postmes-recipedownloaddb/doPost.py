def doPost(request, session):
################################################################################
# Code Description:
#   This script processes a RecipeDownload API request by validating the incoming
#   recipe payload, checking mandatory header fields, preventing duplicate recipe
#   headers and duplicate operation parameters, and storing valid recipe header
#   and parameter details into the MES database using a transaction.
#
#   Logic:
#   1) If WipOrderNo exists with Status = DOWNLOADED, return duplicate error.
#   2) If WipOrderNo exists with Status != DOWNLOADED, update existing header
#      and refresh parameter records.
#   3) If WipOrderNo does not exist, insert new header and parameter records.
#
# Version History:
# +-------+---------+------------+-------------+----------------------------------------+
# | Sl.No | Version | Fix        | Author      | Description                            |
# +-------+---------+------------+-------------+----------------------------------------+
# | 1     | 1.0.0   | 2026-05-29 | HariKrishna | Initial version history added          |
# | 2     | 1.0.1   | 2026-06-03 | HariKrishna | Update existing non-downloaded order   |
# +-------+---------+------------+-------------+----------------------------------------+
################################################################################
################################################################################
# Code Description:
#   RecipeDownload API processing script.
#   1) If WipOrderNo exists with DOWNLOADED status, duplicate error is returned.
#   2) If WipOrderNo exists with non-DOWNLOADED status, existing header is updated.
#   3) If WipOrderNo does not exist, new header is inserted.
#   4) If PLC ACK timeout occurs, status is updated to FAILED immediately.
################################################################################

	logger = system.util.getLogger("postmes-RecipeDownload")
	
	DB = "Dev_MSSQL_Server"
	
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
	    # Check Existing Header
	    # =====================================================
	    existingHeaderQuery = """
	        SELECT TOP 1 ID, Status
	        FROM MES_Recipe_Header
	        WHERE WipOrderNo = ?
	        ORDER BY ID DESC
	    """
	
	    existingHeader = system.db.runPrepQuery(existingHeaderQuery, [wipOrderNo], DB)
	
	    headerID = None
	    isUpdateMode = False
	
	    if len(existingHeader) > 0:
	        headerID = existingHeader[0]["ID"]
	        existingStatus = existingHeader[0]["Status"]
	
	        if existingStatus == "DOWNLOADED":
	            return {
	                "json": {
	                    "RecipeDownload": {
	                        "ResultFlag": False,
	                        "Message": "Duplicate WipOrderNo already exists with DOWNLOADED status: %s" % wipOrderNo
	                    }
	                }
	            }
	        else:
	            isUpdateMode = True
	            logger.info("Existing WipOrderNo found. HeaderID=%s, Status=%s. Updating existing record." % (headerID, existingStatus))
	
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
	    # Database Transaction - Insert / Update Header and Params
	    # =====================================================
	    tx = system.db.beginTransaction(database=DB, timeout=10000)
	
	    try:
	        if isUpdateMode:
	            updateHeaderQuery = """
	                UPDATE MES_Recipe_Header
	                SET
	                    Equipment = ?,
	                    ProductNo = ?,
	                    ProcessCode = ?,
	                    ProcessRevision = ?,
	                    OrderQuantity = ?,
	                    Status = ?
	                WHERE ID = ?
	            """
	
	            headerArgs = [
	                equipment,
	                productNo,
	                processCode,
	                processRevision,
	                orderQty,
	                "RECEIVED",
	                headerID
	            ]
	
	            system.db.runPrepUpdate(updateHeaderQuery, headerArgs, tx=tx)
	
	            deleteParamQuery = """
	                DELETE FROM MES_Recipe_Parameters
	                WHERE HeaderID = ?
	            """
	
	            system.db.runPrepUpdate(deleteParamQuery, [headerID], tx=tx)
	
	        else:
	            insertHeaderQuery = """
	                INSERT INTO MES_Recipe_Header
	                (
	                    WipOrderNo,
	                    Equipment,
	                    ProductNo,
	                    ProcessCode,
	                    ProcessRevision,
	                    OrderQuantity,
	                    Status
	                )
	                VALUES (?, ?, ?, ?, ?, ?, ?)
	            """
	
	            headerArgs = [
	                wipOrderNo,
	                equipment,
	                productNo,
	                processCode,
	                processRevision,
	                orderQty,
	                "RECEIVED"
	            ]
	
	            system.db.runPrepUpdate(insertHeaderQuery, headerArgs, tx=tx)
	
	            # Safer than SCOPE_IDENTITY()
	            getHeaderIDQuery = """
	                SELECT TOP 1 ID
	                FROM MES_Recipe_Header
	                WHERE WipOrderNo = ?
	                ORDER BY ID DESC
	            """
	
	            headerID = system.db.runScalarPrepQuery(getHeaderIDQuery, [wipOrderNo], tx=tx)
	
	        if headerID is None:
	            raise Exception("HeaderID not found after insert/update for WipOrderNo: %s" % wipOrderNo)
	
	        insertParamQuery = """
	            INSERT INTO MES_Recipe_Parameters
	            (
	                HeaderID,
	                OperationNo,
	                StepSequenceNo,
	                ParameterCode,
	                ParameterName,
	                TargetValue,
	                LSL,
	                USL,
	                UOM
	            )
	            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
	        """
	
	        for operation in operations:
	            operationNo = operation.get("OperationNo")
	
	            for param in operation.get("Parameters", []):
	                paramArgs = [
	                    headerID,
	                    operationNo,
	                    param.get("StepSequenceNo"),
	                    param.get("ParameterCode"),
	                    param.get("ParameterName"),
	                    param.get("TargetValue"),
	                    param.get("LowerSpecificationLimit"),
	                    param.get("UpperSpecificationLimit"),
	                    param.get("ParameterUOM")
	                ]
	
	                system.db.runPrepUpdate(insertParamQuery, paramArgs, tx=tx)
	
	        system.db.commitTransaction(tx)
	
	    except Exception as dbEx:
	        system.db.rollbackTransaction(tx)
	
	        logger.error("DB Save Failed: " + str(dbEx))
	
	        return {
	            "json": {
	                "RecipeDownload": {
	                    "ResultFlag": False,
	                    "Message": "Database save failed: " + str(dbEx)
	                }
	            }
	        }
	
	    finally:
	        system.db.closeTransaction(tx)
	
	    logger.info("Recipe saved into MSSQL. HeaderID = " + str(headerID))
	
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
	    time.sleep(1)
	
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
	
	    timeoutSeconds = 10
	    ackReceived = False
	
	    for i in range(timeoutSeconds):
	        ackValue = system.tag.readBlocking([ackTag])[0].value
	
	        if ackValue == True:
	            ackReceived = True
	            break
	
	        time.sleep(1)
	
	    # =====================================================
	    # Update Final Status
	    # =====================================================
	    if ackReceived:
	        finalStatus = "DOWNLOADED"
	    else:
	        finalStatus = "FAILED"
	
	    finalStatusUpdateQuery = """
	        UPDATE MES_Recipe_Header
	        SET Status = ?
	        WHERE ID = ?
	    """
	
	    rowsUpdated = system.db.runPrepUpdate(finalStatusUpdateQuery, [finalStatus, headerID], DB)
	
	    logger.info("Final status update rows affected = " + str(rowsUpdated))
	    logger.info("Final status updated to " + finalStatus + " for HeaderID = " + str(headerID))
	
	    # Optional: Reset trigger after processing
	    system.tag.writeBlocking(
	        ["[default]M2E_RecipeDownload/RecipeDownload/DownloadTrigger"],
	        [False]
	    )
	
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