###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : ag_methods_M2S_RecipeDownload.py
# Module         : Recipe Download Handler
#
# Description:
# Validates MES recipes, maps them to PLC AGRecipeHeader and AGParameter
# structures, and invokes the configured SetRecipe OPC UA method.
#
# Author         : Hari
# Version        : 2.0
# Date           : 24-Aug-2026
#
# Change History
# -----------------------------------------------------------------------------
# Sl No | Version | Date        | Author | Fix/Change
# -----------------------------------------------------------------------------
# 1     | 1.0     | 07-Jul-2026 | Hari   | Initial RecipeDownload handler
# 2     | 2.0     | 24-Aug-2026 | Hari   | Replaced SQL/tag flow with OPC UA
#       |         |             |        | SetRecipe method integration
###############################################################################

import system
import system.util
from scada_interface import audit, constants, logger, message_header, opcua_client, opcua_routing
from scada_interface.errors import ValidationError


PLC_PARAMETER_COUNT = 5

# Shared router schema for the fields required before business validation.
SCHEMA = {
    "RecipeDownload.WipOrderNo": {"required": True, "type": "str", "max_length": 50, "label": "WipOrderNo"},
    "RecipeDownload.ProcessCode": {"required": True, "type": "str", "max_length": 50, "label": "ProcessCode"},
    "RecipeDownload.ProcessDescription": {"required": True, "type": "str", "max_length": 50, "label": "ProcessDescription"},
    "RecipeDownload.ProductNo": {"required": True, "type": "str", "max_length": 100, "label": "ProductNo"},
    "RecipeDownload.EquipmentId": {"required": True, "type": "str", "max_length": 100, "label": "EquipmentId"},
    "RecipeDownload.Operations": {"required": True, "type": "list", "label": "Operations"}
}

REQUIRED_PARAMETER_FIELDS = [
    "ParameterCode", "ParameterType", "ParameterUom",
    "UpperSpecificationLimit", "LowerSpecificationLimit", "TargetValue"
]


# -----------------------------------------------------------------------------
# Function    : validate_business_rules
# Description : Validates operations and the first five PLC-bound parameters.
# -----------------------------------------------------------------------------
def validate_business_rules(ctx, payload, config):
    recipe = payload.get("RecipeDownload", {})
    operations = recipe.get("Operations") or []
    if len(operations) == 0:
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-0101", "RecipeDownload.Operations is empty", 400)

    # PLC accepts a fixed AGParameter[5]. Parameters are read across operations
    # in their received order, matching the mapping used during processing.
    parameter_count = 0
    for operation in operations:
        for parameter in operation.get("Parameters") or []:
            if parameter_count >= PLC_PARAMETER_COUNT:
                break
            parameter_code = _safe_string(parameter.get("ParameterCode"))
            missing = []
            for field_name in REQUIRED_PARAMETER_FIELDS:
                if field_name not in parameter or parameter.get(field_name) is None:
                    missing.append(field_name)
            if missing:
                raise ValidationError(
                    constants.STATUS_VALIDATION_FAILED,
                    "VAL-0102",
                    "ParameterCode=%s missing fields: %s" % (parameter_code, ", ".join(missing)),
                    400
                )
            _validate_numeric_fields(parameter, parameter_code)
            parameter_count += 1
        if parameter_count >= PLC_PARAMETER_COUNT:
            break

    if parameter_count == 0:
        raise ValidationError(constants.STATUS_VALIDATION_FAILED, "VAL-0103", "No recipe parameters were supplied", 400)

    # Resolve the equipment route during business validation so the request
    # selects its OPC UA method before any PLC call is attempted.
    ctx["recipe_download_target"] = _resolve_opcua_target(recipe.get("EquipmentId"))
    logger.diagnostic(ctx, config, "RECIPE_TARGET_RESOLUTION", "RecipeDownload OPC UA target resolved", {
        "equipment_id": recipe.get("EquipmentId"),
        "opcua_connection": ctx["recipe_download_target"].get("opcua_connection"),
        "opcua_object_node_id": ctx["recipe_download_target"].get("opcua_object_node_id"),
        "opcua_method_node_id": ctx["recipe_download_target"].get("opcua_method_node_id")
    })

    # Expose MES business identifiers to the common audit transaction.
    ctx["equipment_id"] = recipe.get("EquipmentId")
    ctx["business_reference"] = recipe.get("WipOrderNo")
    return True


