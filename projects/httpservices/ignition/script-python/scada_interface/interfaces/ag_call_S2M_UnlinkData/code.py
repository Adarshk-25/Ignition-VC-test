###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : ag_call_S2M_UnlinkData.py
# Interface      : S2M.UnlinkData
# Module         : AG Call UnlinkData Handler
#
# Description:
# Reads and validates an AGUnlink PLC request, submits one prepared MES request,
# persists unsuccessful delivery for shared retry, and acknowledges the PLC.
# The trigger-derived parent is used for every PLC operation.
#
# Author         : Hari
# Version        : 1.0
# Date           : 09-Sep-2026
#
# Change History
# -----------------------------------------------------------------------------
# Sl No | Version | Date        | Author | Fix/Change
# -----------------------------------------------------------------------------
# 1     | 1.0     | 09-Sep-2026 | Hari   | Initial S2M.UnlinkData implementation
# -----------------------------------------------------------------------------
###############################################################################

import system
from scada_interface import audit, logger, message_header, router


SCHEMA = {
    "UnlinkData.SenderFBS": {"required": True, "type": "str"},
    "UnlinkData.RequestAckNumber": {"required": True, "type": "int"},
    "UnlinkData.ContainerId": {"required": True, "type": "str"},
    "UnlinkData.ContainerType": {"required": True, "type": "str"},
    "UnlinkData.RequestData": {"required": True, "type": "list"}
}


# -----------------------------------------------------------------------------
# Function    : _debug
# Description : Emits config-controlled UnlinkData diagnostic records.
# -----------------------------------------------------------------------------
def _debug(ctx, config, step, message, details=None):
    logger.diagnostic(ctx, config, step, message, details or {})


# -----------------------------------------------------------------------------
# Function    : _text
# Description : Converts PLC string values without accepting nulls implicitly.
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
# Description : Builds paths exclusively from the validated trigger parent.
# -----------------------------------------------------------------------------
def _paths(config):
    base = config.get("ag_tag_base_path")
    return dict((name, base + name) for name in (
        "Handshake", "SenderFBS", "RequestAckNumber", "RequestTimestamp",
        "ContainerId", "ContainerType", "RequestData", "StatusCode",
        "ResponseAckNumber", "ResponseTimestamp", "ResponseData"
    ))


# -----------------------------------------------------------------------------
# Function    : _validate_results
# Description : Validates result count and every Ignition tag quality.
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
# Description : Detaches ordinary nested collections into plain Jython values.
# -----------------------------------------------------------------------------
def _detach(value):
    # system.util.jsonDecode returns PyDictionary on some Ignition/Jython
    # versions. Check mapping behavior before adapter conversion because some
    # mapping implementations also expose toList().
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
# Description : Normalizes an Ignition Document value through its JSON contract.
# -----------------------------------------------------------------------------
def _document_array(value):
    # Calling toDict recursively is unsafe for some Ignition Document adapters.
    # The Ignition JSON codec reliably removes adapter/Java object references.
    text_value = _text(value).strip()
    decoded = None
    if isinstance(value, basestring) or text_value.startswith("["):
        # PyDocumentObjectAdapter.__str__ retains the original JSON object
        # structure more reliably than jsonEncode(adapter) in some versions.
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
# Function    : _unlink_item
# Description : Normalizes one decoded unlink object without positional mapping.
# -----------------------------------------------------------------------------
def _unlink_item(value, index):
    if isinstance(value, dict):
        return value
    # Certain Ignition adapters expose a JSON object as [[key, value], ...].
    # Accept that representation only when every entry is an explicit pair.
    if isinstance(value, list):
        pairs = []
        for entry in value:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                pairs = []
                break
            pairs.append((_text(entry[0]), _detach(entry[1])))
        if pairs:
            return dict(pairs)
    raise Exception("RequestData[%s] must be an object. ActualType=%s"
                    % (index, value.__class__.__name__))


