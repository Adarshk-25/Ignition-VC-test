def handleTimerEvent():
	inputs = [
	    "STEP1",
	    "PO-12345",
	    "V1",
	    "Param_001",
	    "Temperature",
	    "degC",
	    60.0,
	    40.0,
	    45.0,
	    "V1"
	]
	
	connectionName = "PLC"
	objectId = (
        "nsu=http://agratas.com/UA/;"
        "s=IN11.E123.PAE.NTC11/AGMethods"
    )
    
    methodId = (
        "nsu=http://agratas.com/UA/;"
        "s=IN11.E123.PAE.NTC11/AGMethods/SetRecipe"
    )
	
	result = system.opcua.callMethod(
	    "PLC",
	    objectId,
	    scalarTestMethodId,
	    inputs
	)