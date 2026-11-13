###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : ag_call_S2M_OperationResult.py
# Interface      : S2M.OperationResult
# Module         : Asynchronous AG Call OperationResult Handler
#
# Description:
# Reads a list of PLC operation results, maps and freezes the complete MES
# envelope, attempts MES once, and persists every eligible non-200/transport
# failure through the shared Store-and-Forward service. PLC status 200 is
# written only after HTTP 200 delivery or successful durable queue insertion.
# Persistent retries never access PLC tags.
#
# Delivery contract:
#   HTTP 200             -> DELIVERED -> PLC StatusCode 200
#   Any non-200/timeout  -> QUEUED    -> PLC StatusCode 200 after SQL commit
#   Queue/read failure   -> no PLC completion; Handshake remains 1
#   Handshake 3/other    -> StatusCode 510; ResponseAckNumber is not written
#
# Author         : Hari
# Version        : 2.1
# Date           : 27-Sep-2026
#
# Change History
# -----------------------------------------------------------------------------
# Sl No | Version | Date        | Author | Fix/Change
# -----------------------------------------------------------------------------
# 1     | 1.0     | 24-Jul-2026 | Hari   | Initial synchronous implementation
# 2     | 2.0     | 11-Sep-2026 | Hari   | List input and asynchronous durable delivery
# 3     | 2.1     | 27-Sep-2026 | Hari   | Production-type OperationResult mapping
# -----------------------------------------------------------------------------
###############################################################################

import system
import system.util
from scada_interface import audit, logger, message_header, router


SCHEMA = {
       "OperationResult.RequestData": {"required": True, "type": "list"}
}


# -----------------------------------------------------------------------------
# Function    : _debug
# Description : Emits config-controlled OperationResult diagnostic records.
# -----------------------------------------------------------------------------
def _debug(ctx, config, step, message, extra=None):
    logger.diagnostic(ctx, config, step, message, extra or {})


# -----------------------------------------------------------------------------
# Function    : _text
# Description : Safely converts a PLC value to Unicode for Jython.
# -----------------------------------------------------------------------------
def _text(value):
    if value is None:
        return ""
    try:
        return unicode(value)
    except Exception:
        return str(value)


# -----------------------------------------------------------------------------
# Function    : _paths
# Description : Builds PLC paths from the request-local dynamic AG base.
# -----------------------------------------------------------------------------
def _paths(config):
    base = config.get("ag_tag_base_path")
    return dict((name, base + name) for name in (
        "Handshake", "SenderFBS", "RequestData", "RequestAckNumber", "StatusCode",
        "ResponseTimestamp", "ResponseAckNumber"
    ))


# -----------------------------------------------------------------------------
# Function    : _validate_results
# Description : Validates tag result count and every Ignition quality.
# -----------------------------------------------------------------------------
def _validate_results(paths, results):
    if len(results) != len(paths):
        raise Exception("PLC tag operation returned an unexpected result count")
    failures = []
    for index in range(len(paths)):
        quality = getattr(results[index], "quality", results[index])
        if not quality.isGood():
            failures.append("%s=%s" % (paths[index], quality))
    if failures:
        raise Exception("PLC tag operation failed: %s" % ", ".join(failures))


# -----------------------------------------------------------------------------
# Function    : _detach
# Description : Detaches nested Ignition/Java collections to plain values.
# -----------------------------------------------------------------------------
def _detach(value):
    if isinstance(value, dict) or hasattr(value, "items"):
        return dict((_text(key), _detach(child)) for key, child in value.items())
    if isinstance(value, (list, tuple)):
        return [_detach(child) for child in value]
    if hasattr(value, "toDict"):
        converted = value.toDict()
        if converted is not value:
            return _detach(converted)
    if hasattr(value, "toList"):
        converted = value.toList()
        if converted is not value:
            return _detach(converted)
    return value


# -----------------------------------------------------------------------------
# Function    : _document_array
# Description : Normalizes Document/native/JSON input to a detached list.
# -----------------------------------------------------------------------------
def _document_array(value):
    text_value = _text(value).strip()
    decoded = None
    if isinstance(value, basestring) or text_value.startswith("["):
        try:
            decoded = system.util.jsonDecode(text_value)
        except Exception:
            if isinstance(value, basestring):
                raise
    if decoded is None:
        decoded = system.util.jsonDecode(system.util.jsonEncode(value))
    decoded = _detach(decoded)
    if not isinstance(decoded, list):
        raise Exception("PLC RequestData must be a JSON array")
    return decoded


