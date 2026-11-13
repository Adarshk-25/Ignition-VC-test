###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : ag_call_S2M_UnloadingMaterial.py
# Interface      : S2M.UnloadingMaterial
# Module         : Ignition Gateway AG Call Handler
# MES Operation  : ag_calls_S2M_UnloadingMaterial
#
# Description:
#   1. Processes AGUnloadingMaterial when the PLC Handshake changes to 1.
#   2. Uses the handshake tag path only for dynamic PLC tag routing.
#   3. Reads RequestData and RequestAckNumber from the Siemens PLC.
#   4. Maps SourceFBS, RFIDNo, ItemID and ReasonCode to MES UnloadingInfo.
#   5. Builds and freezes MessageHeader plus UnloadingInfo under Inputs.
#   6. Treats exactly HTTP 200 as delivered and durably queues every eligible
#      non-200/timeout/no-response failure through the shared dispatcher.
#   7. Writes StatusCode 200 and copies RequestAckNumber only after delivery or
#      successful durable queue insertion.
#   8. Leaves Handshake 1 unchanged after validation or queue insertion failure.
#   9. Writes StatusCode, ResponseTimestamp and ResponseAckNumber first.
#  10. Writes Handshake last, only after all metadata writes succeed.
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
# MES Request Business Object:
# {
#     "EquipmentId": "IN11_E115_PCE_MIX21",
#     "ContainerNo": "HU",
#     "SerialNo": "JR-001",
#     "Reason": "Testing"
# }
#
# PLC Response Mapping:
# -----------------------------------------------------------------------------
# Delivery outcome  | StatusCode | ResponseAckNumber      | Final Handshake
# -----------------------------------------------------------------------------
# HTTP 200          | 200        | Original request ACK   | 2
# Durable queue     | 200        | Original request ACK   | 2
# Queue/read failure| No write   | No write               | Remains 1
# Cancel/invalid    | 510        | Not overwritten        | Received value
#
# Version History
# -----------------------------------------------------------------------------
# Version | Date       | Author | Description
# -----------------------------------------------------------------------------
# 1.0     | 11-Sep-2026| Hari   | Initial framework-based implementation
# 1.1     | 11-Sep-2026| Hari   | Use Boolean value instead of object identity
#         |            |        | for Ignition/Jython ResultFlag handling
# 1.2     | 11-Sep-2026| Hari   | Map RequestData.SourceFBS to MES EquipmentId
# 1.3     | 11-Sep-2026| Hari   | Added asynchronous Store-and-Forward delivery
# 1.4     | 21-Sep-2026| Codex  | Allow empty optional business fields
###############################################################################

import system
import system.util
from scada_interface import audit, logger, message_header, router


SCHEMA = {
    "UnloadingMaterial.RequestAckNumber": {"required": True, "type": "str"},
    "UnloadingMaterial.RequestData": {"required": True, "type": "dict"},
    "UnloadingMaterial.RequestData.SourceFBS": {"required": False, "type": "str"},
    "UnloadingMaterial.RequestData.RFIDNo": {"required": False, "type": "str"},
    "UnloadingMaterial.RequestData.ItemID": {"required": False, "type": "str"},
    "UnloadingMaterial.RequestData.ReasonCode": {"required": False, "type": "str"}
}


# -----------------------------------------------------------------------------
# Function    : _debug
# Description : Emits config-controlled UnloadingMaterial diagnostics.
# -----------------------------------------------------------------------------
def _debug(ctx, config, step, message, extra=None):
    logger.diagnostic(ctx, config, step, message, extra)


# -----------------------------------------------------------------------------
# Function    : _unicode
# Description : Safely converts a value to Unicode for Ignition/Jython.
# -----------------------------------------------------------------------------
def _unicode(value, default_value=""):
    if value is None:
        return unicode(default_value)
    try:
        return unicode(value)
    except Exception:
        return unicode(default_value)


# -----------------------------------------------------------------------------
# Function    : _paths
# Description : Builds request-local PLC paths from the dynamically routed base.
# -----------------------------------------------------------------------------
def _paths(config):
    base = config.get("ag_tag_base_path")
    return {
        "RequestData": base + "RequestData",
        "RequestAckNumber": base + "RequestAckNumber",
        "StatusCode": base + "StatusCode",
        "ResponseTimestamp": base + "ResponseTimestamp",
        "ResponseAckNumber": base + "ResponseAckNumber",
        "Handshake": base + "Handshake"
    }


# -----------------------------------------------------------------------------
# Function    : _validate_qualities
# Description : Raises when any PLC read or write quality is not good.
# -----------------------------------------------------------------------------
def _validate_qualities(paths, qualities):
    failures = []
    for index in range(len(qualities)):
        if not qualities[index].isGood():
            failures.append("%s=%s" % (paths[index], qualities[index]))
    if failures:
        raise Exception("PLC tag operation failed: %s" % ", ".join(failures))


