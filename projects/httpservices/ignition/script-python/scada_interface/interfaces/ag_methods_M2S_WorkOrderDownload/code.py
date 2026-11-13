###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : ag_methods_M2S_WorkOrderDownload.py
# Module         : Work Order Download Handler
#
# Description:
# Validates an MES work order, maps it to one JSON PLC structure, dynamically
# resolves the equipment SetWorkOrder method, and invokes it through OPC UA.
###############################################################################

import math
import system
import system.util
from scada_interface import audit, constants, logger, message_header, opcua_client, opcua_routing
from scada_interface.errors import ValidationError


SCHEMA = {
    "WorkOrderDownload.WipOrderNo": {"required": True, "type": "str", "max_length": 50, "label": "WipOrderNo"},
    "WorkOrderDownload.WorkOrderQuantity": {"required": True, "type": "number", "label": "WorkOrderQuantity"},
    "WorkOrderDownload.WorkOrderType": {"required": True, "type": "str", "max_length": 20, "label": "WorkOrderType"},
    "WorkOrderDownload.ProductNo": {"required": True, "type": "str", "max_length": 100, "label": "ProductNo"},
    "WorkOrderDownload.MixingBatchNo": {"required": True, "type": "str", "max_length": 100, "label": "MixingBatchNo"},
    "WorkOrderDownload.Uom": {"required": True, "type": "str", "max_length": 20, "label": "Uom"},
    "WorkOrderDownload.MixingQuantity": {"required": True, "type": "number", "label": "MixingQuantity"},
    "WorkOrderDownload.ProcessCode": {"required": True, "type": "str", "max_length": 100, "label": "ProcessCode"},
    "WorkOrderDownload.EquipmentId": {"required": True, "type": "str", "max_length": 100, "label": "EquipmentId"}
}

STRING_FIELDS = [
    "WipOrderNo", "WorkOrderType", "ProductNo", "MixingBatchNo", "Uom",
    "ProcessCode", "EquipmentId"
]


def validate_business_rules(ctx, payload, config):
    header = payload.get("MessageHeader") or {}
    if header.get("SourceSystem", "").strip() != "MES":
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-WO-001",
                              "MessageHeader.SourceSystem must be MES", 400)
    if header.get("TargetSystem", "").strip() != "SCADA":
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-WO-002",
                              "MessageHeader.TargetSystem must be SCADA", 400)

    data = payload.get("WorkOrderDownload") or {}
    for field_name in STRING_FIELDS:
        value = data.get(field_name)
        if value is None or not str(value).strip():
            raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-WO-003",
                                  "WorkOrderDownload.%s must not be blank" % field_name, 400)

    work_order_quantity = _positive_number(data.get("WorkOrderQuantity"), "WorkOrderQuantity")
    mixing_quantity = _positive_number(data.get("MixingQuantity"), "MixingQuantity")
    if mixing_quantity > work_order_quantity:
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-WO-004",
                              "MixingQuantity must not exceed WorkOrderQuantity", 400)

    target = opcua_routing.resolve_work_order_download_target(data.get("EquipmentId"))
    target = _apply_mock_target(target, config)
    ctx["work_order_download_target"] = target
    ctx["equipment_id"] = str(data.get("EquipmentId")).strip()
    ctx["business_reference"] = str(data.get("WipOrderNo")).strip()
    logger.diagnostic(ctx, config, "WORK_ORDER_TARGET_RESOLUTION",
                      "WorkOrderDownload OPC UA target resolved", {
                          "equipment_id": ctx.get("equipment_id"),
                          "opcua_connection": target.get("opcua_connection"),
                          "opcua_object_node_id": target.get("opcua_object_node_id"),
                          "opcua_method_node_id": target.get("opcua_method_node_id"),
                          "mock_plc_enabled": config.get("mock_plc_enabled", False) is True
                      })
    return True


def map_to_opcua_args(ctx, payload, config):
    data = payload.get("WorkOrderDownload") or {}
    # Build the JSON text explicitly so the PLC structure fields remain in the
    # confirmed order even under Jython 2.7's unordered dictionary behavior.
    work_order_json = (
        "{"
        "\"WorkOrderID\":%s,"
        "\"RecipeID\":%s,"
        "\"AmountToProduce\":%s,"
        "\"UOM\":%s,"
        "\"UnitFBS\":%s,"
        "\"ProductType\":%s,"
        "\"WorkOrderType\":%s,"
        "\"MixingQuantity\":%s,"
        "\"MixingBatchNo\":%s}"
    ) % (
        _json_string(data.get("WipOrderNo")),
        _json_string(data.get("ProcessCode")),
        _json_string(_number_string(data.get("WorkOrderQuantity"), "WorkOrderQuantity")),
        _json_string(data.get("Uom")),
        _json_string(data.get("EquipmentId")),
        _json_string(data.get("ProductNo")),
        _json_string(data.get("WorkOrderType")),
        _json_string(_number_string(data.get("MixingQuantity"), "MixingQuantity")),
        _json_string(data.get("MixingBatchNo"))
    )
    return [work_order_json]


