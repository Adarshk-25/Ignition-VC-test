def handleTimerEvent():
	import random
	
	statusPath = "[default]ConveyorSimulation/Conveyor1/status"
	speedPath = "[default]ConveyorSimulation/Conveyor1/speed"
	faultPath = "[default]ConveyorSimulation/Conveyor1/fault"
	value = random.choice(["RUNNING","STOPPED"])
	fault = random.random() < 0.1
	if fault:
		value = "STOPPED"
		speed = 0
	else:
		if value == "RUNNING":
			speed = random.randint(50,100)
		else:
			speed=0
	system.tag.writeBlocking([statusPath,speedPath,faultPath],[value,speed,fault])


