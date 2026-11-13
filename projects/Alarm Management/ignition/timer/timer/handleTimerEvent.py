def handleTimerEvent():
	import random, datetime
    
    # Base path to UDT instance
	basePath = "[default]Conveyer"

    # Tag paths inside the UDT
	batchStartPath   = basePath + "/batchStartTime"
	batchEndPath     = basePath + "/batchEndTime"
	tensionPath      = basePath + "/beltTension"
	directionPath    = basePath + "/direction"
	loadPath         = basePath + "/load"
	runningPath      = basePath + "/runningStatus"
	speedPath        = basePath + "/conveyerSpeed"
	vibration		  =basePath+"/vibration"
    
    # Simulated values
	now = datetime.datetime.now()
    
    # Batch logic
	batchActive = random.choice([True, False])
	if batchActive:
	    batchStart = now
	    batchEnd   = None
	else:
		batchStart = None
		batchEnd   = now
    
    # Mechanical/electrical values
	tension   = random.randint(70, 120)          # Belt tension (N)
	direction = random.choice([0, 1, 2])        # 0=Stopped, 1=Forward, 2=Reverse
	load      = random.randint(0, 100)          # Load percentage
	running   = (direction != 0)                # Boolean
	vibrationVal=random.randint(100,200)
    # Speed logic: only when running forward/reverse
	if running:
	    speed = random.randint(50, 100)         # Conveyor speed (m/min or rpm)
	else:
		speed = 0
    
    # Write values to UDT tags
	system.tag.writeBlocking(
        [batchStartPath, batchEndPath, tensionPath, directionPath, loadPath, runningPath, speedPath,vibration],
        [batchStart, batchEnd, tension, direction, load, running, speed,vibrationVal]
    )