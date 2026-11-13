###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : ag_call_S2M_ScrapReport.py
# Interface      : S2M.ScrapReport
# Module         : Asynchronous AG Call ScrapReport Handler
#
# Description:
# Reads and validates an AGScrapReport PLC list, maps it to MES WastageReport,
# attempts delivery once, persists every non-200/transport failure through the
# shared Store-and-Forward service, and acknowledges the PLC only after MES
# delivery or durable queue acceptance. Persistent retries never access PLC.
#
# PLC RequestData item:
# {
#     "SourceFBS": "IN11.E115.PCE.MIX11",
#     "ReportTime": "2026-09-11T17:30:00Z",
#     "WorkOrderID": "WO-100001",
#     "ItemID": "CELL-SN-1001",
#     "BatchID": "BATCH-1001",
#     "Quantity": 10.5,
#     "UoM": "PCS",
#     "ReasonCode": "SCRAP-001"
# }
#
# Delivery contract:
#   HTTP 200             -> DELIVERED -> PLC StatusCode 200
#   Any non-200/timeout  -> QUEUED    -> PLC StatusCode 200 after SQL commit
#   Queue insertion fail -> no PLC completion; Handshake remains 1
#   Handshake 3/other    -> StatusCode 510; ResponseAckNumber is not written
#
# Author         : Hari
# Version        : 1.0
# Date           : 11-Sep-2026
#
# Change History
# -----------------------------------------------------------------------------
# Sl No | Version | Date        | Author | Fix/Change
# -----------------------------------------------------------------------------
# 1     | 1.0     | 11-Sep-2026 | Hari   | Initial asynchronous implementation
# -----------------------------------------------------------------------------
###############################################################################

import system
from scada_interface import audit, logger, message_header, router


SCHEMA = {
    "ScrapReport.RequestAckNumber": {"required": True, "type": "int"},
    "ScrapReport.WorkOrderType": {"required": True, "type": "int"},
    "ScrapReport.OprSequenceNo": {"required": True, "type": "str"},
    "ScrapReport.RequestData": {"required": True, "type": "list"}
}


# -----------------------------------------------------------------------------
# Function    : _debug
# Description : Emits config-controlled ScrapReport diagnostic records.
# -----------------------------------------------------------------------------
def _debug(ctx, config, step, message, details=None):
    logger.diagnostic(ctx, config, step, message, details or {})