# -----------------------------------------------------------------------------
# Function    : _item_object
# Description : Normalizes one list member into a dictionary.
# -----------------------------------------------------------------------------
def _item_object(value, index=None):
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        pairs = []
        for entry in value:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                pairs = []
                break
            pairs.append((_text(entry[0]), _detach(entry[1])))
        if pairs:
            return dict(pairs)
    return {}


# -----------------------------------------------------------------------------
# Function    : _optional_text
# Description : Returns a trimmed string or the empty-string default.
# -----------------------------------------------------------------------------
def _optional_text(source, field):
    return _text(source.get(field)).strip()


# -----------------------------------------------------------------------------
# Function    : _optional_number
# Description : Preserves a supplied value or returns the numeric zero default.
# -----------------------------------------------------------------------------
def _optional_number(source, field):
    value = source.get(field)
    return 0 if value is None or value == "" else value


# -----------------------------------------------------------------------------
# Function    : _optional_array
# Description : Preserves a list or returns the empty-list default.
# -----------------------------------------------------------------------------
def _optional_array(source, field):
    value = source.get(field)
    return value if isinstance(value, list) else []


def _map_material(items):
    return [{
        "MaterialBatchNo": _optional_text(item, "BatchID"),
        "SourceHUNo": _optional_text(item, "SourceFBS"),
        "ConsumedQuantity": _optional_number(item, "ConsumedQuantity"),
        "FeedingLocation": _optional_text(item, "DestinationFBS")
    } for item in [_item_object(value) for value in items]]


def _map_parameters(items):
    return [{
        "ParameterCode": _optional_text(item, "ParameterCode"),
        "ParameterName": _optional_text(item, "ParameterName"),
        "ActualValue": _optional_number(item, "ActualValue"),
        "ParameterResult": _optional_text(item, "ParameterResult")
    } for item in [_item_object(value) for value in items]]


def _map_transfers(items):
    return [{
        "ItemId": _optional_text(item, "ItemID"),
        "SourceEquipmentId": _optional_text(item, "SourceFBS"),
        "DestinationEquipmentId": _optional_text(item, "DestinationFBS"),
        "QuantityTransferred": _optional_number(item, "QuantityTransferred"),
        "UoM": _optional_text(item, "UoM")
    } for item in [_item_object(value) for value in items]]


def _map_mixing(item, materials, parameters):
    transfers = _optional_array(item, "TransferDetails")
    return [{
        "StepId": _optional_text(step, "StepID"),
        "StepStartTime": _optional_text(step, "StepStartTime"),
        "StepEndTime": _optional_text(step, "StepEndTime"),
        "MaterialLoadingDetails": _map_material(materials),
        "ParameterResults": _map_parameters(parameters),
        "TransferDetails": _map_transfers(transfers)
    } for step in [_item_object(value) for value in
                   _optional_array(item, "MixingStepResults")]]


def _map_rolls(item, materials, parameters):
    return [{
        "RFIDCore": _optional_text(roll, "ItemID"),
        "ProducedOKQuantity": _optional_number(roll, "ProducedOKQuantity"),
        "NGQuantity": _optional_number(roll, "NGQuantity"),
        "UoM": _optional_text(roll, "UoM"),
        "StartTime": _optional_text(roll, "StartTime"),
        "CompletionTime": _optional_text(roll, "CompletionTime"),
        "MaterialConsumption": _map_material(materials),
        "ParameterResults": _map_parameters(parameters)
    } for roll in [_item_object(value) for value in
                   _optional_array(item, "RollInfoItems")]]


def _map_serial_items(item, source_field, materials, parameters):
    mapped = []
    for value in _optional_array(item, source_field):
        serial = _item_object(value)
        result = {
            "SerialNo": _optional_text(serial, "SerialNo"),
            "SlotId": _optional_text(serial, "SlotID"),
            "InboundTime": _optional_text(serial, "InboundTime"),
            "OutboundTime": _optional_text(serial, "OutboundTime"),
            "OverallResult": _optional_text(serial, "OverallResult"),
            "MaterialConsumption": _map_material(materials),
            "ParameterResults": _map_parameters(parameters)
        }
        if source_field == "SerialInfo":
            result["PastSerialNo"] = _optional_text(serial, "PastSerialNo")
        mapped.append(result)
    return mapped


