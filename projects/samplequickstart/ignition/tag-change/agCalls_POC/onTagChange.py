def onTagChange(initialChange, newValue, previousValue, event, executionCount):
	logger = system.util.getLogger("agCalls_POC")
	
	try:
	    logger.info("AG Calls tag change started")
	
	    # Ignore the initial tag subscription event
	    if initialChange:
	        logger.info("Initial change ignored")
	
	    else:
	        # Convert the incoming tag value to integer
	        handshakeValue = int(newValue.value)
	
	        # PLC expects ResponseTime as a String
	        responseTime = system.date.format(
	            system.date.now(),
	            "yyyy-MM-dd'T'HH:mm:ss.SSS"
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
	
	        # Handshake value 1 means success
	        if handshakeValue == 1:
	            statusCode = 200
	            logger.info("Valid handshake received: 1")
	
	        # Any other value means failure
	        else:
	            statusCode = 500
	            logger.warn(
	                "Invalid handshake received: %s"
	                % str(handshakeValue)
	            )
	
	        writeResults = system.tag.writeBlocking(
	            [
	                statusCodePath,
	                responseTimePath
	            ],
	            [
	                statusCode,
	                responseTime
	            ]
	        )
	
	        logger.info(
	            "PLC response written. StatusCode=%s, ResponseTime=%s, "
	            "WriteResults=%s"
	            % (
	                str(statusCode),
	                responseTime,
	                str(writeResults)
	            )
	        )
	
	except Exception as e:
	    logger.error(
	        "AG Calls tag change error: %s"
	        % str(e)
	    )