# -----------------------------------------------------------------------------
# Function    : _integer
# Description : Requires a true integral PLC value and explicitly rejects Boolean.
# -----------------------------------------------------------------------------
def _integer(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, long)):
        raise Exception("%s must be an integer" % field)
    return int(value)


# -----------------------------------------------------------------------------
# Function    : read_ag_request
# Description : Reads, detaches and stability-checks the complete PLC request.
# -----------------------------------------------------------------------------
def read_ag_request(ctx, config, handshake_tag_path, handshake_value):
    paths = _paths(config)
    names = ["SenderFBS", "RequestAckNumber", "RequestTimestamp",
             "ContainerId", "ContainerType", "RequestData"]
    read_paths = [paths[name] for name in names]
    _debug(ctx, config, "UNLINK_DATA_PLC_READ", "Reading PLC unlink request",
           {"trigger_tag_path": handshake_tag_path, "read_paths": read_paths})
    results = system.tag.readBlocking(read_paths)
    _validate_results(read_paths, results)
    values = {}
    for index in range(len(names)):
        if names[index] == "RequestData":
            # Normalize the original tag value, not a potentially recursive
            # toDict result exposed by an Ignition Document adapter.
            values[names[index]] = _document_array(results[index].value)
        else:
            values[names[index]] = _detach(results[index].value)

    stable_names = ["Handshake", "SenderFBS", "RequestAckNumber", "RequestTimestamp"]
    stable_paths = [paths[name] for name in stable_names]
    stable = system.tag.readBlocking(stable_paths)
    _validate_results(stable_paths, stable)
    stable_values = dict((stable_names[index], _detach(stable[index].value))
                         for index in range(len(stable_names)))
    if _integer(stable_values["Handshake"], "Handshake") != 1:
        raise Exception("PLC Handshake changed during request capture")
    for name in stable_names[1:]:
        if stable_values[name] != values[name]:
            raise Exception("PLC %s changed during request capture" % name)

    ctx["business_reference"] = str(values["RequestAckNumber"])
    return {"UnlinkData": values}


# -----------------------------------------------------------------------------
# Function    : validate_business_rules
# Description : Validates the full unlink batch and binds audit context.
# -----------------------------------------------------------------------------
def validate_business_rules(ctx, payload, config):
    data = payload["UnlinkData"]
    for field in ("SenderFBS", "RequestTimestamp", "ContainerId", "ContainerType"):
        if not isinstance(data.get(field), basestring) or not data[field].strip():
            raise Exception("%s must be a nonblank string" % field)
    data["RequestAckNumber"] = _integer(data.get("RequestAckNumber"), "RequestAckNumber")
    message_header.parse_event_timestamp(data["RequestTimestamp"])
    items = data.get("RequestData")
    if not isinstance(items, list) or not items:
        raise Exception("RequestData must be a nonempty array")
    for index in range(len(items)):
        item = _unlink_item(items[index], index)
        items[index] = item
        for field in ("ItemID", "RFID"):
            if not isinstance(item.get(field), basestring) or not item[field].strip():
                raise Exception("RequestData[%s].%s must be a nonblank string" % (index, field))
        item["SlotNo"] = _integer(item.get("SlotNo"), "RequestData[%s].SlotNo" % index)
    ctx["equipment_id"] = data["SenderFBS"].strip()
    ctx["business_reference"] = str(data["RequestAckNumber"])
    _debug(ctx, config, "UNLINK_DATA_MAPPING", "PLC unlink request validated",
           {"equipment_id": ctx["equipment_id"], "item_count": len(items),
            "request_ack_number": data["RequestAckNumber"]})
    return True


# -----------------------------------------------------------------------------
# Function    : _business_payload
# Description : Maps captured PLC fields to the MES UnlinkData business object.
# -----------------------------------------------------------------------------
def _business_payload(data):
    return {
        "EquipmentId": data["SenderFBS"].strip(),
        "ContainerId": data["ContainerId"].strip(),
        "ContainerType": data["ContainerType"],
        "UnlinkTime": data["RequestTimestamp"],
        "UnlinkInfos": [{"SerialNo": item["ItemID"].strip(),
                         "RfidNo": item["RFID"].strip(),
                         "SlotNo": item["SlotNo"]} for item in data["RequestData"]]
    }