def process(ctx, payload, config):
    data = payload.get("WorkOrderDownload") or {}
    target = ctx.get("work_order_download_target")
    if target is None:
        target = opcua_routing.resolve_work_order_download_target(data.get("EquipmentId"))
        target = _apply_mock_target(target, config)
    method_config = dict(config)
    method_config.update(target)
    method_args = map_to_opcua_args(ctx, payload, config)

    logger.diagnostic(ctx, config, "WORK_ORDER_OPCUA_REQUEST",
                      "Calling PLC SetWorkOrder method", {
                          "equipment_id": data.get("EquipmentId"),
                          "opcua_connection": method_config.get("opcua_connection"),
                          "opcua_object_node_id": method_config.get("opcua_object_node_id"),
                          "opcua_method_node_id": method_config.get("opcua_method_node_id"),
                          "input_count": len(method_args)
                      })
    audit.log_step(ctx, constants.STEP_OPCUA_CALL, "STARTED", {
        "methodNodeId": method_config.get("opcua_method_node_id"),
        "inputCount": len(method_args)
    })
    result = opcua_client.call_method(ctx, method_config, method_args)
    logger.diagnostic(ctx, config, "WORK_ORDER_OPCUA_RESPONSE",
                      "PLC SetWorkOrder method completed", {
                          "opc_status": result.get("opc_status"),
                          "method_node_id": result.get("method_node_id")
                      })
    audit.log_step(ctx, constants.STEP_OPCUA_CALL, "SUCCESS", {
        "opcStatus": result.get("opc_status"),
        "methodNodeId": result.get("method_node_id")
    })
    return {"plc_status": result.get("opc_status"),
            "method_node_id": result.get("method_node_id")}


def build_success_response(ctx, result):
    return _work_order_response(ctx, "200", "Work order downloaded to PLC successfully", 200)


def build_failure_response(ctx, message):
    result_flag = "500"
    http_status = 500
    errors = ctx.get("errors") or []
    if errors:
        error_code = str(errors[-1].get("error_code") or "")
        if error_code.startswith("VAL-"):
            result_flag = "400"
            http_status = 400
        elif error_code.startswith("DUP-"):
            result_flag = "400"
            http_status = 409
        elif error_code.startswith("AUTH-"):
            result_flag = "400"
            http_status = 401
    return _work_order_response(ctx, result_flag, message, http_status)


def _work_order_response(ctx, result_flag, message, http_status):
    response_body = (
        "{\"MessageHeader\":{"
        "\"InterfaceName\":%s,"
        "\"TransactionId\":%s,"
        "\"SourceSystem\":\"SCADA\","
        "\"TargetSystem\":\"MES\","
        "\"EventTimestamp\":%s},"
        "\"WorkOrderDownload\":{"
        "\"ResultFlag\":%s,"
        "\"Message\":%s}}"
    ) % (
        _json_string(ctx.get("interface_name") or "M2S.WorkOrderDownload"),
        _json_string(ctx.get("transaction_id") or ""),
        _json_string(message_header.utc_timestamp()),
        _json_string(result_flag),
        _json_string(message)
    )
    return {"json": response_body, "status": http_status}


def _positive_number(value, field_name):
    if isinstance(value, bool):
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-WO-004",
                              "%s must be a positive finite number" % field_name, 400)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-WO-004",
                              "%s must be a positive finite number" % field_name, 400)
    if math.isnan(number) or math.isinf(number) or number <= 0:
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-WO-004",
                              "%s must be a positive finite number" % field_name, 400)
    return number


def _number_string(value, field_name):
    _positive_number(value, field_name)
    return str(value).strip()


def _json_string(value):
    if value is None:
        value = ""
    return system.util.jsonEncode(str(value).strip())


def _apply_mock_target(target, config):
    """Use the existing in-process OPC UA mock only when explicitly enabled."""
    result = dict(target)
    if config.get("mock_plc_enabled", False) is True:
        result["opcua_connection"] = opcua_client.MOCK_OPCUA_CONNECTION
    return result