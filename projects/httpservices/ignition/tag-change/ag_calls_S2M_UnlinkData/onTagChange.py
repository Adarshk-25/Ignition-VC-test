def onTagChange(initialChange, newValue, previousValue, event, executionCount):
	###############################################################################
	# Project        : AGRATAS SCADA - MES Integration
	# File Name      : ag_calls_S2M_UnlinkData.py
	# Module         : S2M.UnlinkData Handshake Tag Event
	# Description    : Routes genuine AGUnlink handshake changes to the framework.
	# Author         : Hari
	# Version        : 1.1
	# Date           : 09-Sep-2026
	#
	# Change History
	# -----------------------------------------------------------------------------
	# Sl No | Version | Date        | Author | Fix/Change
	# -----------------------------------------------------------------------------
	# 1     | 1.0     | 09-Sep-2026 | Hari   | Initial S2M.UnlinkData trigger
	# 2     | 1.1     | 09-Sep-2026 | Hari   | Changed entry point to Gateway onTagChange
	# -----------------------------------------------------------------------------
	###############################################################################
	
	    from scada_interface import config, router
	
	
	# -----------------------------------------------------------------------------
	# Function    : onTagChange
	# Description : Ignores subscriptions/duplicates and routes a real PLC edge.
	# -----------------------------------------------------------------------------
	
	    trigger_config = config.get_interface_config("S2M.UnlinkData")
	    trigger_logger = system.util.getLogger("SCADA.Interface.S2M.UnlinkData.Trigger")
	
	    if initialChange:
	        if trigger_config.get("debug_enabled") is True:
	            trigger_logger.info("DEBUG_MODE: Ignoring initial tag subscription event")
	        return
	
	    if previousValue.value == newValue.value:
	        if trigger_config.get("debug_enabled") is True:
	            trigger_logger.info("DEBUG_MODE: Ignoring unchanged handshake event")
	        return
	
	    value = newValue.value
	    if isinstance(value, bool) or not isinstance(value, (int, long)):
	        trigger_logger.error("Invalid UnlinkData handshake value; integer required")
	        return
	
	    tag_path = str(event.getTagPath())
	    if trigger_config.get("debug_enabled") is True:
	        trigger_logger.info(
	            "DEBUG_MODE: UnlinkData handshake changed. tag_path=%s previous=%s current=%s execution_count=%s"
	            % (tag_path, previousValue.value, value, executionCount)
	        )
	
	    
	    router.handle_ag_call(
			interface_name="S2M.UnlinkData",
			handshake_tag_path=tag_path,
			handshake_value=newValue.value
		)