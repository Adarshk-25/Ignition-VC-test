def onTagChange(initialChange, newValue, previousValue, event, executionCount):
	if not initialChange and newValue.value == 1:
	
	    # Read all required input tags
	    equipment = system.tag.readBlocking(
	        ["[default]LoginSimulationTags/EquipmentID"]
	    )[0].value
	
	    employee = system.tag.readBlocking(
	        ["[default]LoginSimulationTags/EmployeeNo"]
	    )[0].value
	
	    password = system.tag.readBlocking(
	        ["[default]LoginSimulationTags/Password"]
	    )[0].value
	
	    role = system.tag.readBlocking(
	        ["[default]LoginSimulationTags/Role"]
	    )[0].value
	
	    validateSkill = system.tag.readBlocking(
	        ["[default]LoginSimulationTags/ValidateSkill"]
	    )[0].value
	
	    loginType = system.tag.readBlocking(
	        ["[default]LoginSimulationTags/LoginType"]
	    )[0].value
	
	    loginTime = system.tag.readBlocking(
	        ["[default]LoginSimulationTags/LoginTime"]
	    )[0].value
	
	
	    # Build JSON structure (as per IDS)
	    payload = {
	        "UserLogin": {
	            "EquipmentID": equipment,
	            "EmployeeNo": employee,
	            "Password": password,
	            "Role": role,
	            "ValidateSkill": validateSkill,
	            "LoginTime": str(loginTime),
	            "LoginType": loginType
	        }
	    }
	
	    # Print JSON to logs
	    system.util.getLogger("LoginSimulation").info(str(payload))
	
	    # Simulate MES validation
	    if employee == "TEST_USER" and password == "1234":
	        result = True
	        message = "Login and Skill Validation Successful."
	    else:
	        result = False
	        message = "Invalid Credentials."
	
	    system.tag.writeBlocking(
	        [
	            "[default]LoginSimulationTags/ResultFlag",
	            "[default]LoginSimulationTags/Message",
	            "[default]LoginSimulationTags/ResponseHandshakeBit"
	        ],
	        [
	            result,
	            message,
	            1
	        ]
	    )