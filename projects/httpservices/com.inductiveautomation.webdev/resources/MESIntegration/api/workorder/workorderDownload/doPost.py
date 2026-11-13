def doPost(request, session):
	###############################################################################
	# Project        : AGRATAS SCADA - MES Integration
	# File Name      : doPost.py
	# Module         : Work Order Download WebDev Endpoint
	###############################################################################
	
	from scada_interface import router
	return router.handle_rest_request(
		interface_name="WorkOrderDownload",
	        direction="M2S_TO_S2E",
	        request=request
	)