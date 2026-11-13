def doGet(request, session):
		tagValue = system.tag.readBlocking(['[default]agratas/_System/_WriteOptimizationDutyCycle.Timestamp'])
	return {'json': {'tagValue':str(tagValue)}}