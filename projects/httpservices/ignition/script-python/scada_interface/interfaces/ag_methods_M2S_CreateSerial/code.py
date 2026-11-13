###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : ag_methods_M2S_CreateSerial.py
# Module         : Create Serial Handler
#
# Description:
# Validates an MES serial list, maps every entry to one ordered JSON PLC array,
# dynamically resolves the equipment AGCreatSerial method, and invokes it once
# through the common OPC UA client.
#
# Author         : Hari
# Version        : 1.0
# Date           : 15-Sep-2026
#
# Change History
# -----------------------------------------------------------------------------
# Sl No | Version | Date        | Author | Fix/Change
# -----------------------------------------------------------------------------
# 1     | 1.0     | 15-Sep-2026 | Hari   | Initial mock-first implementation
###############################################################################

import system
import system.util
from scada_interface import audit, constants, logger, message_header, opcua_client, opcua_routing
from scada_interface.errors import ValidationError


MAX_SERIAL_ITEMS = 100

SCHEMA = {
    "CreateSerial.EquipmentID": {
        "required": True, "type": "str", "max_length": 100,
        "label": "EquipmentID"
    },
    "CreateSerial.SerialInfo": {
        "required": True, "type": "list", "label": "SerialInfo"
    }
}


# -----------------------------------------------------------------------------
# Function    : validate_business_rules
# Description : Validates direction, equipment and every item.
# -----------------------------------------------------------------------------
def validate_business_rules(ctx, payload, config):
    header = payload.get("MessageHeader") or {}
    # SchemaVersion is owned by MES. Preserve it without validating or
    # normalizing it so the same value can be returned in the response.
    ctx["schema_version"] = header.get("SchemaVersion")
    if _trim(header.get("SourceSystem")) != "MES":
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-CS-001",
                              "MessageHeader.SourceSystem must be MES", 400)
    if _trim(header.get("TargetSystem")) != "SCADA":
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-CS-002",
                              "MessageHeader.TargetSystem must be SCADA", 400)
    create_serial = payload.get("CreateSerial") or {}
    equipment_id = _required_string(create_serial.get("EquipmentID"),
                                    "CreateSerial.EquipmentID", 100, "VAL-CS-004")
    items = create_serial.get("SerialInfo")
    if not isinstance(items, list) or len(items) == 0:
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-CS-005",
                              "CreateSerial.SerialInfo must contain at least one item", 400)
    if len(items) > MAX_SERIAL_ITEMS:
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-CS-005",
                              "CreateSerial.SerialInfo exceeds maximum item count %s" % MAX_SERIAL_ITEMS, 400)

    # Duplicate entries are intentionally preserved. MES owns list cardinality,
    # and the confirmed sample contains identical entries.
    for index, item in enumerate(items):
        _validate_item(item, index)

    target = opcua_routing.resolve_create_serial_target(equipment_id)
    target = _apply_mock_target(target, config)
    ctx["create_serial_target"] = target
    ctx["equipment_id"] = equipment_id
    ctx["business_reference"] = ctx.get("transaction_id")
    logger.diagnostic(ctx, config, "CREATE_SERIAL_TARGET_RESOLUTION",
                      "CreateSerial OPC UA target resolved", {
                          "equipment_id": equipment_id,
                          "opcua_connection": target.get("opcua_connection"),
                          "opcua_object_node_id": target.get("opcua_object_node_id"),
                          "opcua_method_node_id": target.get("opcua_method_node_id"),
                          "mock_plc_enabled": config.get("mock_plc_enabled", False) is True
                      })
    return True


# -----------------------------------------------------------------------------
# Function    : map_to_opcua_args
# Description : Builds one deterministic JSON String containing all serials.
# -----------------------------------------------------------------------------
def map_to_opcua_args(ctx, payload, config):
    create_serial = payload.get("CreateSerial") or {}
    item_json = []
    for item in create_serial.get("SerialInfo") or []:
        item_json.append(
            "{\"PreviousItemID\":%s,\"GeneratedID\":%s,"
            "\"ResultFlag\":%s,\"Message\":%s}"
            % (_json_string(item.get("OldSerialNo")),
               _json_string(item.get("GeneratedID")),
               "true" if item.get("ResultFlag") is True else "false",
               _json_string(item.get("Message")))
        )
    return ["{\"AGCreatSerial\":[%s]}" % ",".join(item_json)]


# -----------------------------------------------------------------------------
# Function    : process
# Description : Audits and executes one request-local OPC UA method call.
# -----------------------------------------------------------------------------
def process(ctx, payload, config):
    create_serial = payload.get("CreateSerial") or {}
    target = ctx.get("create_serial_target")
    if target is None:
        target = opcua_routing.resolve_create_serial_target(create_serial.get("EquipmentID"))
        target = _apply_mock_target(target, config)

    method_config = dict(config)
    method_config.update(target)
    method_args = map_to_opcua_args(ctx, payload, config)
    serial_info = create_serial.get("SerialInfo") or []
    item_count = len(serial_info)

    logger.diagnostic(ctx, config, "CREATE_SERIAL_OPCUA_REQUEST",
                      "Calling PLC AGCreatSerial method", {
                          "equipment_id": create_serial.get("EquipmentID"),
                          "item_count": item_count,
                          "input_count": len(method_args),
                          "opcua_connection": method_config.get("opcua_connection"),
                          "opcua_object_node_id": method_config.get("opcua_object_node_id"),
                          "opcua_method_node_id": method_config.get("opcua_method_node_id")
                      })
    audit.log_step(ctx, constants.STEP_OPCUA_CALL, "STARTED", {
        "methodNodeId": method_config.get("opcua_method_node_id"),
        "inputCount": len(method_args),
        "itemCount": item_count
    })
    result = opcua_client.call_method(ctx, method_config, method_args)
    logger.diagnostic(ctx, config, "CREATE_SERIAL_OPCUA_RESPONSE",
                      "PLC AGCreatSerial method completed", {
                          "opc_status": result.get("opc_status"),
                          "method_node_id": result.get("method_node_id"),
                          "item_count": item_count
                      })
    audit.log_step(ctx, constants.STEP_OPCUA_CALL, "SUCCESS", {
        "opcStatus": result.get("opc_status"),
        "methodNodeId": result.get("method_node_id"),
        "itemCount": item_count
    })
    return {
        "plc_status": result.get("opc_status"),
        "method_node_id": result.get("method_node_id"),
        "item_count": item_count,
        "serial_info": _copy_response_items(serial_info),
        "mock_plc": method_config.get("opcua_connection") == opcua_client.MOCK_OPCUA_CONNECTION
    }


