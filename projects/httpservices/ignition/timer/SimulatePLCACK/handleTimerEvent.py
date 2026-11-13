def handleTimerEvent():
	logger = system.util.getLogger("simulatePLCACK")
	
	try:
	
	    logger.info("Timer Script Started")
	
	    triggerTag = "[default]M2E_RecipeDownload/RecipeDownload/DownloadTrigger"
	    ackTag = "[default]M2E_RecipeDownload/RecipeDownload/Ack"
	
	    trigger = system.tag.readBlocking([triggerTag])[0].value
	    ack = system.tag.readBlocking([ackTag])[0].value
	
	    logger.info("Trigger Value for DownloadTrigger " + str(trigger) )
	    logger.info("Trigger Value for Ack " + str(ack) )
	    import time
	
	    if trigger == True:
	
	        logger.info("Trigger TRUE detected")
	
	        time.sleep(2)
	
	        writeResults=system.tag.writeBlocking(
	            [ackTag],
	            [True]
	        )
	
	        logger.info("ACK tag written" + str(writeResults))
	
	        system.tag.writeBlocking(
	            [triggerTag],
	            [False]
	        )
	
	        logger.info("Trigger value for DownloadTrigger reset FALSE")
	
	except Exception as e:
	
	    logger.error("ERROR: " + str(e))