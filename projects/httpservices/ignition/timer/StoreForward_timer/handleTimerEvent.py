def handleTimerEvent():
	##############################################################################
	# Project        : AGRATAS SCADA - MES Integration
	# File Name      : StoreForward_timer.py
	# Module         : Gateway Timer Event - Store-and-Forward
	#
	# Description:
	# Invokes one common dispatcher on a dedicated fixed-delay 30,000 ms timer.
	#
	# Author         : Hari
	# Version        : 1.0
	# Date           : 06-Sep-2026
	#
	# Change History
	# ----------------------------------------------------------------------------
	# Sl No | Version | Date        | Author | Fix/Change
	# ----------------------------------------------------------------------------
	# 1     | 1.0     | 06-Sep-2026 | Hari   | Store-and-Forward framework conventions and observability
	# ----------------------------------------------------------------------------
	##############################################################################
	
	# Configure ONE Gateway timer: fixed delay 30,000 ms, dedicated thread.
	from scada_interface import router
	
	router.handle_store_and_forward()