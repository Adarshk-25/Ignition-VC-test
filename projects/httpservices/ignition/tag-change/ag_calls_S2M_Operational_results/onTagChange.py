def onTagChange(initialChange, newValue, previousValue, event, executionCount):
	
	    ###############################################################################
	    # Project        : AGRATAS SCADA - MES Integration
	    # Interface      : S2M.OperationResult
	    # Module         : Ignition Gateway Tag Change Script
	    # MES Operation  : AGR_PRD_S2M_Operational_results
	    #
	    # Description:
	    #   1. Monitors AGSetOperationResult/Handshake.
	    #   2. Ignores initial subscriptions and unchanged values.
	    #   3. Delegates the physical trigger path to the shared AG router.
	    #   4. The handler maps each RequestData record by production type and
	    #      applies typed empty defaults to unavailable business fields.
	    #   5. SenderFBS supplies EquipmentId for every mapped operation.
	    #   6. HTTP 200 is delivered; eligible non-200/transport failures are
	    #      persisted through the shared Store-and-Forward service.
	    #   7. PLC receives status 200 after delivery or successful queue commit.
	    #   8. StatusCode, ResponseTimestamp and ACK are written before Handshake.
	    #
	    # Handshake:
	    #   0 = Idle
	    #   1 = New request from PLC
	    #   2 = SCADA processing completed
	    #   3 = Invalid or cancelled request
	    #
	    # Version History
	    # -----------------------------------------------------------------------------
	    # Version | Date       | Author | Description
	    # -----------------------------------------------------------------------------
	    # 1.0     | 24-Jul-2026| Hari   | Initial OperationResult trigger
	    # 2.0     | 11-Sep-2026| Hari   | Asynchronous list/Store-and-Forward flow
	    # 2.1     | 27-Sep-2026| Hari   | Production-type optional-field mapping
	    ###############################################################################
	
	    from scada_interface import router
	    trigger_logger = system.util.getLogger(
	        "SCADA.Interface.S2M.OperationResult.Trigger"
	    )
	
	    if initialChange:
	        trigger_logger.info("DEBUG_MODE: Ignoring initial tag subscription event")
	        return
	
	    if previousValue.value == newValue.value:
	        trigger_logger.info(
	            "DEBUG_MODE: Ignoring tag event because the value did not change"
	        )
	        return
	
	    tag_path = str(event.getTagPath())
	    trigger_logger.info(
	        "DEBUG_MODE: OperationResult handshake changed. "
	        "tag_path=%s previous=%s current=%s execution_count=%s"
	        % (tag_path, previousValue.value, newValue.value, executionCount)
	    )
	
	    router.handle_ag_call(
	        interface_name="S2M.OperationResult",
	        handshake_tag_path=tag_path,
	        handshake_value=newValue.value
	    )