def _map_operation(item, equipment_id):
    production_type = _optional_text(item, "ProductionType")
    materials = _optional_array(item, "MaterialConsumption")
    parameters = _optional_array(item, "ParameterResults")
    result = {
        "ProductionOrderNo": _optional_text(item, "WorkOrderID"),
        "BatchId": "",
        "ProducedOKQuantity": 0,
        "NGQuantity": 0,
        "UoM": _optional_text(item, "UoM"),
        "OperationSequence": _optional_text(item, "OperationSequence"),
        "RecipeId": _optional_text(item, "RecipeID"),
        "EquipmentId": equipment_id,
        "OperationStartTime": "",
        "OperationEndTime": "",
        "ProductionType": production_type,
        "OperationFlag": _optional_number(item, "OperationFlag"),
        "MixingStepResults": [],
        "RollInfoItems": [],
        "IsTray": _optional_number(item, "IsTray"),
        "TrayNo": _optional_text(item, "TrayNo"),
        "JRInfo": [],
        "SerialInfo": []
    }
    if production_type == "M":
        result["MixingStepResults"] = _map_mixing(item, materials, parameters)
    elif production_type == "E":
        result["RollInfoItems"] = _map_rolls(item, materials, parameters)
    elif production_type == "S":
        result["JRInfo"] = _map_serial_items(
            item, "JRInfo", materials, parameters
        )
    elif production_type == "C":
        result["SerialInfo"] = _map_serial_items(
            item, "SerialInfo", materials, parameters
        )
    return result


# -----------------------------------------------------------------------------
# Function    : read_ag_request
# Description : Reads and freezes RequestData and ACK from PLC.
# -----------------------------------------------------------------------------
def read_ag_request(ctx, config, handshake_tag_path, handshake_value):
    paths = _paths(config)
    read_paths = [
        paths["RequestData"], paths["RequestAckNumber"], paths["SenderFBS"]
    ]
    _debug(ctx, config, "OPERATION_RESULT_PLC_READ", "Reading PLC request tags", {
        "handshake_tag_path": handshake_tag_path,
        "handshake_value": handshake_value,
        "route_equipment_id": config.get("route_equipment_id"),
        "read_paths": read_paths
    })
    results = system.tag.readBlocking(read_paths)
    _validate_results(read_paths, results)
    if results[0].value is None:
        raise Exception("PLC RequestData contains null")
    if results[1].value is None or not _text(results[1].value).strip():
        raise Exception("PLC RequestAckNumber contains null or empty value")

    items = _document_array(results[0].value)
    ack = _text(results[1].value).strip()
    sender_fbs = _text(results[2].value).strip()
    ctx["business_reference"] = ack
    _debug(ctx, config, "OPERATION_RESULT_PLC_READ", "PLC request captured", {
        "request_ack_number": ack,
        "item_count": len(items)
    })
    return {"OperationResult": {
        "RequestAckNumber": ack,
        "RequestData": items,
        "SenderFBS": sender_fbs
    }}


# -----------------------------------------------------------------------------
# Function    : validate_business_rules
# Description : Creates the optional-field, production-type MES mapping.
# -----------------------------------------------------------------------------
def validate_business_rules(ctx, payload, config):
    data = payload["OperationResult"]
    items = data.get("RequestData")
    if not isinstance(items, list):
        items = []
    equipment_id = _text(data.get("SenderFBS")).strip()
    mapped_items = []
    for index in range(len(items)):
        item = _item_object(items[index], index)
        items[index] = item
        mapped_items.append(_map_operation(item, equipment_id))

    data["MappedRequest"] = mapped_items
    ctx["business_reference"] = data["RequestAckNumber"]
    ctx["business_equipment_id"] = equipment_id
    _debug(ctx, config, "OPERATION_RESULT_MAPPING", "PLC request mapped", {
        "equipment_id": equipment_id,
        "item_count": len(mapped_items)
    })
    return True


