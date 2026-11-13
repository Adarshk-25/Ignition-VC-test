###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : ag_methods_M2S_MatStatusUpdate.py
# Module         : Material Status Update Handler
#
# Description:
# Validates an MES material status request, maps all blocked items to one JSON
# PLC structure, dynamically resolves the equipment method, and invokes it
# through the common OPC UA client. EmployeeNo is intentionally not accepted or
# mapped by this interface contract.
#
# Author         : Hari
# Version        : 1.0
# Date           : 09-Sep-2026
#
# Change History
# -----------------------------------------------------------------------------
# Sl No | Version | Date        | Author | Fix/Change
# -----------------------------------------------------------------------------
# 1     | 1.0     | 09-Sep-2026 | Hari   | Initial mock-first implementation
###############################################################################

import system
import system.util
from scada_interface import audit, constants, logger, message_header, opcua_client, opcua_routing
from scada_interface.errors import ValidationError


MAX_BLOCKED_ITEMS = 100

SCHEMA = {
    "BlockProduct.EquipmentId": {"required": True, "type": "str", "max_length": 100, "label": "EquipmentId"},
    "BlockProduct.BlockedItems": {"required": True, "type": "list", "label": "BlockedItems"}
}

# -----------------------------------------------------------------------------
# Function    : validate_business_rules
# Description : Validates header direction, equipment and every blocked item.
# -----------------------------------------------------------------------------
def validate_business_rules(ctx, payload, config):
    header = payload.get("MessageHeader") or {}
    if _trim(header.get("SourceSystem")) != "MES":
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-MSU-001",
                              "MessageHeader.SourceSystem must be MES", 400)
    if _trim(header.get("TargetSystem")) != "SCADA":
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-MSU-002",
                              "MessageHeader.TargetSystem must be SCADA", 400)

    block_product = payload.get("BlockProduct") or {}
    equipment_id = _required_string(block_product.get("EquipmentId"),
                                    "BlockProduct.EquipmentId", 100, "VAL-MSU-003")
    items = block_product.get("BlockedItems")
    if not isinstance(items, list) or len(items) == 0:
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-MSU-004",
                              "BlockProduct.BlockedItems must contain at least one item", 400)
    if len(items) > MAX_BLOCKED_ITEMS:
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-MSU-004",
                              "BlockProduct.BlockedItems exceeds maximum item count %s" % MAX_BLOCKED_ITEMS, 400)

    for index, item in enumerate(items):
        _validate_item(item, index)

    target = opcua_routing.resolve_mat_status_update_target(equipment_id)
    target = _apply_mock_target(target, config)
    ctx["mat_status_update_target"] = target
    ctx["equipment_id"] = equipment_id
    ctx["business_reference"] = ctx.get("transaction_id")
    logger.diagnostic(ctx, config, "MAT_STATUS_TARGET_RESOLUTION",
                      "MatStatusUpdate OPC UA target resolved", {
                          "equipment_id": equipment_id,
                          "opcua_connection": target.get("opcua_connection"),
                          "opcua_object_node_id": target.get("opcua_object_node_id"),
                          "opcua_method_node_id": target.get("opcua_method_node_id"),
                          "mock_plc_enabled": config.get("mock_plc_enabled", False) is True
                      })
    return True


# -----------------------------------------------------------------------------
# Function    : map_to_opcua_args
# Description : Builds one deterministic JSON String for the PLC method.
# -----------------------------------------------------------------------------
def map_to_opcua_args(ctx, payload, config):
    block_product = payload.get("BlockProduct") or {}
    item_json = []
    for item in block_product.get("BlockedItems") or []:
        item_json.append(
            "{\"ItemID\":%s,\"OutboundTime\":%s,\"BatchID\":%s,"
            "\"RFID_Core\":%s,\"ReasonCode\":%s,\"QualityStatus\":%s}"
            % (_json_string(item.get("SerialId")),
               _json_string(item.get("JROutboundTime")),
               _json_string(item.get("BatchId")),
               _json_string(item.get("RfidNo")),
               _json_string(item.get("ReasonCode")),
               _json_value(item.get("Status")))
        )
    plc_json = "{\"UnitFBS\":%s,\"BlockedItems\":[%s]}" % (
        _json_string(block_product.get("EquipmentId")), ",".join(item_json)
    )
    return [plc_json]


