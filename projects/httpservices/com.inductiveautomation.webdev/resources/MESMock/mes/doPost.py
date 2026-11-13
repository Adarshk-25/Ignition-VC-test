def doPost(request, session):
	# =====================================================================
	# MES MOCK SERVER
	# Ignition WebDev Python Resource - doPost
	#
	# PURPOSE:
	#   Portable MES mock endpoint for SCADA -> MES (S2M) interface testing.
	#   Resolves an interface category, builds a standard MES response, and
	#   returns the full MessageHeader + business body in ResponseJSON.
	#
	# WEBDEV URL:
	#   /system/webdev/httpservices/MESMock/mes
	#
	# CATEGORY URL:
	#   /system/webdev/httpservices/MESMock/mes?category=<InterfaceName>
	#
	# EXAMPLES:
	#   /system/webdev/httpservices/MESMock/mes?category=S2M.MaterialInfo
	#   /system/webdev/httpservices/MESMock/mes?category=S2M.Serialnbound
	#
	# CATEGORY RESOLUTION PRIORITY:
	#   1. URL query parameter ?category=
	#   2. Inputs.RequestJSON.MessageHeader.InterfaceName
	#   3. Inputs.MessageHeader.InterfaceName
	#
	# SUPPORTED CATEGORIES:
	#   01. S2M.FinalPackaging
	#   02. S2M.MaterialInfo
	#   03. S2M.UserLogin
	#   04. S2M.UserLogout
	#   05. S2M.OperationResult
	#   06. S2M.MachineAlarm
	#   07. S2M.MachineState
	#   08. S2M.UnlinkData
	#   09. S2M.ProductionOrderStart
	#   10. S2M.ProductionOrderState
	#   11. S2M.UnloadingMaterial
	#   12. S2M.MESHeartbeat (legacy alias S2M.MESHbit)
	#   13. S2M.ScrapReport
	#   14. S2M.CreateSerial
	#   15. S2M.Serialnbound
	#
	# SUPPORTED REQUEST ENVELOPES:
	#
	#   A) Direct Inputs
	#      {"Inputs":{"MessageHeader":{...},"<BusinessBody>":{...}}}
	#
	#   B) RequestJSON wrapper
	#      {"Inputs":{"RequestJSON":{"MessageHeader":{...},"<BusinessBody>":{...}}}}
	#
	# S2M.Serialnbound:
	#   Request/response business body name = SerialInbound
	#
	# WEBDEV RESPONSE FORMAT:
	#   {
	#       "Outputs": {
	#           "__Routing__": true,
	#           "ResponseJSON": "<FULL MES RESPONSE AS JSON STRING>"
	#       }
	#   }
	#
	# IMPORTANT:
	#   - ResponseJSON is intentionally a STRING.
	#   - MessageHeader is first, BusinessBody is second inside ResponseJSON.
	#   - Response direction is MES -> SCADA.
	#   - TransactionId and EventTimestamp are preserved when supplied.
	#   - Do NOT use LinkedHashMap.
	# =====================================================================
	
	import system
	
	
	logger = system.util.getLogger(
	    "MES_MOCK_SERVER"
	)
	
	
	logger.info(
	    "============================================================"
	)
	
	logger.info(
	    "MES MOCK doPost EXECUTED"
	)
	
	
	try:
	
	    # =================================================================
	    # UTC TIMESTAMP
	    # =================================================================
	
	    def utcTimestamp():
	
	        from java.text import SimpleDateFormat
	        from java.util import TimeZone
	
	        formatter = SimpleDateFormat(
	            "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"
	        )
	
	        formatter.setTimeZone(
	            TimeZone.getTimeZone("UTC")
	        )
	
	        return formatter.format(
	            system.date.now()
	        )
	
	
	    # =================================================================
	    # QUERY PARAMETER
	    # =================================================================
	
	    def getQueryParameter(
	        parameterName
	    ):
	
	        try:
	
	            params = request.get(
	                "params",
	                {}
	            )
	
	            value = params.get(
	                parameterName
	            )
	
	            if value is not None:
	
	                return str(
	                    value
	                ).strip()
	
	        except Exception, ex:
	
	            logger.warn(
	                "Unable to read request params. Error=%s"
	                % str(ex)
	            )
	
	
	        # -------------------------------------------------------------
	        # Servlet fallback
	        # -------------------------------------------------------------
	
	        try:
	
	            servletRequest = request.get(
	                "servletRequest"
	            )
	
	            if servletRequest is not None:
	
	                value = servletRequest.getParameter(
	                    parameterName
	                )
	
	                if value is not None:
	
	                    return str(
	                        value
	                    ).strip()
	
	        except Exception, ex:
	
	            logger.warn(
	                "Servlet parameter read failed. Error=%s"
	                % str(ex)
	            )
	
	
	        return None
	
	
	    # =================================================================
	    # READ REQUEST PAYLOAD
	    # =================================================================
	
	    def getPayload():
	
	        try:
	
	            logger.info(
	                "Request keys=%s"
	                % str(
	                    request.keys()
	                )
	            )
	
	        except:
	            pass
	
	
	        # -------------------------------------------------------------
	        # POST DATA
	        # -------------------------------------------------------------
	
	        try:
	
	            postData = request.get(
	                "postData"
	            )
	
	
	            logger.info(
	                "postData type=%s"
	                % str(
	                    type(postData)
	                )
	            )
	
	
	            logger.info(
	                "postData=%s"
	                % str(
	                    postData
	                )
	            )
	
	
	            if postData is not None:
	
	                # -----------------------------------------------------
	                # Already decoded JSON
	                # -----------------------------------------------------
	
	                if isinstance(
	                    postData,
	                    dict
	                ):
	
	                    return postData
	
	
	                # -----------------------------------------------------
	                # JSON String
	                # -----------------------------------------------------
	
	                text = str(
	                    postData
	                ).strip()
	
	
	                if text:
	
	                    return system.util.jsonDecode(
	                        text
	                    )
	
	
	        except Exception, ex:
	
	            logger.warn(
	                "postData read/decode failed. Error=%s"
	                % str(ex)
	            )
	
	
	        # -------------------------------------------------------------
	        # request["data"] fallback
	        # -------------------------------------------------------------
	
	        try:
	
	            data = request.get(
	                "data"
	            )
	
	
	            if data is not None:
	
	                logger.info(
	                    "request[data] type=%s"
	                    % str(
	                        type(data)
	                    )
	                )
	
	
	                if isinstance(
	                    data,
	                    dict
	                ):
	
	                    return data
	
	
	                text = str(
	                    data
	                ).strip()
	
	
	                if text:
	
	                    return system.util.jsonDecode(
	                        text
	                    )
	
	
	        except Exception, ex:
	
	            logger.warn(
	                "request[data] read/decode failed. Error=%s"
	                % str(ex)
	            )
	
	
	        return {}
	
	
	    # =================================================================
	    # GET INPUTS ROOT / REQUESTJSON CONTENT
	    #
	    # Normalizes both supported envelopes so downstream code always reads
	    # MessageHeader and BusinessBody from the same dictionary.
	    # =================================================================
	
	    def getInputs(
	        payload
	    ):
	
	        try:
	
	            inputs = payload.get(
	                "Inputs"
	            )
	
	            if inputs is None:
	                return {}
	
	            # -------------------------------------------------------------
	            # Inputs.RequestJSON wrapper
	            # -------------------------------------------------------------
	
	            try:
	
	                requestJson = inputs.get(
	                    "RequestJSON"
	                )
	
	                if requestJson is not None:
	
	                    if isinstance(
	                        requestJson,
	                        dict
	                    ):
	
	                        return requestJson
	
	                    requestJsonText = str(
	                        requestJson
	                    ).strip()
	
	                    if requestJsonText:
	
	                        decodedRequestJson = system.util.jsonDecode(
	                            requestJsonText
	                        )
	
	                        if isinstance(
	                            decodedRequestJson,
	                            dict
	                        ):
	
	                            return decodedRequestJson
	
	            except Exception, ex:
	
	                logger.warn(
	                    "Unable to decode Inputs.RequestJSON. Error=%s"
	                    % str(ex)
	                )
	
	            # -------------------------------------------------------------
	            # Standard Inputs.MessageHeader + BusinessBody
	            # -------------------------------------------------------------
	
	            return inputs
	
	        except Exception, ex:
	
	            logger.warn(
	                "Unable to resolve Inputs. Error=%s"
	                % str(ex)
	            )
	
	        return {}
	
	
	    # =================================================================
	    # GET MESSAGE HEADER
	    # =================================================================
	
	    def getMessageHeader(
	        inputs
	    ):
	
	        try:
	
	            header = inputs.get(
	                "MessageHeader"
	            )
	
	            if header is not None:
	
	                return header
	
	        except:
	            pass
	
	
	        # -------------------------------------------------------------
	        # Lowercase fallback
	        # -------------------------------------------------------------
	
	        try:
	
	            header = inputs.get(
	                "messageHeader"
	            )
	
	            if header is not None:
	
	                return header
	
	        except:
	            pass
	
	
	        return {}
	
	
	    # =================================================================
	    # TRANSACTION ID
	    # =================================================================
	
	    def getTransactionId(
	        header
	    ):
	
	        fieldNames = [
	
	            "TransactionId",
	
	            "TransactionID",
	
	            "TrasanactionId",
	
	            "TransanctionID"
	        ]
	
	
	        for fieldName in fieldNames:
	
	            try:
	
	                value = header.get(
	                    fieldName
	                )
	
	                if value is not None:
	
	                    return str(
	                        value
	                    )
	
	            except:
	                pass
	
	
	        return ""
	
	
	    # =================================================================
	    # GET BUSINESS BODY
	    #
	    # Business body is ALWAYS expected below Inputs.
	    #
	    # Inputs
	    #   |
	    #   +-- MessageHeader
	    #   |
	    #   +-- MaterialInfo
	    #
	    # =================================================================
	
	    def getBusinessBody(
	        inputs,
	        bodyName
	    ):
	
	        try:
	
	            body = inputs.get(
	                bodyName
	            )
	
	            if body is not None:
	
	                return body
	
	        except:
	            pass
	
	
	        return {}
	
	
	    # =================================================================
	    # BUILD MES RESPONSE HEADER
	    #
	    # Response:
	    #
	    # SCADA -> MES request
	    #
	    # becomes
	    #
	    # MES -> SCADA response
	    #
	    # Equipment is copied from request.
	    #
	    # EventTimestamp:
	    #   Preserve incoming timestamp when available.
	    #
	    # =================================================================
	
	    def buildResponseHeader(
	        category,
	        requestHeader,
	        transactionId
	    ):
	
	        equipment = ""
	
	        eventTimestamp = ""
	
	
	        try:
	
	            equipment = requestHeader.get(
	                "Equipment",
	                ""
	            )
	
	        except:
	            equipment = ""
	
	
	        try:
	
	            eventTimestamp = requestHeader.get(
	                "EventTimestamp",
	                ""
	            )
	
	        except:
	            eventTimestamp = ""
	
	
	        if not eventTimestamp:
	
	            eventTimestamp = utcTimestamp()
	
	
	        responseHeader = {
	
	            "Equipment":
	                equipment,
	
	            "InterfaceName":
	                category,
	
	            "TransactionId":
	                transactionId,
	
	            "SourceSystem":
	                "MES",
	
	            "TargetSystem":
	                "SCADA",
	
	            "EventTimestamp":
	                eventTimestamp
	        }
	
	
	        return responseHeader
	
	
	    # =================================================================
	    # BUILD INNER MES RESPONSE JSON
	    #
	    # Result:
	    #
	    # {
	    #   "MessageHeader": {...},
	    #   "MaterialInfo": {...}
	    # }
	    #
	    #
	    # We manually build the OUTER order so MessageHeader appears first.
	    #
	    # =================================================================
	
	    def buildMESResponseJSON(
	        responseHeader,
	        bodyName,
	        responseBody
	    ):
	
	        headerJson = system.util.jsonEncode(
	            responseHeader
	        )
	
	
	        bodyJson = system.util.jsonEncode(
	            responseBody
	        )
	
	
	        mesResponseJson = (
	
	            "{"
	
	            +
	
	            "\"MessageHeader\":"
	
	            +
	
	            headerJson
	
	            +
	
	            ","
	
	            +
	
	            "\""
	
	            +
	
	            str(
	                bodyName
	            )
	
	            +
	
	            "\":"
	
	            +
	
	            bodyJson
	
	            +
	
	            "}"
	        )
	
	
	        return mesResponseJson
	
	
	    # =================================================================
	    # BUILD FINAL API RESPONSE
	    #
	    # IMPORTANT:
	    #
	    # ResponseJSON must be a STRING.
	    #
	    # {
	    #     "Outputs": {
	    #         "__Routing__": true,
	    #         "ResponseJSON":
	    #             "{\"MessageHeader\":{...},\"MaterialInfo\":{...}}"
	    #     }
	    # }
	    #
	    # =================================================================
	
	    def buildFinalApiResponse(
	        mesResponseJson
	    ):
	
	        outputs = {
	
	            "__Routing__":
	                True,
	
	            "ResponseJSON":
	                mesResponseJson
	        }
	
	
	        finalResponse = {
	
	            "Outputs":
	                outputs
	        }
	
	
	        return finalResponse
	
	
	    # =================================================================
	    # READ REQUEST
	    # =================================================================
	
	    payload = getPayload()
	
	
	    logger.info(
	        "Raw Request Payload=%s"
	        % system.util.jsonEncode(
	            payload
	        )
	    )
	
	
	    # =================================================================
	    # GET INPUTS
	    # =================================================================
	
	    inputs = getInputs(
	        payload
	    )
	
	
	    logger.info(
	        "Inputs=%s"
	        % system.util.jsonEncode(
	            inputs
	        )
	    )
	
	
	    # =================================================================
	    # GET MESSAGE HEADER
	    # =================================================================
	
	    requestHeader = getMessageHeader(
	        inputs
	    )
	
	
	    logger.info(
	        "Request MessageHeader=%s"
	        % system.util.jsonEncode(
	            requestHeader
	        )
	    )
	
	
	    # =================================================================
	    # GET TRANSACTION ID
	    # =================================================================
	
	    transactionId = getTransactionId(
	        requestHeader
	    )
	
	
	    logger.info(
	        "TransactionId=%s"
	        % transactionId
	    )
	
	
	    # =================================================================
	    # GET CATEGORY
	    #
	    # Priority:
	    #
	    # 1. URL ?category=
	    # 2. Inputs.MessageHeader.InterfaceName
	    #
	    # This allows BOTH:
	    #
	    # ?category=S2M.MaterialInfo
	    #
	    # and automatically using InterfaceName.
	    #
	    # =================================================================
	
	    category = getQueryParameter(
	        "category"
	    )
	
	
	    if category is None or category == "":
	
	        try:
	
	            category = requestHeader.get(
	                "InterfaceName",
	                ""
	            )
	
	        except:
	
	            category = ""
	
	
	    logger.info(
	        "Resolved Category=%s"
	        % str(category)
	    )
	
	
	    # =================================================================
	    # BUILD COMMON RESPONSE HEADER
	    # =================================================================
	
	    responseHeader = buildResponseHeader(
	        category,
	        requestHeader,
	        transactionId
	    )
	
	
	    # =================================================================
	    #
	    # 1. S2M.FinalPackaging
	    #
	    # =================================================================
	
	    if category == "S2M.FinalPackaging":
	
	        logger.info(
	            "Processing S2M.FinalPackaging"
	        )
	
	
	        cellPackageInfo = getBusinessBody(
	            inputs,
	            "CellPackageInfo"
	        )
	
	
	        palletNo = (
	
	            cellPackageInfo.get(
	                "PalletNo"
	            )
	
	            or
	
	            cellPackageInfo.get(
	                "PalletID"
	            )
	
	            or
	
	            "P1-000"
	        )
	
	
	        trayNo = (
	
	            cellPackageInfo.get(
	                "TrayNo"
	            )
	
	            or
	
	            cellPackageInfo.get(
	                "TrayID"
	            )
	
	            or
	
	            ""
	        )
	
	
	        responseBody = {
	
	            "PalletNo":
	                palletNo,
	
	            "TrayNo":
	                trayNo,
	
	            "ResultFlag":
	                True,
	
	            "Message":
	                "Final packaging confirmed successfully - MES MOCK"
	        }
	
	
	        bodyName = "CellPackageInfo"
	
	
	    # =================================================================
	    #
	    # 2. S2M.MaterialInfo
	    #
	    # =================================================================
	
	    elif category == "S2M.MaterialInfo":
	
	        logger.info(
	            "Processing S2M.MaterialInfo"
	        )
	
	
	        material = getBusinessBody(
	            inputs,
	            "MaterialInfo"
	        )
	
	
	        equipment = ""
	
	
	        try:
	
	            equipment = requestHeader.get(
	                "Equipment",
	                ""
	            )
	
	        except:
	            pass
	
	
	        if not equipment:
	
	            equipment = material.get(
	                "FeedingLocation",
	                ""
	            )
	
	
	        # -------------------------------------------------------------
	        # MaterialInfo MES mock response
	        #
	        # Adjust these values later if different MES test scenarios
	        # are required.
	        # -------------------------------------------------------------
	
	        responseBody = {
	
	            "HuContainer":
	                material.get(
	                    "HuContainer",
	                    ""
	                ),
	
	            "RecipeID":
	                material.get(
	                    "RecipeID",
	                    ""
	                ),
	            "WorkOrder":
	                material.get(
	                    "WorkOrder",
	                    ""
	                ),
	
	            "BatchID":
	                material.get(
	                    "WorkOrder",
	                    ""
	                ),
	
	            "ExpiryDate":
	                "1900-01-01T00:00:00Z",
	
	            "Authorization":
	                False,
	
	            "QualityStatus":
	                "Fail"
	        }
	
	
	        bodyName = "MaterialInfo"
	
	
	    # =================================================================
	    #
	    # 3. S2M.UserLogin
	    #
	    # =================================================================
	
	    elif category == "S2M.UserLogin":
	
	        logger.info(
	            "Processing S2M.UserLogin"
	        )
	
	
	        userLogin = getBusinessBody(
	            inputs,
	            "UserLogin"
	        )
	
	
	        responseBody = {
	
	            "ResultFlag":
	                True,
	
	            "Message":
	                "Login and Skill Validation Successful.",
	
	            "EmployeeNo":
	                userLogin.get(
	                    "EmployeeNo",
	                    ""
	                )
	        }
	
	
	        bodyName = "UserLogin"
	
	
	    # =================================================================
	    #
	    # 4. S2M.UserLogout
	    #
	    # =================================================================
	
	    elif category == "S2M.UserLogout":
	
	        logger.info(
	            "Processing S2M.UserLogout"
	        )
	
	
	        responseBody = {
	
	            "ResultFlag":
	                True,
	
	            "Message":
	                "Logout completed successfully - MES MOCK"
	        }
	
	
	        bodyName = "UserLogout"
	
	
	    # =================================================================
	    #
	    # 5. S2M.OperationResult
	    #
	    # =================================================================
	
	    elif category == "S2M.OperationResult":
	
	        logger.info(
	            "Processing S2M.OperationResult"
	        )
	
	
	        responseBody = {
	
	            "ResultFlag":
	                True,
	
	            "Message":
	                "Operation result received successfully - MES MOCK"
	        }
	
	
	        bodyName = "OperationResult"
	
	
	    # =================================================================
	    #
	    # 6. S2M.MachineAlarm
	    #
	    # =================================================================
	
	    elif category == "S2M.MachineAlarm":
	
	        logger.info(
	            "Processing S2M.MachineAlarm"
	        )
	
	
	        responseBody = {
	
	            "ResultFlag":
	                True,
	
	            "Message":
	                "Machine alarm received successfully - MES MOCK"
	        }
	
	
	        bodyName = "MachineAlarm"
	
	
	    # =================================================================
	    #
	    # 7. S2M.MachineState
	    #
	    # =================================================================
	
	    elif category == "S2M.MachineState":
	
	        logger.info(
	            "Processing S2M.MachineState"
	        )
	
	
	        responseBody = {
	
	            "ResultFlag":
	                True,
	
	            "Message":
	                "Machine state received successfully - MES MOCK"
	        }
	
	
	        bodyName = "MachineState"
	
	
	    # =================================================================
	    #
	    # 8. S2M.UnlinkData
	    #
	    # =================================================================
	
	    elif category == "S2M.UnlinkData":
	
	        logger.info(
	            "Processing S2M.UnlinkData"
	        )
	
	
	        responseBody = {
	
	            "ResultFlag":
	                True,
	
	            "Message":
	                "Unlink operation completed successfully - MES MOCK"
	        }
	
	
	        bodyName = "UnlinkData"
	
	
	    # =================================================================
	    #
	    # 9. S2M.ProductionOrderStart
	    #
	    # =================================================================
	
	    elif category == "S2M.ProductionOrderStart":
	
	        logger.info(
	            "Processing S2M.ProductionOrderStart"
	        )
	
	
	        responseBody = {
	
	            "ResultFlag":
	                True,
	
	            "Message":
	                "Production order started successfully - MES MOCK"
	        }
	
	
	        bodyName = "ProductionOrderStart"
	
	
	    # =================================================================
	    #
	    # 10. S2M.ProductionOrderState
	    #
	    # =================================================================
	
	    elif category == "S2M.ProductionOrderState":
	
	        logger.info(
	            "Processing S2M.ProductionOrderState"
	        )
	
	
	        productionOrder = getBusinessBody(
	            inputs,
	            "ProductionOrderState"
	        )
	
	
	        responseBody = {
	
	            "ProductionOrderNo":
	                productionOrder.get(
	                    "ProductionOrderNo",
	                    ""
	                ),
	
	            "ResultFlag":
	                True,
	
	            "Message":
	                "Production order state updated successfully - MES MOCK"
	        }
	
	
	        bodyName = "ProductionOrderState"
	
	
	    # =================================================================
	    #
	    # 11. S2M.UnloadingMaterial
	    #
	    # =================================================================
	
	    elif category == "S2M.UnloadingMaterial":
	
	        logger.info(
	            "Processing S2M.UnloadingMaterial"
	        )
	
	
	        responseBody = {
	
	            "ResultFlag":
	                True,
	
	            "Message":
	                "Material unloading completed successfully - MES MOCK"
	        }
	
	
	        bodyName = "UnloadingInfo"
	
	
	    # =================================================================
	    #
	    # 12. S2M.MESHeartbeat
	    #
	    # =================================================================
	
	    elif (
	        category == "S2M.MESHeartbeat"
	        or
	        category == "S2M.MESHbit"
	    ):
	
	        logger.info(
	            "Processing S2M.MESHeartbeat"
	        )
	
	
	        responseHeader[
	            "InterfaceName"
	        ] = "S2M.MESHeartbeat"
	
	
	        responseBody = {
	
	            "Status":
	                "200",
	
	            "ResultFlag":
	                True,
	
	            "Message":
	                "MES MOCK is available",
	
	            "EventTimestamp":
	                utcTimestamp()
	        }
	
	
	        bodyName = "HeartbeatResponse"
	
	
	    # =================================================================
	    #
	    # 13. S2M.ScrapReport
	    #
	    # =================================================================
	
	    elif category == "S2M.ScrapReport":
	
	        logger.info(
	            "Processing S2M.ScrapReport"
	        )
	
	
	        responseBody = {
	
	            "ResultFlag":
	                True,
	
	            "Message":
	                "Scrap report received successfully - MES MOCK"
	        }
	
	
	        bodyName = "WastageReport"
	
	
	    # =================================================================
	    #
	    # 14. S2M.CreateSerial
	    #
	    # =================================================================
	
	    elif category == "S2M.CreateSerial":
	
	        logger.info(
	            "Processing S2M.CreateSerial"
	        )
	
	
	        createSerial = getBusinessBody(
	            inputs,
	            "CreateSerial"
	        )
	
	
	        workOrderNo = str(
	            createSerial.get(
	                "WorkOrderNo",
	                "000001"
	            )
	        )
	
	
	        generatedId = (
	
	            "MOCKCELL-"
	
	            +
	
	            workOrderNo
	
	            +
	
	            "-"
	
	            +
	
	            system.date.format(
	                system.date.now(),
	                "yyyyMMddHHmmss"
	            )
	        )
	
	
	        responseBody = {
	
	            "GeneratedID":
	                generatedId,
	
	            "ResultFlag":
	                True,
	
	            "Message":
	                "Cell ID generated successfully - MES MOCK"
	        }
	
	
	        bodyName = "CreateSerial"
	
	
	    # =================================================================
	    #
	    # 15. S2M.Serialnbound
	    #
	    # Request business body: SerialInbound
	    # Response business body: SerialInbound
	    #
	    # =================================================================
	
	    elif category == "S2M.Serialnbound":
	
	        logger.info(
	            "Processing S2M.Serialnbound"
	        )
	
	
	        serialInbound = getBusinessBody(
	            inputs,
	            "SerialInbound"
	        )
	
	
	        serialInfo = serialInbound.get(
	            "SerialInfo",
	            []
	        )
	
	
	        try:
	            serialCount = len(serialInfo)
	        except:
	            serialCount = 0
	
	
	        logger.info(
	            "S2M.Serialnbound received. Equipment=%s, WorkOrder=%s, RecipeID=%s, OperationNo=%s, SerialCount=%s"
	            % (
	                str(serialInbound.get("Equipment", "")),
	                str(serialInbound.get("WorkOrder", "")),
	                str(serialInbound.get("RecipeID", "")),
	                str(serialInbound.get("OperationNo", "")),
	                str(serialCount)
	            )
	        )
	
	
	        responseBody = {
	
	            "ResultFlag":
	                True,
	
	            "Message":
	                "Serial inbound received successfully - MES MOCK"
	        }
	
	
	        bodyName = "SerialInbound"
	
	
	    # =================================================================
	    #
	    # GENERIC INTERFACE
	    #
	    # =================================================================
	
	    else:
	
	        logger.info(
	            "Processing Generic MES Mock Interface=%s"
	            % str(category)
	        )
	
	
	        if category and "." in category:
	
	            bodyName = category.split(
	                "."
	            )[-1]
	
	        else:
	
	            bodyName = (
	                category
	                or
	                "MockResponse"
	            )
	
	
	        responseBody = {
	
	            "ResultFlag":
	                True,
	
	            "Message":
	                "%s processed successfully - MES MOCK"
	                % str(category)
	        }
	
	
	    # =================================================================
	    # BUILD INNER MES RESPONSE
	    #
	    # MessageHeader FIRST
	    # Business Body SECOND
	    #
	    # =================================================================
	
	    mesResponseJson = buildMESResponseJSON(
	        responseHeader,
	        bodyName,
	        responseBody
	    )
	
	
	    logger.info(
	        "MES ResponseJSON=%s"
	        % mesResponseJson
	    )
	
	
	    # =================================================================
	    # BUILD FINAL API RESPONSE
	    #
	    # {
	    #     "Outputs": {
	    #         "__Routing__": true,
	    #         "ResponseJSON": "<JSON STRING>"
	    #     }
	    # }
	    #
	    # =================================================================
	
	    finalResponse = buildFinalApiResponse(
	        mesResponseJson
	    )
	
	
	    logger.info(
	        "Final API Response=%s"
	        % system.util.jsonEncode(
	            finalResponse
	        )
	    )
	
	
	    logger.info(
	        "MES MOCK SUCCESS. "
	        "Category=%s, "
	        "TransactionId=%s"
	        % (
	            category,
	            transactionId
	        )
	    )
	
	
	    logger.info(
	        "============================================================"
	    )
	
	
	    # =================================================================
	    # RETURN HTTP 200
	    # =================================================================
	
	    return {
	
	        "json":
	            finalResponse,
	
	        "responseCode":
	            200
	    }
	
	
	# =====================================================================
	# ERROR HANDLER
	# =====================================================================
	
	except Exception, ex:
	
	    errorMessage = str(
	        ex
	    )
	
	
	    logger.error(
	        "MES MOCK ERROR. %s"
	        % errorMessage
	    )
	
	
	    # -----------------------------------------------------------------
	    # Inner error response
	    # -----------------------------------------------------------------
	
	    errorHeader = {
	
	        "Equipment":
	            "",
	
	        "InterfaceName":
	            "",
	
	        "TransactionId":
	            "",
	
	        "SourceSystem":
	            "MES",
	
	        "TargetSystem":
	            "SCADA",
	
	        "EventTimestamp":
	            system.date.format(
	                system.date.now(),
	                "yyyy-MM-dd'T'HH:mm:ss.SSS"
	            )
	    }
	
	
	    errorBody = {
	
	        "ResultFlag":
	            False,
	
	        "Message":
	            errorMessage
	    }
	
	
	    headerJson = system.util.jsonEncode(
	        errorHeader
	    )
	
	
	    bodyJson = system.util.jsonEncode(
	        errorBody
	    )
	
	
	    errorResponseJson = (
	
	        "{"
	
	        +
	
	        "\"MessageHeader\":"
	
	        +
	
	        headerJson
	
	        +
	
	        ","
	
	        +
	
	        "\"MockResponse\":"
	
	        +
	
	        bodyJson
	
	        +
	
	        "}"
	    )
	
	
	    # -----------------------------------------------------------------
	    # Final WebDev error envelope
	    # -----------------------------------------------------------------
	
	    finalErrorResponse = {
	
	        "Outputs": {
	
	            "__Routing__":
	                True,
	
	            "ResponseJSON":
	                errorResponseJson
	        }
	    }
	
	
	    logger.error(
	        "MES MOCK ERROR RESPONSE=%s"
	        % system.util.jsonEncode(
	            finalErrorResponse
	        )
	    )
	
	
	    return {
	
	        "json":
	            finalErrorResponse,
	
	        "responseCode":
	            500
	    }