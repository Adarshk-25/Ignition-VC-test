def doPost(request, session):
	###############################################################################
	# Project        : AGRATAS SCADA - MES Integration
	# File Name      : doPost.py
	# Module         : Material Status Update WebDev Endpoint
	#
	# Description:
	# Delegates M2S.MatStatusUpdate requests to the common integration router.
	###############################################################################
	
	from scada_interface import router
	
	
	# -----------------------------------------------------------------------------
	# Function    : doPost
	# Description : Routes one MES material status request through the framework.
	# -----------------------------------------------------------------------------
	return router.handle_rest_request(
	    interface_name="MatStatusUpdate",
	    direction="M2S_TO_S2E",
	    request=request
	    )