def onTagChange(initialChange, newValue, previousValue, event, executionCount):
	system.util.getLogger("simulatePLCACK")
	
	try:
	    system.util.getLogger("simulatePLCACK").info("DownloadTrigger Tag Change Started")
	
	    if initialChange == False:
	        if newValue.value == True:
	            system.util.getLogger("simulatePLCACK").info("DownloadTrigger TRUE detected")
	
	            import time
	            #time.sleep(2)
	
	            system.tag.writeBlocking(
	                ["[default]M2E_RecipeDownload/RecipeDownload/Ack"],
	                [True]
	            )
	
	            system.tag.writeBlocking(
	                ["[default]M2E_RecipeDownload/RecipeDownload/DownloadTrigger"],
	                [False]
	            )
	
	            system.util.getLogger("simulatePLCACK").info("Ack TRUE written and DownloadTrigger reset FALSE")
	    else:
	        system.util.getLogger("simulatePLCACK").info("Initial change ignored")
	
	except Exception as e:
	    system.util.getLogger("simulatePLCACK").error(
	        "ERROR: " + str(e)
	    )