# -----------------------------------------------------------------------------
# Function    : process
# Description : Attempts MES once and returns DELIVERED or durable QUEUED result.
# -----------------------------------------------------------------------------
def process(ctx, payload, config):
    data = payload["OperationResult"]
    business = data["MappedRequest"]
    # Freeze the shared RequestJSON envelope once for delivery and replay.
    envelope = message_header.wrap_outbound(ctx, config, business)
    audit.save_payload(ctx, "MES_REQUEST", envelope,
                       config.get("payload_logging_mode", "HASH_ONLY"))
    audit.log_step(ctx, "MES_REST_CALL", "IN_PROGRESS")
    _debug(ctx, config, "OPERATION_RESULT_MES_ATTEMPT", "Submitting operation result", {
        "mes_url": config.get("mes_url"),
        "request_ack_number": data["RequestAckNumber"],
        "item_count": len(business)
    })
    delivery = router.submit_async_mes_request(ctx, config, business, envelope)
    mes_result = delivery.get("mes_result") or {}
    audit.save_payload(ctx, "MES_RESPONSE", mes_result,
                       config.get("payload_logging_mode", "HASH_ONLY"))
    audit.log_step(ctx, "MES_REST_CALL", delivery["outcome"], {
        "delivery_outcome": delivery["outcome"],
        "mes_http_status": mes_result.get("status_code"),
        "queue_id": delivery.get("queue_id")
    })
    _debug(ctx, config, "OPERATION_RESULT_MES_RESULT", "Submission resolved", {
        "delivery_outcome": delivery["outcome"],
        "mes_http_status": mes_result.get("status_code"),
        "queue_id": delivery.get("queue_id")
    })
    return {
        "StatusCode": 200,
        "ResponseAckNumber": data["RequestAckNumber"],
        "Handshake": 2,
        "DeliveryOutcome": delivery["outcome"],
        "QueueId": delivery.get("queue_id")
    }


# -----------------------------------------------------------------------------
# Function    : _write_metadata
# Description : Writes completion metadata first and handshake separately last.
# -----------------------------------------------------------------------------
def _write_metadata(config, status_code, ack_number, handshake):
    paths = _paths(config)
    metadata_paths = [
        paths["StatusCode"], paths["ResponseTimestamp"],
        paths["ResponseAckNumber"]
    ]
    metadata_values = [int(status_code), system.date.now(), ack_number]
    results = system.tag.writeBlocking(metadata_paths, metadata_values)
    _validate_results(metadata_paths, results)
    handshake_paths = [paths["Handshake"]]
    results = system.tag.writeBlocking(handshake_paths, [int(handshake)])
    _validate_results(handshake_paths, results)


# -----------------------------------------------------------------------------
# Function    : write_ag_response
# Description : Writes accepted delivery/queue completion to PLC.
# -----------------------------------------------------------------------------
def write_ag_response(ctx, config, result):
    _debug(ctx, config, "OPERATION_RESULT_PLC_WRITE", "Writing PLC completion", {
        "status_code": result["StatusCode"],
        "response_ack_number": result["ResponseAckNumber"],
        "delivery_outcome": result.get("DeliveryOutcome"),
        "queue_id": result.get("QueueId")
    })
    _write_metadata(
        config, result["StatusCode"], result["ResponseAckNumber"],
        result["Handshake"]
    )
    _debug(ctx, config, "OPERATION_RESULT_PLC_WRITE", "PLC metadata and handshake written")


# -----------------------------------------------------------------------------
# Function    : write_ag_failure
# Description : Logs failure and intentionally leaves Handshake=1 unchanged.
# -----------------------------------------------------------------------------
def write_ag_failure(ctx, config, message):
    logger.error(ctx, "OPERATION_RESULT_FAILURE", "FAILED", message, {
        "plc_completion_written": False,
        "handshake_preserved": 1
    })


# -----------------------------------------------------------------------------
# Function    : handle_ag_handshake
# Description : Writes 510/time without overwriting ACK for invalid states.
# -----------------------------------------------------------------------------
def handle_ag_handshake(ctx, config, handshake_value):
    paths = _paths(config)
    metadata_paths = [paths["StatusCode"], paths["ResponseTimestamp"]]
    results = system.tag.writeBlocking(metadata_paths, [510, system.date.now()])
    _validate_results(metadata_paths, results)
    handshake_paths = [paths["Handshake"]]
    results = system.tag.writeBlocking(handshake_paths, [int(handshake_value)])
    _validate_results(handshake_paths, results)
    _debug(ctx, config, "OPERATION_RESULT_HANDSHAKE", "Invalid handshake response written", {
        "handshake_value": handshake_value,
        "response_ack_written": False
    })
    return {"StatusCode": 510, "Handshake": handshake_value}


# -----------------------------------------------------------------------------
# Function    : is_success_result
# Description : Treats delivered and durably queued PLC acknowledgements as good.
# -----------------------------------------------------------------------------
def is_success_result(result):
    return result.get("StatusCode") == 200