# -----------------------------------------------------------------------------
# Function    : process
# Description : Attempts MES once and returns delivered or durably queued outcome.
# -----------------------------------------------------------------------------
def process(ctx, payload, config):
    data = payload["UnlinkData"]
    business = _business_payload(data)
    envelope = message_header.wrap_outbound(ctx, config, business)
    audit.save_payload(ctx, "MES_REQUEST", envelope,
                       config.get("payload_logging_mode", "HASH_ONLY"))
    audit.log_step(ctx, "MES_REST_CALL", "IN_PROGRESS")
    delivery = router.submit_async_mes_request(ctx, config, business, envelope)
    mes_result = delivery.get("mes_result") or {}
    audit.save_payload(ctx, "MES_RESPONSE", mes_result,
                       config.get("payload_logging_mode", "HASH_ONLY"))
    audit.log_step(ctx, "MES_REST_CALL", delivery["outcome"], {
        "delivery_outcome": delivery["outcome"],
        "mes_http_status": mes_result.get("status_code")
    })
    return {
        "StatusCode": 200,
        "ResponseAckNumber": data["RequestAckNumber"],
        "ResponseTimestamp": data["RequestTimestamp"],
        "DeliveryOutcome": delivery["outcome"],
        "QueueId": delivery.get("queue_id")
    }


# -----------------------------------------------------------------------------
# Function    : write_ag_response
# Description : Writes metadata together, validates it, then writes handshake last.
# -----------------------------------------------------------------------------
def write_ag_response(ctx, config, result):
    paths = _paths(config)
    metadata_paths = [paths["StatusCode"], paths["ResponseAckNumber"],
                      paths["ResponseTimestamp"]]
    qualities = system.tag.writeBlocking(metadata_paths, [
        result["StatusCode"], result["ResponseAckNumber"], result["ResponseTimestamp"]
    ])
    _validate_results(metadata_paths, qualities)
    handshake_paths = [paths["Handshake"]]
    handshake_quality = system.tag.writeBlocking(handshake_paths, [2])
    _validate_results(handshake_paths, handshake_quality)


# -----------------------------------------------------------------------------
# Function    : handle_ag_handshake
# Description : Writes the defined 510 response for invalid numeric handshakes.
# -----------------------------------------------------------------------------
def handle_ag_handshake(ctx, config, handshake_value):
    paths = _paths(config)
    timestamp = ""
    read_paths = [paths["RequestTimestamp"]]
    results = system.tag.readBlocking(read_paths)
    if len(results) == 1 and results[0].quality.isGood() and results[0].value is not None:
        timestamp = _text(results[0].value)
    metadata_paths = [paths["StatusCode"], paths["ResponseData"],
                      paths["ResponseAckNumber"], paths["ResponseTimestamp"]]
    qualities = system.tag.writeBlocking(metadata_paths, [510, {}, 0, timestamp])
    _validate_results(metadata_paths, qualities)
    handshake_paths = [paths["Handshake"]]
    qualities = system.tag.writeBlocking(handshake_paths, [handshake_value])
    _validate_results(handshake_paths, qualities)
    return {"StatusCode": 510, "ResponseData": {}, "ResponseAckNumber": 0,
            "ResponseTimestamp": timestamp, "Handshake": handshake_value}


# -----------------------------------------------------------------------------
# Function    : write_ag_failure
# Description : Leaves handshake 1 unchanged after validation or system failure.
# -----------------------------------------------------------------------------
def write_ag_failure(ctx, config, error_message):
    logger.error(ctx, "UNLINK_DATA_FAILED", "FAILED", error_message)


# -----------------------------------------------------------------------------
# Function    : is_success_result
# Description : PLC acknowledgement succeeds for delivered and queued outcomes.
# -----------------------------------------------------------------------------
def is_success_result(result):
    return result.get("StatusCode") == 200