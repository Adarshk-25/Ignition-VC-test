def onTagChange(initialChange, newValue, previousValue, event, executionCount):
	# Project        : AGRATAS SCADA - MES Integration
	# Interface      : S2M.UnloadingMaterial
	# Module         : Ignition Gateway Tag Change Script
	# MES Operation  : ag_calls_S2M_UnloadingMaterial
	#
	# Description:
	#   1. Monitors the AGUnloadingMaterial Handshake tag.
	#   2. Ignores the initial subscription event and unchanged values.
	#   3. Delegates the physical trigger path to the shared AG router.
	#   4. Uses the equipment in that path for dynamic PLC tag routing.
	#   5. Reads RequestData and RequestAckNumber in the interface handler.
	#   6. Maps SourceFBS, RFIDNo, ItemID and ReasonCode into UnloadingInfo.
	#   7. Treats HTTP 200 as delivered and durably queues eligible failures.
	#   8. Copies RequestAckNumber after delivery or successful queue insertion.
	#   9. Writes StatusCode, ResponseTimestamp and ResponseAckNumber first.
	#  10. Writes Handshake last after all metadata writes succeed.
	#
	# Handshake:
	#   0 = Idle
	#   1 = New request from PLC
	#   2 = SCADA processing completed
	#   3 = Invalid or cancelled request
	#
	# PLC RequestData:
	# {
	#     "SourceFBS": "IN11.E115.PCE.MIX21",
	#     "RFIDNo": "HU",
	#     "ItemID": "JR-001",
	#     "ReasonCode": "Testing"
	# }
	#
	# Version History
	# -----------------------------------------------------------------------------
	# Version | Date       | Author | Description
	# -----------------------------------------------------------------------------
	# 1.0     | 11-Sep-2026| Hari   | Initial thin framework trigger
	# 1.1     | 11-Sep-2026| Hari   | Document SourceFBS to EquipmentId mapping
	# 1.2     | 11-Sep-2026| Hari   | Document asynchronous durable delivery
	###############################################################################

	from scada_interface import router
	trigger_logger = system.util.getLogger(
		"SCADA.Interface.S2M.UnloadingMaterial.Trigger"
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
		"DEBUG_MODE: UnloadingMaterial handshake changed. "
		"tag_path=%s previous=%s current=%s execution_count=%s"
		% (tag_path, previousValue.value, newValue.value, executionCount)
	)

	router.handle_ag_call(
		interface_name="S2M.UnloadingMaterial",
		handshake_tag_path=tag_path,
		handshake_value=newValue.value
	)