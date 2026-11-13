def doPost(request, session):
	###############################################################################
	# Project        : AGRATAS SCADA - MES Integration
	# Interface      : M2S.WorkOrderDownload
	# Direction      : MES -> SCADA
	# Module         : Ignition WebDev doPost
	#
	# Purpose
	# -------
	# 1. Receive WorkOrderDownload payload from MES.
	# 2. Log complete request in Gateway logs.
	# 3. Return acknowledgement response.
	#
	# NOTE
	# ----
	# No validation.
	# No OPC UA.
	# No PLC call.
	# No database operation.
	###############################################################################
	
	
	###############################################################################
	# Logger
	###############################################################################
	
	logger = system.util.getLogger(
	    "M2S_WorkOrderDownload"
	)
	
	
	###############################################################################
	# Helper : JSON Value
	###############################################################################
	
	def jsonValue(value):
	
	    return system.util.jsonEncode(
	        value
	    )
	
	
	###############################################################################
	# Helper : Safe String
	###############################################################################
	
	def safeString(value):
	
	    if value is None:
	        return ""
	
	    return str(value)
	
	
	###############################################################################
	# Helper : Build Response
	#
	# MessageHeader values are taken directly from incoming request.
	###############################################################################
	
	def buildResponseJson(
	    messageHeader,
	    resultFlag,
	    message
	):
	
	    return (
	        "{"
	            "\"MessageHeader\":{"
	
	                "\"InterfaceName\":"
	                + jsonValue(
	                    safeString(
	                        messageHeader.get(
	                            "InterfaceName",
	                            ""
	                        )
	                    )
	                )
	                + ","
	
	                "\"TransactionId\":"
	                + jsonValue(
	                    safeString(
	                        messageHeader.get(
	                            "TransactionId",
	                            ""
	                        )
	                    )
	                )
	                + ","
	
	                "\"SourceSystem\":"
	                + jsonValue(
	                    safeString(
	                        messageHeader.get(
	                            "SourceSystem",
	                            ""
	                        )
	                    )
	                )
	                + ","
	
	                "\"TargetSystem\":"
	                + jsonValue(
	                    safeString(
	                        messageHeader.get(
	                            "TargetSystem",
	                            ""
	                        )
	                    )
	                )
	                + ","
	
	                "\"EventTimestamp\":"
	                + jsonValue(
	                    safeString(
	                        messageHeader.get(
	                            "EventTimestamp",
	                            ""
	                        )
	                    )
	                )
	
	            + "},"
	
	            "\"WorkOrderDownload\":{"
	
	                "\"ResultFlag\":"
	                + jsonValue(
	                    str(
	                        resultFlag
	                    )
	                )
	                + ","
	
	                "\"Message\":"
	                + jsonValue(
	                    message
	                )
	
	            + "}"
	
	        + "}"
	    )
	
	
	###############################################################################
	# Default values
	###############################################################################
	
	messageHeader = {}
	
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
	    # Step 2 : Log raw request
	    ###########################################################################
	
	    logger.info(
	        "M2S.WorkOrderDownload raw request received. Payload=%s"
	        % str(
	            data
	        )
	    )
	
	
	    ###########################################################################
	    # Step 3 : Decode JSON if incoming payload is String
	    ###########################################################################
	
	    if isinstance(
	        data,
	        basestring
	    ):
	
	        data = system.util.jsonDecode(
	            data
	        )
	
	
	    ###########################################################################
	    # Step 4 : Log decoded complete payload
	    ###########################################################################
	
	    requestJson = system.util.jsonEncode(
	        data
	    )
	
	
	    logger.info(
	        "M2S.WorkOrderDownload decoded request. Payload=%s"
	        % requestJson
	    )
	
	
	    ###########################################################################
	    # Step 5 : Read MessageHeader
	    #
	    # No validation.
	    ###########################################################################
	
	    messageHeader = data.get(
	        "MessageHeader",
	        {}
	    )
	
	
	    transactionId = safeString(
	        messageHeader.get(
	            "TransactionId",
	            ""
	        )
	    )
	
	
	    ###########################################################################
	    # Step 6 : Read WorkOrderDownload
	    #
	    # No validation.
	    ###########################################################################
	
	    workOrder = data.get(
	        "WorkOrderDownload",
	        {}
	    )
	
	
	    ###########################################################################
	    # Step 7 : Log MessageHeader
	    ###########################################################################
	
	    logger.info(
	        "WorkOrderDownload Header. "
	        "InterfaceName=%s, "
	        "TransactionId=%s, "
	        "SourceSystem=%s, "
	        "TargetSystem=%s, "
	        "EventTimestamp=%s"
	        % (
	            safeString(
	                messageHeader.get(
	                    "InterfaceName",
	                    ""
	                )
	            ),
	            transactionId,
	            safeString(
	                messageHeader.get(
	                    "SourceSystem",
	                    ""
	                )
	            ),
	            safeString(
	                messageHeader.get(
	                    "TargetSystem",
	                    ""
	                )
	            ),
	            safeString(
	                messageHeader.get(
	                    "EventTimestamp",
	                    ""
	                )
	            )
	        )
	    )
	
	
	    ###########################################################################
	    # Step 8 : Log complete WorkOrderDownload section
	    ###########################################################################
	
	    logger.info(
	        "WorkOrderDownload Data. "
	        "TransactionId=%s, "
	        "Payload=%s"
	        % (
	            transactionId,
	            system.util.jsonEncode(
	                workOrder
	            )
	        )
	    )
	
	
	    ###########################################################################
	    # Step 9 : Build Success Response
	    ###########################################################################
	
	    responseJson = buildResponseJson(
	        messageHeader,
	        "200",
	        "WorkOrderDownload to PLC successfully"
	    )
	
	
	    ###########################################################################
	    # Step 10 : HTTP Status
	    ###########################################################################
	
	    request[
	        "servletResponse"
	    ].setStatus(
	        200
	    )
	
	
	    ###########################################################################
	    # Step 11 : Log final response
	    ###########################################################################
	
	    logger.info(
	        "M2S.WorkOrderDownload completed. "
	        "TransactionId=%s, "
	        "Response=%s"
	        % (
	            transactionId,
	            responseJson
	        )
	    )
	
	
	    ###########################################################################
	    # Step 12 : Return response
	    ###########################################################################
	
	    return {
	
	        "json": responseJson
	    }
	
	
	###############################################################################
	# Exception Handling
	#
	# Only catches actual script / JSON parsing errors.
	# This is NOT payload validation.
	###############################################################################
	
	except Exception as error:
	
	    logger.error(
	        "M2S.WorkOrderDownload exception. "
	        "TransactionId=%s, "
	        "Error=%s"
	        % (
	            transactionId,
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
	        messageHeader,
	        "500",
	        "WorkOrderDownload failed: %s"
	        % str(
	            error
	        )
	    )
	
	
	    return {
	
	        "json": responseJson
	    }