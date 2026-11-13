def handleTimerEvent():
	###############################################################################
	# Project        : AGRATAS SCADA - MES Integration
	# File Name      : MESHeartbeat_timer.py
	# Module         : Gateway Timer Event - MESHeartbeat
	#
	# Gateway setup  : Fixed delay, initial delay 5,000 ms, delay 20,000 ms,
	#                  dedicated thread.
	###############################################################################
	
	from scada_interface import router
	
	
	router.handle_scheduled_request("S2M.MESHeartbeat")