# -----------------------------------------------------------------------------
# Function    : _text
# Description : Converts PLC values safely without accepting null implicitly.
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
# Description : Builds paths only from the request-local routed AG base.
# -----------------------------------------------------------------------------
def _paths(config):
    base = config.get("ag_tag_base_path")
    return dict((name, base + name) for name in (
        "Handshake", "RequestAckNumber", "WorkOrderType", "OprSequenceNo",
        "RequestData", "StatusCode", "ResponseAckNumber", "ResponseTimestamp"
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
# Description : Converts nested adapters/collections to detached Jython values.
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
# Description : Normalizes Document/native/JSON values to a detached list.
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
# Description : Normalizes one Document array member to a dictionary.
# -----------------------------------------------------------------------------
def _item_object(value, index):
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
    raise Exception("RequestData[%s] must be an object. ActualType=%s"
                    % (index, value.__class__.__name__))


# -----------------------------------------------------------------------------
# Function    : _integer
# Description : Requires an integral value and explicitly rejects Boolean.
# -----------------------------------------------------------------------------
def _integer(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, long)):
        raise Exception("%s must be an integer" % field)
    return int(value)


# -----------------------------------------------------------------------------
# Function    : _required_text
# Description : Validates and trims one mandatory string field.
# -----------------------------------------------------------------------------
def _required_text(source, field, path):
    if field not in source or source.get(field) is None:
        raise Exception("Mandatory field %s is missing or null" % path)
    value = _text(source.get(field)).strip()
    if not value:
        raise Exception("Mandatory field %s is empty" % path)
    return value


# -----------------------------------------------------------------------------
# Function    : _quantity
# Description : Validates a numeric scrap quantity while rejecting Boolean.
# -----------------------------------------------------------------------------
def _quantity(value, path):
    if value is None or isinstance(value, bool):
        raise Exception("%s must be numeric and cannot be Boolean" % path)
    if isinstance(value, (int, long, float)):
        return value
    text = _text(value).strip()
    try:
        if "." in text or "e" in text.lower():
            return float(text)
        return int(text)
    except Exception:
        raise Exception("%s must be numeric. Value=%s" % (path, text))


# -----------------------------------------------------------------------------
# Function    : read_ag_request
# Description : Reads and freezes the complete PLC request before MES delivery.
# -----------------------------------------------------------------------------
def read_ag_request(ctx, config, handshake_tag_path, handshake_value):
    paths = _paths(config)
    names = ["RequestAckNumber", "WorkOrderType", "OprSequenceNo", "RequestData"]
    read_paths = [paths[name] for name in names]
    _debug(ctx, config, "SCRAP_REPORT_PLC_READ", "Reading PLC scrap request", {
        "trigger_tag_path": handshake_tag_path,
        "route_equipment_id": config.get("route_equipment_id"),
        "read_paths": read_paths
    })
    results = system.tag.readBlocking(read_paths)
    _validate_results(read_paths, results)
    values = {}
    for index in range(len(names)):
        name = names[index]
        if name == "RequestData":
            values[name] = _document_array(results[index].value)
        else:
            values[name] = _detach(results[index].value)

    # Recheck request-control tags before accepting the captured list. This
    # detects a PLC sequence change without retaining live tag references.
    stable_names = ["Handshake", "RequestAckNumber", "WorkOrderType", "OprSequenceNo"]
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
    _debug(ctx, config, "SCRAP_REPORT_PLC_READ", "PLC scrap request captured", {
        "request_ack_number": values["RequestAckNumber"],
        "item_count": len(values["RequestData"])
    })
    return {"ScrapReport": values}


# -----------------------------------------------------------------------------
# Function    : validate_business_rules
# Description : Validates every item and binds business/audit context.
# -----------------------------------------------------------------------------
def validate_business_rules(ctx, payload, config):
    data = payload["ScrapReport"]
    data["RequestAckNumber"] = _integer(
        data.get("RequestAckNumber"), "RequestAckNumber"
    )
    data["WorkOrderType"] = _integer(data.get("WorkOrderType"), "WorkOrderType")
    data["OprSequenceNo"] = _required_text(
        data, "OprSequenceNo", "OprSequenceNo"
    )
    items = data.get("RequestData")
    if not isinstance(items, list) or not items:
        raise Exception("RequestData must be a nonempty array")

    common_source = None
    common_work_order = None
    for index in range(len(items)):
        item = _item_object(items[index], index)
        items[index] = item
        prefix = "RequestData[%s]." % index
        item["SourceFBS"] = _required_text(item, "SourceFBS", prefix + "SourceFBS")
        item["ReportTime"] = _required_text(item, "ReportTime", prefix + "ReportTime")
        message_header.parse_event_timestamp(item["ReportTime"])
        item["WorkOrderID"] = _required_text(item, "WorkOrderID", prefix + "WorkOrderID")
        item["ItemID"] = _required_text(item, "ItemID", prefix + "ItemID")
        item["BatchID"] = _required_text(item, "BatchID", prefix + "BatchID")
        item["Quantity"] = _quantity(item.get("Quantity"), prefix + "Quantity")
        item["UoM"] = _required_text(item, "UoM", prefix + "UoM")
        item["ReasonCode"] = _required_text(item, "ReasonCode", prefix + "ReasonCode")
        if common_source is None:
            common_source = item["SourceFBS"]
            common_work_order = item["WorkOrderID"]
        elif item["SourceFBS"] != common_source:
            raise Exception("All RequestData SourceFBS values must match")
        elif item["WorkOrderID"] != common_work_order:
            raise Exception("All RequestData WorkOrderID values must match")

    ctx["equipment_id"] = common_source
    ctx["business_reference"] = str(data["RequestAckNumber"])
    _debug(ctx, config, "SCRAP_REPORT_MAPPING", "PLC scrap request validated", {
        "equipment_id": common_source,
        "work_order_id": common_work_order,
        "work_order_type": data["WorkOrderType"],
        "operation_sequence": data["OprSequenceNo"],
        "item_count": len(items)
    })
    return True


# -----------------------------------------------------------------------------
# Function    : _business_payload
# Description : Maps the frozen PLC list to MES WastageReport/ScrapInfo.
# -----------------------------------------------------------------------------
def _business_payload(data):
    first = data["RequestData"][0]
    scrap_info = []
    for item in data["RequestData"]:
        scrap_info.append({
            "ReportTime": item["ReportTime"],
            "Container": item["ItemID"],
            "LotNo": item["BatchID"],
            "Quantity": item["Quantity"],
            "UOM": item["UoM"],
            "ReasonCode": item["ReasonCode"]
        })
    return {
        "EquipmentID": first["SourceFBS"],
        "WorkOrderNo": first["WorkOrderID"],
        "WorkOrderType": data["WorkOrderType"],
        "OprSequenceNo": data["OprSequenceNo"],
        "ScrapInfo": scrap_info
    }


# -----------------------------------------------------------------------------
# Function    : process
# Description : Attempts MES once and returns DELIVERED or durable QUEUED result.
# -----------------------------------------------------------------------------
def process(ctx, payload, config):
    data = payload["ScrapReport"]
    business = _business_payload(data)
    envelope = message_header.wrap_outbound(ctx, config, business)
    audit.save_payload(ctx, "MES_REQUEST", envelope,
                       config.get("payload_logging_mode", "HASH_ONLY"))
    audit.log_step(ctx, "MES_REST_CALL", "IN_PROGRESS")
    _debug(ctx, config, "SCRAP_REPORT_MES_ATTEMPT", "Submitting scrap report", {
        "mes_url": config.get("mes_url"),
        "equipment_id": business["EquipmentID"],
        "work_order_no": business["WorkOrderNo"],
        "item_count": len(business["ScrapInfo"])
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
    _debug(ctx, config, "SCRAP_REPORT_MES_RESULT", "Scrap report submission resolved", {
        "delivery_outcome": delivery["outcome"],
        "mes_http_status": mes_result.get("status_code"),
        "queue_id": delivery.get("queue_id")
    })
    return {
        "StatusCode": 200,
        "ResponseAckNumber": data["RequestAckNumber"],
        "DeliveryOutcome": delivery["outcome"],
        "QueueId": delivery.get("queue_id")
    }


# -----------------------------------------------------------------------------
# Function    : write_ag_response
# Description : Writes completion metadata, validates it, then writes handshake.
# -----------------------------------------------------------------------------
def write_ag_response(ctx, config, result):
    paths = _paths(config)
    response_timestamp = system.date.now()
    metadata_paths = [
        paths["StatusCode"], paths["ResponseTimestamp"],
        paths["ResponseAckNumber"]
    ]
    metadata_values = [
        result["StatusCode"], response_timestamp, result["ResponseAckNumber"]
    ]
    _debug(ctx, config, "SCRAP_REPORT_PLC_WRITE", "Writing PLC completion metadata", {
        "status_code": result["StatusCode"],
        "response_ack_number": result["ResponseAckNumber"],
        "delivery_outcome": result.get("DeliveryOutcome"),
        "queue_id": result.get("QueueId")
    })
    qualities = system.tag.writeBlocking(metadata_paths, metadata_values)
    _validate_results(metadata_paths, qualities)
    handshake_paths = [paths["Handshake"]]
    handshake_qualities = system.tag.writeBlocking(handshake_paths, [2])
    _validate_results(handshake_paths, handshake_qualities)
    _debug(ctx, config, "SCRAP_REPORT_PLC_WRITE", "PLC metadata and handshake written")


# -----------------------------------------------------------------------------
# Function    : handle_ag_handshake
# Description : Writes 510/time without overwriting ACK for invalid states.
# -----------------------------------------------------------------------------
def handle_ag_handshake(ctx, config, handshake_value):
    paths = _paths(config)
    metadata_paths = [paths["StatusCode"], paths["ResponseTimestamp"]]
    metadata_values = [510, system.date.now()]
    qualities = system.tag.writeBlocking(metadata_paths, metadata_values)
    _validate_results(metadata_paths, qualities)
    handshake_paths = [paths["Handshake"]]
    qualities = system.tag.writeBlocking(handshake_paths, [handshake_value])
    _validate_results(handshake_paths, qualities)
    _debug(ctx, config, "SCRAP_REPORT_HANDSHAKE", "Invalid handshake response written", {
        "handshake_value": handshake_value,
        "status_code": 510,
        "response_ack_written": False
    })
    return {"StatusCode": 510, "Handshake": handshake_value}


# -----------------------------------------------------------------------------
# Function    : write_ag_failure
# Description : Logs failure and intentionally leaves Handshake=1 unchanged.
# -----------------------------------------------------------------------------
def write_ag_failure(ctx, config, error_message):
    logger.error(ctx, "SCRAP_REPORT_FAILED", "FAILED", error_message, {
        "plc_completion_written": False,
        "handshake_preserved": 1
    })


# -----------------------------------------------------------------------------
# Function    : is_success_result
# Description : Treats delivered and durably queued PLC acknowledgements as good.
# -----------------------------------------------------------------------------
def is_success_result(result):
    return result.get("StatusCode") == 200