# -----------------------------------------------------------------------------
# Function    : process
# Description : Audits and executes one request-local OPC UA method call.
# -----------------------------------------------------------------------------
def process(ctx, payload, config):
    block_product = payload.get("BlockProduct") or {}
    target = ctx.get("mat_status_update_target")
    if target is None:
        target = opcua_routing.resolve_mat_status_update_target(block_product.get("EquipmentId"))
        target = _apply_mock_target(target, config)

    method_config = dict(config)
    method_config.update(target)
    method_args = map_to_opcua_args(ctx, payload, config)
    item_count = len(block_product.get("BlockedItems") or [])

    logger.diagnostic(ctx, config, "MAT_STATUS_OPCUA_REQUEST",
                      "Calling PLC MatStatusUpdate method", {
                          "equipment_id": block_product.get("EquipmentId"),
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
    logger.diagnostic(ctx, config, "MAT_STATUS_OPCUA_RESPONSE",
                      "PLC MatStatusUpdate method completed", {
                          "opc_status": result.get("opc_status"),
                          "method_node_id": result.get("method_node_id")
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
        "mock_plc": method_config.get("opcua_connection") == opcua_client.MOCK_OPCUA_CONNECTION
    }


# -----------------------------------------------------------------------------
# Function    : build_success_response
# Description : Builds the Boolean MES success contract for mock or live mode.
# -----------------------------------------------------------------------------
def build_success_response(ctx, result):
    message = "Block product request processed successfully"
    if result.get("method_node_id") and result.get("plc_status") == "Good":
        # Current interface configuration is mock-first. The context does not
        # contain static config, so process returns the selected mode explicitly.
        if result.get("mock_plc") is True:
            message = "Block product request received successfully - SCADA MOCK"
    return _mat_status_response(ctx, True, message, 200)


# -----------------------------------------------------------------------------
# Function    : build_failure_response
# Description : Maps common failures to the Boolean MES failure contract.
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
    return _mat_status_response(ctx, False, message, http_status)


# -----------------------------------------------------------------------------
# Function    : _mat_status_response
# Description : Builds an ordered, safely escaped WebDev response envelope.
# -----------------------------------------------------------------------------
def _mat_status_response(ctx, result_flag, message, http_status):
    response_body = (
        "{\"MessageHeader\":{"
        "\"InterfaceName\":%s,"
        "\"TransactionId\":%s,"
        "\"SourceSystem\":\"SCADA\","
        "\"TargetSystem\":\"MES\","
        "\"EventTimestamp\":%s},"
        "\"BlockProduct\":{"
        "\"ResultFlag\":%s,"
        "\"Message\":%s}}"
    ) % (
        _json_string(ctx.get("interface_name") or "M2S.MatStatusUpdate"),
        _json_string(ctx.get("transaction_id") or ""),
        _json_string(message_header.utc_timestamp()),
        "true" if result_flag else "false",
        _json_string(message)
    )
    return {"json": response_body, "status": http_status}


# -----------------------------------------------------------------------------
# Function    : _validate_item
# Description : Validates the required fields in one item.
# -----------------------------------------------------------------------------
def _validate_item(item, index):
    if not isinstance(item, dict):
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-MSU-005",
                              "BlockProduct.BlockedItems[%s] must be an object" % index, 400)


# -----------------------------------------------------------------------------
# Function    : _required_string
# Description : Returns a trimmed bounded string or raises safe validation.
# -----------------------------------------------------------------------------
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