# -----------------------------------------------------------------------------
# Function    : build_success_response
# Description : Returns all accepted serials in the confirmed response direction.
# -----------------------------------------------------------------------------
def build_success_response(ctx, result):
    return _success_response(ctx, result.get("serial_info") or [], 200)


# -----------------------------------------------------------------------------
# Function    : build_failure_response
# Description : Maps common failures to a safe CreateSerial failure response.
# -----------------------------------------------------------------------------
def build_failure_response(ctx, message):
    http_status = 500
    errors = ctx.get("errors") or []
    if errors:
        error_code = str(errors[-1].get("error_code") or "")
        if error_code.startswith("VAL-"):
            http_status = 400
        elif error_code.startswith("DUP-"):
            http_status = 409
        elif error_code.startswith("AUTH-"):
            http_status = 401
        elif error_code.startswith("OPC-"):
            http_status = 502
    return _failure_response(ctx, message, http_status)


def _success_response(ctx, serial_info, http_status):
    response_body = (
        "{\"MessageHeader\":{"
        "\"InterfaceName\":\"S2M.CreateSerial\","
        "\"TransactionId\":%s,"
        "\"SourceSystem\":\"SCADA\","
        "\"TargetSystem\":\"MES\","
        "\"EventTimestamp\":%s,"
        "\"SchemaVersion\":%s},"
        "\"CreateSerial\":{\"SerialInfo\":[%s]}}"
    ) % (
        _json_string(ctx.get("transaction_id")),
        _json_string(message_header.utc_timestamp()),
        _json_value(ctx.get("schema_version")),
        ",".join([_response_item_json(item) for item in serial_info])
    )
    return {"json": response_body, "status": http_status}


def _failure_response(ctx, message, http_status):
    response_body = (
        "{\"MessageHeader\":{"
        "\"InterfaceName\":\"S2M.CreateSerial\","
        "\"TransactionId\":%s,"
        "\"SourceSystem\":\"SCADA\","
        "\"TargetSystem\":\"MES\","
        "\"EventTimestamp\":%s,"
        "\"SchemaVersion\":%s},"
        "\"CreateSerial\":{\"ResultFlag\":false,\"Message\":%s}}"
    ) % (
        _json_string(ctx.get("transaction_id")),
        _json_string(message_header.utc_timestamp()),
        _json_value(ctx.get("schema_version")),
        _json_string(message)
    )
    return {"json": response_body, "status": http_status}


def _response_item_json(item):
    return (
        "{\"OldSerialNo\":%s,\"GeneratedID\":%s,"
        "\"ResultFlag\":%s,\"Message\":%s}"
        % (_json_string(item.get("OldSerialNo")),
           _json_string(item.get("GeneratedID")),
           "true" if item.get("ResultFlag") is True else "false",
           _json_string(item.get("Message")))
    )


def _copy_response_items(items):
    result = []
    for item in items:
        result.append({
            "OldSerialNo": _trim(item.get("OldSerialNo")),
            "GeneratedID": _trim(item.get("GeneratedID")),
            "ResultFlag": item.get("ResultFlag") is True,
            "Message": _trim(item.get("Message"))
        })
    return result


def _validate_item(item, index):
    if not isinstance(item, dict):
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-CS-006",
                              "CreateSerial.SerialInfo[%s] must be an object" % index, 400)
    prefix = "CreateSerial.SerialInfo[%s]" % index
    _required_string(item.get("OldSerialNo"), prefix + ".OldSerialNo", 100, "VAL-CS-006")
    _required_string(item.get("GeneratedID"), prefix + ".GeneratedID", 100, "VAL-CS-006")
    if not isinstance(item.get("ResultFlag"), bool):
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-CS-006",
                              prefix + ".ResultFlag must be a Boolean", 400)
    _required_string(item.get("Message"), prefix + ".Message", 255, "VAL-CS-006")


def _required_string(value, path, max_length, error_code):
    if not isinstance(value, basestring) or not value.strip():
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, error_code,
                              "%s is required and must be a non-blank string" % path, 400)
    result = value.strip()
    if len(result) > max_length:
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, error_code,
                              "%s exceeds maximum length %s" % (path, max_length), 400)
    return result


def _trim(value):
    if value is None:
        return ""
    return str(value).strip()


def _json_string(value):
    return system.util.jsonEncode(_trim(value))


def _json_value(value):
    return system.util.jsonEncode(value)


def _apply_mock_target(target, config):
    """Replace only the request-local connection when mock mode is enabled."""
    result = dict(target)
    if config.get("mock_plc_enabled", False) is True:
        result["opcua_connection"] = opcua_client.MOCK_OPCUA_CONNECTION
    return result