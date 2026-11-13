def doGet(request, session):

	import system
	import random
	
	global oee_data
	
	# initialize once
	if 'oee_data' not in globals():
		oee_data = {
			"oeeE": 76,
			"oeeA": 75.8,
			"oeeB": 98.1,
			"alarms": 3,
			"lastUpdate": system.date.now()
		}

	now = system.date.now()
	diff = system.date.secondsBetween(oee_data["lastUpdate"], now)

	# update every 10 seconds
	if diff >= 3:
		oee_data["oeeE"] = round(random.uniform(75, 95), 2)
		oee_data["oeeA"] = round(random.uniform(75, 95), 1)
		oee_data["oeeB"] = round(random.uniform(75, 95), 1)
		oee_data["alarms"] = random.randint(0, 5)
		oee_data["lastUpdate"] = now

	return {
		'json': {
			"oeeE": oee_data["oeeE"],
			"oeeA": oee_data["oeeA"],
			"oeeB": oee_data["oeeB"],
			"alarms": oee_data["alarms"]
		}
	}