# -----------------------------------------------------------------------------
# Function    : _as_document_dict
# Description : Normalizes an Ignition Document, dictionary, or JSON string.
# -----------------------------------------------------------------------------
def _as_document_dict(value):
    result = value
    if isinstance(result, basestring):
        result = system.util.jsonDecode(_unicode(result))
    elif hasattr(result, "toDict"):
        result = result.toDict()
    if not isinstance(result, dict):
        raise Exception(
            "PLC RequestData must be a JSON object. ActualType=%s"
            % result.__class__.__name__
        )
    return result


# -----------------------------------------------------------------------------
# Function    : read_ag_request
# Description : Reads and decodes the PLC unloading request and ACK together.
# -----------------------------------------------------------------------------
def read_ag_request(ctx, config, handshake_tag_path, handshake_value):
    paths = _paths(config)
    read_paths = [paths["RequestData"], paths["RequestAckNumber"]]
    _debug(ctx, config, "UNLOADING_MATERIAL_PLC_READ", "Reading PLC request tags", {
        "handshake_tag_path": handshake_tag_path,
        "handshake_value": handshake_value,
        "read_paths": read_paths,
        "route_equipment_id": config.get("route_equipment_id")
    })
    results = system.tag.readBlocking(read_paths)
    _validate_qualities(read_paths, [result.quality for result in results])

    if results[0].value is None or _unicode(results[0].value).strip() == "":
        raise Exception("PLC RequestData is null or empty")
    if results[1].value is None or _unicode(results[1].value).strip() == "":
        raise Exception("PLC RequestAckNumber is null or empty")

    request_data = _as_document_dict(results[0].value)
    ack = _unicode(results[1].value).strip()
    ctx["business_reference"] = ack
    _debug(ctx, config, "UNLOADING_MATERIAL_PLC_READ", "PLC request read successfully", {
        "request_ack_number": ack,
        "container_no": _unicode(request_data.get("RFIDNo")).strip(),
        "serial_no": _unicode(request_data.get("ItemID")).strip()
    })
    return {
        "UnloadingMaterial": {
            "RequestAckNumber": ack,
            "RequestData": request_data
        }
    }


# -----------------------------------------------------------------------------
# Function    : validate_business_rules
# Description : Captures business context for the PLC unloading request.
# -----------------------------------------------------------------------------
def validate_business_rules(ctx, payload, config):
    data = payload.get("UnloadingMaterial", {})
    request = data.get("RequestData", {})
    ctx["business_reference"] = data.get("RequestAckNumber")
    ctx["source_system"] = "SCADA"
    ctx["target_system"] = "MES"
    _debug(ctx, config, "UNLOADING_MATERIAL_MAPPING", "PLC request accepted", {
        "equipment_id": _unicode(request.get("SourceFBS")).strip(),
        "route_equipment_id": config.get("route_equipment_id"),
        "container_no": _unicode(request.get("RFIDNo")).strip(),
        "serial_no": _unicode(request.get("ItemID")).strip(),
        "reason": _unicode(request.get("ReasonCode")).strip()
    })
    return True


# -----------------------------------------------------------------------------
# Function    : _mes_business_payload
# Description : Maps PLC RequestData into MES UnloadingInfo.
# -----------------------------------------------------------------------------
def _mes_business_payload(payload, config):
    request = payload["UnloadingMaterial"]["RequestData"]
    return {
        "EquipmentId": _unicode(request.get("SourceFBS")).strip(),
        "ContainerNo": _unicode(request.get("RFIDNo")).strip(),
        "SerialNo": _unicode(request.get("ItemID")).strip(),
        "Reason": _unicode(request.get("ReasonCode")).strip()
    }


