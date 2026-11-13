def onTagChange(initialChange, newValue, previousValue, event, executionCount):
	# Project        : AGRATAS SCADA - MES Integration
	# Interface      : S2M.ScrapReport
	# Module         : Ignition Gateway Tag Change Script
	# MES Operation  : ag_calls_S2M_ScrapReport
	#
	# Description:
	#   1. Monitors the AGScrapReport Handshake tag.
	#   2. Ignores initial subscriptions and unchanged values.
	#   3. Delegates the physical path to the shared AG router.
	#   4. The handler reads RequestData, RequestAckNumber, WorkOrderType and
	#      OprSequenceNo and freezes the mapped MES envelope.
	#   5. HTTP 200 is delivered; every non-200/timeout is durably queued.
	#   6. PLC receives status 200 only after delivery or successful persistence.
	#   7. ResponseTimestamp is a Date and Handshake is written last.
	#
	# Version History
	# -----------------------------------------------------------------------------
	# Version | Date       | Author | Description
	# -----------------------------------------------------------------------------
	# 1.0     | 11-Sep-2026| Hari   | Initial asynchronous framework trigger
	###############################################################################

	from scada_interface import router
	trigger_logger = system.util.getLogger(
		"SCADA.Interface.S2M.ScrapReport.Trigger"
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
		"DEBUG_MODE: ScrapReport handshake changed. "
		"tag_path=%s previous=%s current=%s execution_count=%s"
		% (tag_path, previousValue.value, newValue.value, executionCount)
	)

	router.handle_ag_call(
		interface_name="S2M.ScrapReport",
		handshake_tag_path=tag_path,
		handshake_value=newValue.value
	)