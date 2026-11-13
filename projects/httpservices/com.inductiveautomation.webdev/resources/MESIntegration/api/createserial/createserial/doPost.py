def doPost(request, session):
	###############################################################################
	# Project        : AGRATAS SCADA - MES Integration
	# File Name      : doPost.py
	# Module         : Create Serial WebDev Endpoint
	#
	# Description:
	# Delegates M2S.CreateSerial requests to the common integration router.
	###############################################################################
	
	from scada_interface import router
	
	
	# -----------------------------------------------------------------------------
	# Function    : doPost
	# Description : Routes one MES CreateSerial request through the framework.
	# -----------------------------------------------------------------------------
	
	return router.handle_rest_request(
	    interface_name="CreateSerial",
	    direction="M2S_TO_S2E",
	    request=request
	)