# -----------------------------------------------------------------------------
# Function    : map_to_opcua_args
# Description : Builds two JSON strings required by the PLC SetRecipe method.
# -----------------------------------------------------------------------------
def map_to_opcua_args(ctx, payload, config):
    recipe = payload.get("RecipeDownload", {})
    plc_header = {
        "ProcessStep": _safe_string(recipe.get("ProcessCode")),
        "ProductID": _safe_string(recipe.get("ProductNo")),
        "UnitFBS": _safe_string(recipe.get("EquipmentId")),
        "RecipeID": "%s.%s" % (_safe_string(recipe.get("ProcessCode")), _safe_string(recipe.get("ProcessRevision")))
    }
    # Flatten parameters across operations and stop at the PLC array capacity.
    plc_parameters = []
    for operation in recipe.get("Operations", []):
        for parameter in operation.get("Parameters") or []:
            if len(plc_parameters) >= PLC_PARAMETER_COUNT:
                break
            plc_parameters.append(_build_plc_parameter(parameter))
        if len(plc_parameters) >= PLC_PARAMETER_COUNT:
            break
    # Pad unused array positions with a valid empty AGParameter structure.
    while len(plc_parameters) < PLC_PARAMETER_COUNT:
        plc_parameters.append(_empty_plc_parameter())

    # Siemens custom structures are ExtensionObjects. Ignition requires their
    # JSON string representations; a Jython PyList cannot be passed directly.
    return [system.util.jsonEncode(plc_header), system.util.jsonEncode(plc_parameters)]


# -----------------------------------------------------------------------------
# Function    : process
# Description : Audits and executes the configured PLC SetRecipe OPC UA method.
# -----------------------------------------------------------------------------
def process(ctx, payload, config):
    method_args = map_to_opcua_args(ctx, payload, config)
    recipe = payload.get("RecipeDownload", {})
    target = ctx.get("recipe_download_target") or _resolve_opcua_target(recipe.get("EquipmentId"))

    # Use a request-local copy. STATIC_CONFIG is shared by all gateway requests
    # and must never be modified with equipment-specific routing values.
    method_config = dict(config)
    method_config.update(target)
    logger.diagnostic(ctx, config, "RECIPE_OPCUA_REQUEST", "Calling PLC SetRecipe method", {
        "equipment_id": recipe.get("EquipmentId"),
        "opcua_connection": method_config.get("opcua_connection"),
        "opcua_object_node_id": method_config.get("opcua_object_node_id"),
        "opcua_method_node_id": method_config.get("opcua_method_node_id"),
        "input_count": len(method_args)
    })
    audit.log_step(ctx, constants.STEP_OPCUA_CALL, "STARTED", {
        "methodNodeId": method_config.get("opcua_method_node_id"), "inputCount": len(method_args)
    })
    result = opcua_client.call_method(ctx, method_config, method_args)
    logger.diagnostic(ctx, config, "RECIPE_OPCUA_RESPONSE", "PLC SetRecipe method completed", {
        "opc_status": result.get("opc_status"),
        "method_node_id": result.get("method_node_id")
    })
    audit.log_step(ctx, constants.STEP_OPCUA_CALL, "SUCCESS", {
        "opcStatus": result.get("opc_status"), "methodNodeId": result.get("method_node_id")
    })
    return {"plc_status": result.get("opc_status"), "method_node_id": result.get("method_node_id")}


# -----------------------------------------------------------------------------
# Function    : build_success_response
# Description : Builds the MES RecipeDownload success response contract.
# -----------------------------------------------------------------------------
def build_success_response(ctx, result):
    return _recipe_response(ctx, "200", "Recipe downloaded to PLC successfully", 200)


# -----------------------------------------------------------------------------
# Function    : build_failure_response
# Description : Maps framework failures to RecipeDownload 400/500 responses.
# -----------------------------------------------------------------------------
def build_failure_response(ctx, message):
    result_flag = "500"
    http_status = 500
    errors = ctx.get("errors") or []
    if errors:
        error_code = str(errors[-1].get("error_code") or "")
        if error_code.startswith("VAL-") or error_code.startswith("DUP-"):
            result_flag = "400"
            http_status = 400
    return _recipe_response(ctx, result_flag, message, http_status)


