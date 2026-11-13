def onTagChange(initialChange, newValue, previousValue, event, executionCount):
	def onTagChange(initialChange, newValue, previousValue, event, executionCount):

    system.util.getLogger("MES").info(
        "Prev={} New={}".format(previousValue.value, newValue.value)
    )

    if initialChange:
        return

    if newValue.value == True and previousValue.value == False:
        system.util.getLogger("MES").info("READ DATA NOW")