# -----------------------------------------------------------------------------
# Function    : process
# Description : Attempts MES once and returns DELIVERED or durable QUEUED result.
# -----------------------------------------------------------------------------
def process(ctx, payload, config):
    request_payload = _mes_business_payload(payload, config)
    _debug(ctx, config, "UNLOADING_MATERIAL_MES_ATTEMPT", "Sending unloading request to MES", {
        "mes_url": config.get("mes_url"),
        "request_ack_number": payload["UnloadingMaterial"].get("RequestAckNumber"),
        "equipment_id": request_payload.get("EquipmentId"),
        "container_no": request_payload.get("ContainerNo"),
        "serial_no": request_payload.get("SerialNo")
    })
    envelope = message_header.wrap_outbound(ctx, config, request_payload)
    audit.save_payload(ctx, "MES_REQUEST", envelope,
                       config.get("payload_logging_mode", "HASH_ONLY"))
    audit.log_step(ctx, "MES_REST_CALL", "IN_PROGRESS")
    delivery = router.submit_async_mes_request(
        ctx, config, request_payload, envelope
    )
    mes_result = delivery.get("mes_result") or {}
    audit.save_payload(ctx, "MES_RESPONSE", mes_result,
                       config.get("payload_logging_mode", "HASH_ONLY"))
    audit.log_step(ctx, "MES_REST_CALL", delivery["outcome"], {
        "delivery_outcome": delivery["outcome"],
        "mes_http_status": mes_result.get("status_code"),
        "queue_id": delivery.get("queue_id")
    })
    result = {
        "StatusCode": 200,
        "ResponseAckNumber": payload["UnloadingMaterial"]["RequestAckNumber"],
        "Handshake": 2,
        "DeliveryOutcome": delivery["outcome"],
        "QueueId": delivery.get("queue_id")
    }
    _debug(ctx, config, "UNLOADING_MATERIAL_MES_CALL", "MES unloading submission resolved", {
        "status_code": result["StatusCode"],
        "delivery_outcome": result["DeliveryOutcome"],
        "mes_http_status": mes_result.get("status_code"),
        "queue_id": result["QueueId"]
    })
    return result


# -----------------------------------------------------------------------------
# Function    : is_success_result
# Description : Treats delivered and durably queued PLC acknowledgements as good.
# -----------------------------------------------------------------------------
def is_success_result(result):
    return result.get("StatusCode") == 200


# -----------------------------------------------------------------------------
# Function    : _write_metadata
# Description : Writes PLC metadata first and the completion handshake last.
# -----------------------------------------------------------------------------
def _write_metadata(config, status_code, ack_number, handshake):
    paths = _paths(config)
    # ResponseTimestamp is an OPC UA LDT/DateTime exposed as java.util.Date.
    # A formatted string is intentionally not used because tag coercion fails.
    response_timestamp = system.date.now()
    final_ack = _unicode(ack_number).strip() if int(status_code) == 200 else ""
    write_paths = [
        paths["StatusCode"], paths["ResponseTimestamp"], paths["ResponseAckNumber"]
    ]
    write_values = [int(status_code), response_timestamp, final_ack]
    results = system.tag.writeBlocking(write_paths, write_values)
    _validate_qualities(write_paths, results)

    # Handshake must be last so PLC never consumes partially written metadata.
    handshake_results = system.tag.writeBlocking(
        [paths["Handshake"]], [int(handshake)]
    )
    _validate_qualities([paths["Handshake"]], handshake_results)


# -----------------------------------------------------------------------------
# Function    : write_ag_response
# Description : Writes accepted delivery/queue result to PLC metadata tags.
# -----------------------------------------------------------------------------
def write_ag_response(ctx, config, result):
    _debug(ctx, config, "UNLOADING_MATERIAL_PLC_WRITE", "Writing MES result to PLC", {
        "status_code": result.get("StatusCode"),
        "response_ack_number": result.get("ResponseAckNumber", ""),
        "handshake": result.get("Handshake"),
        "delivery_outcome": result.get("DeliveryOutcome"),
        "queue_id": result.get("QueueId")
    })
    _write_metadata(
        config,
        result["StatusCode"],
        result.get("ResponseAckNumber", ""),
        result["Handshake"]
    )
    _debug(ctx, config, "UNLOADING_MATERIAL_PLC_WRITE", "PLC metadata and handshake written successfully")


# -----------------------------------------------------------------------------
# Function    : write_ag_failure
# Description : Logs failure and intentionally leaves Handshake=1 unchanged.
# -----------------------------------------------------------------------------
def write_ag_failure(ctx, config, message):
    logger.error(ctx, "UNLOADING_MATERIAL_FAILURE", "FAILED", message, {
        "plc_completion_written": False,
        "handshake_preserved": 1
    })


# -----------------------------------------------------------------------------
# Function    : handle_ag_handshake
# Description : Writes 510/time without overwriting ACK for invalid states.
# -----------------------------------------------------------------------------
def handle_ag_handshake(ctx, config, handshake_value):
    _debug(ctx, config, "UNLOADING_MATERIAL_HANDSHAKE", "Handling non-request handshake", {
        "handshake_value": handshake_value
    })
    paths = _paths(config)
    response_timestamp = system.date.now()
    metadata_paths = [paths["StatusCode"], paths["ResponseTimestamp"]]
    metadata_values = [510, response_timestamp]
    results = system.tag.writeBlocking(metadata_paths, metadata_values)
    _validate_qualities(metadata_paths, results)
    handshake_results = system.tag.writeBlocking(
        [paths["Handshake"]], [int(handshake_value)]
    )
    _validate_qualities([paths["Handshake"]], handshake_results)
    return {
        "StatusCode": 510,
        "Handshake": handshake_value
    }