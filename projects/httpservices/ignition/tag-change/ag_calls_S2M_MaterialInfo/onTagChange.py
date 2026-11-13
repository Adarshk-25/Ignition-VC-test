def onTagChange(initialChange, newValue, previousValue, event, executionCount):
	
	# Project        : AGRATAS SCADA - MES Integration
	# Interface      : S2M.MaterialInfo
	# Module         : Ignition Gateway Tag Change Script
	# MES Operation  : AGR_PRD_S2M_MaterialInfo
	#
	# Description:
	#   1. Monitors the AGSetItemInfo Handshake tag.
	#   2. Processes the request when Handshake changes to 1.
	#   3. Reads RequestData and RequestAckNumber from the Siemens PLC.
	#   4. Maps PLC request fields into the MES MaterialInfo request.
	#   5. Sends MessageHeader and MaterialInfo directly under Inputs.
	#   6. Receives and decodes Outputs.ResponseJSON from MES.
	#   7. Maps MES MaterialInfo values into the PLC AGItemResponse structure.
	#   8. Maps MES Authorization dynamically to PLC Authorized Boolean.
	#   9. Maps MES QualityStatus:
	#          Pass -> True
	#          Fail -> False
	#          Missing/Null/Unknown -> False
	#  10. Maps MES RecipeID to PLC RecipeId for StatusCode 200.
	#  11. Maps MES WorkOrder to PLC WorkOrderID for StatusCode 200.
	#  12. Uses empty RecipeId and WorkOrderID for every non-200 response.
	#  13. Copies PLC RequestAckNumber to ResponseAckNumber when StatusCode is 200.
	#  14. Writes ResponseData, StatusCode, ResponseTimestamp and
	#      ResponseAckNumber first.
	#  15. Writes Handshake last, only after all response writes succeed.
	#
	# Handshake:
	#   1 = New request from PLC
	#   2 = SCADA processing completed
	#   3 = Invalid or cancelled request
	#
	# PLC RequestData:
	# {
	#     "ItemID": "HUCO-006",
	#     "RecipeId": "PO_Mixing_100.07",
	#     "WorkOrderID": "AGR_Mixing_0406_01"
	# }
	#
	# MES Request:
	# {
	#     "Inputs": {
	#         "MessageHeader": {
	#             "InterfaceName": "S2M.MaterialInfo",
	#             "TransactionId": "MAT-20260722113821537",
	#             "SourceSystem": "SCADA",
	#             "TargetSystem": "MES",
	#             "EventTimestamp": "2026-07-22T11:38:21.537Z",
	#             "Equipment": "EQ_Mixing",
	#             "EmployeeNo": "657681"
	#         },
	#         "MaterialInfo": {
	#             "HuContainer": "HUCO-006",
	#             "FeedingLocation": "EQ_Mixing",
	#             "WorkOrder": "AGR_Mixing_0406_01",
	#             "RecipeID": "PO_Mixing_100.07"
	#         }
	#     }
	# }
	#
	# MES to PLC Response Mapping:
	# -----------------------------------------------------------------------------
	# MES Field        | PLC Field       | PLC Datatype
	# -----------------------------------------------------------------------------
	# HuContainer      | ItemID          | WString
	# BatchID          | BatchID         | WString
	# ExpiryDate       | ExpiryDate      | WString
	# QualityStatus    | QualityStatus   | Bool
	# Authorization    | Authorized      | Bool
	# RecipeID         | RecipeId        | WString
	# WorkOrder        | WorkOrderID     | WString
	#
	# Positive PLC ResponseData / AGItemResponse:
	# {
	#     "ItemID": "HUCO-006",
	#     "BatchID": "BATCH-001",
	#     "ExpiryDate": "2027-01-01T00:00:00Z",
	#     "QualityStatus": true,
	#     "Authorized": true,
	#     "RecipeId": "PO_Mixing_100.07",
	#     "WorkOrderID": "AGR_Mixing_0406_01"
	# }
	#
	# Technical Failure / Non-200 PLC ResponseData:
	# {
	#     "ItemID": "",
	#     "BatchID": "",
	#     "ExpiryDate": "",
	#     "QualityStatus": false,
	#     "Authorized": false,
	#     "RecipeId": "",
	#     "WorkOrderID": ""
	# }
	#
	# Version History
	# -----------------------------------------------------------------------------
	# Version | Date       | Author | Description
	# -----------------------------------------------------------------------------
	# 1.0     | 22-Jul-2026| Hari   | Initial MaterialInfo implementation
	# 1.1     | 22-Jul-2026| Hari   | Added dynamic MES request and response mapping
	# 1.2     | 22-Jul-2026| Hari   | Corrected MES Inputs request structure
	# 1.3     | 22-Jul-2026| Hari   | Removed OPC UA method call and changed
	#         |            |        | ResponseData to normal PLC tag write
	# 1.4     | 22-Jul-2026| Hari   | Added RequestAckNumber read and copied it to
	#         |            |        | ResponseAckNumber for successful responses
	# 1.5     | 22-Jul-2026| Hari   | Mapped MES Authorization and QualityStatus
	#         |            |        | dynamically into the PLC response
	# 1.6     | 23-Jul-2026| Hari   | Changed PLC QualityStatus datatype to Boolean.
	#         |            |        | MES Pass maps to True. Fail, null, missing or
	#         |            |        | unknown values map to False.
	# 1.7     | 24-Jul-2026| Hari   | Added MES RecipeID to PLC RecipeId mapping and
	#         |            |        | MES WorkOrder to PLC WorkOrderID mapping.
	# 1.8     | 24-Jul-2026| Hari   | Ensured all non-200 responses use empty string
	#         |            |        | fields and False Boolean fields.
	# 1.9     | 24-Jul-2026| Hari   | Changed PLC completion Handshake write to occur
	#         |            |        | only after response data and metadata succeed.
	# 2.0     | 12-Aug-2026| Hari   | Added trigger diagnostics matching the
	#         |            |        | S2M.OperationResult tag-change script.
	###############################################################################

	from scada_interface import router
	trigger_logger = system.util.getLogger("SCADA.Interface.S2M.MaterialInfo.Trigger")

	if initialChange:
		trigger_logger.info("DEBUG_MODE: Ignoring initial tag subscription event")
		return

	if previousValue.value == newValue.value:
		trigger_logger.info("DEBUG_MODE: Ignoring tag event because the value did not change")
		return

	tag_path = str(event.getTagPath())
	trigger_logger.info(
		"DEBUG_MODE: MaterialInfo handshake changed. tag_path=%s previous=%s current=%s execution_count=%s"
		% (tag_path, previousValue.value, newValue.value, executionCount)
	)

	router.handle_ag_call(
		interface_name="S2M.MaterialInfo",
		handshake_tag_path=tag_path,
		handshake_value=newValue.value
	)