# -----------------------------------------------------------------------------
# Function    : _recipe_response
# Description : Builds the ordered RecipeDownload WebDev response envelope.
# -----------------------------------------------------------------------------
def _recipe_response(ctx, result_flag, message, http_status):
    # Jython dictionaries are unordered, and Java LinkedHashMap is not accepted
    # by Ignition WebDev's pyToGson converter. WebDev supports a valid JSON
    # string under the "json" key, so build the small ordered envelope directly.
    # jsonEncode is applied to every dynamic value to preserve JSON escaping.
    response_body = (
        "{\"MessageHeader\":{"
        "\"InterfaceName\":%s,"
        "\"TransactionId\":%s,"
        "\"SourceSystem\":\"SCADA\","
        "\"TargetSystem\":\"MES\","
        "\"EventTimestamp\":%s},"
        "\"RecipeDownload\":{"
        "\"ResultFlag\":%s,"
        "\"Message\":%s}}"
    ) % (
        _json_value(ctx.get("interface_name") or "M2S.RecipeDownload"),
        _json_value(ctx.get("transaction_id") or ""),
        _json_value(message_header.utc_timestamp()),
        _json_value(result_flag),
        _json_value(message)
    )

    return {
        "json": response_body,
        "status": http_status
    }


# -----------------------------------------------------------------------------
# Function    : _json_value
# Description : JSON-escapes one dynamic response value safely.
# -----------------------------------------------------------------------------
def _json_value(value):
    return system.util.jsonEncode(value)


# -----------------------------------------------------------------------------
# Function    : _build_plc_parameter
# Description : Maps one MES parameter to the PLC AGParameter field names.
# -----------------------------------------------------------------------------
def _build_plc_parameter(parameter):
    parameter_code = _safe_string(parameter.get("ParameterCode"))
    return {
        "ParameterRef": parameter_code,
        "ParameterType": _safe_string(parameter.get("ParameterType")),
        "ParameterUOM": _safe_string(parameter.get("ParameterUom")),
        "USL": _safe_float(parameter.get("UpperSpecificationLimit"), "UpperSpecificationLimit", parameter_code),
        "LSL": _safe_float(parameter.get("LowerSpecificationLimit"), "LowerSpecificationLimit", parameter_code),
        "Setpoint": _safe_float(parameter.get("TargetValue"), "TargetValue", parameter_code)
    }


# -----------------------------------------------------------------------------
# Function    : _resolve_opcua_target
# Description : Resolves one EquipmentId to a request-local OPC UA target.
# -----------------------------------------------------------------------------
def _resolve_opcua_target(equipment_id):
    return opcua_routing.resolve_recipe_download_target(equipment_id)


# -----------------------------------------------------------------------------
# Function    : _empty_plc_parameter
# Description : Returns one default entry for the fixed PLC parameter array.
# -----------------------------------------------------------------------------
def _empty_plc_parameter():
    return {"ParameterRef": "", "ParameterType": "", "ParameterUOM": "", "USL": 0.0, "LSL": 0.0, "Setpoint": 0.0}


# -----------------------------------------------------------------------------
# Function    : _validate_numeric_fields
# Description : Validates PLC specification and setpoint numeric conversion.
# -----------------------------------------------------------------------------
def _validate_numeric_fields(parameter, parameter_code):
    for field_name in ["UpperSpecificationLimit", "LowerSpecificationLimit", "TargetValue"]:
        _safe_float(parameter.get(field_name), field_name, parameter_code)


# -----------------------------------------------------------------------------
# Function    : _safe_string
# Description : Converts optional MES values to PLC-compatible strings.
# -----------------------------------------------------------------------------
def _safe_string(value):
    if value is None:
        return ""
    return str(value)


# -----------------------------------------------------------------------------
# Function    : _safe_float
# Description : Converts numeric MES values or raises a validation error.
# -----------------------------------------------------------------------------
def _safe_float(value, field_name, parameter_code):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValidationError(
            constants.STATUS_VALIDATION_FAILED,
            "VAL-0104",
            "ParameterCode=%s field %s must be numeric" % (parameter_code, field_name),
            400
        )