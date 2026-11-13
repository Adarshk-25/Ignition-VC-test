def onStartup(session):
	    try:
        system.perspective.navigate("MixingBockDiagram/MixingBlock")
    except Exception as e:
        system.util.getLogger("Landing").error(str(e))