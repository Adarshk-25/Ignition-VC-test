###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : opcua_routing.py
# Module         : Dynamic OPC UA Method Routing
###############################################################################

import re
from scada_interface import environment
from scada_interface.errors import RoutingError, ValidationError


def resolve_recipe_download_target(equipment_id):
    return resolve_method_target("RecipeDownload", equipment_id, "SetRecipe")


def resolve_work_order_download_target(equipment_id):
    """Resolve a dotted equipment prefix to its SetWorkOrder method target."""
    equipment_key = _validate_equipment_id(equipment_id)
    target = _configured_target("WorkOrderDownload", equipment_key)
    if target is not None:
        return _target_from_config(target, equipment_key)

    object_node = "nsu=http://agratas.com/UA/;s=%s/AGMethods" % equipment_key
    return {
        "opcua_connection": equipment_key.replace(".", "_"),
        "opcua_object_node_id": object_node,
        "opcua_method_node_id": object_node + "/SetWorkOrder"
    }


def resolve_mat_status_update_target(equipment_id):
    """Resolve a dotted equipment prefix to its MatStatusUpdate method."""
    equipment_key = _validate_equipment_id(equipment_id)
    target = _configured_target("MatStatusUpdate", equipment_key)
    if target is not None:
        return _target_from_config(target, equipment_key)

    object_node = "nsu=http://agratas.com/UA/;s=%s/AGMethods" % equipment_key
    return {
        "opcua_connection": equipment_key.replace(".", "_"),
        "opcua_object_node_id": object_node,
        "opcua_method_node_id": object_node + "/MatStatusUpdate"
    }


def resolve_create_serial_target(equipment_id):
    """Resolve a dotted equipment prefix to its AGCreatSerial method."""
    equipment_key = _validate_equipment_id(equipment_id)
    target = _configured_target("CreateSerial", equipment_key)
    if target is not None:
        return _target_from_config(target, equipment_key)

    object_node = "nsu=http://agratas.com/UA/;s=%s/AGMethods" % equipment_key
    return {
        "opcua_connection": equipment_key.replace(".", "_"),
        "opcua_object_node_id": object_node,
        "opcua_method_node_id": object_node + "/AGCreatSerial"
    }


def resolve_method_target(interface_name, equipment_id, default_method_name):
    equipment_key = _validate_equipment_id(equipment_id)
    if interface_name == "RecipeDownload":
        recipe_targets = _recipe_targets()
        if recipe_targets is not None:
            target = recipe_targets.get(equipment_key)
            if target is None:
                raise ValidationError(
                    "VALIDATION_FAILED",
                    "VAL-0105",
                    "No valid OPC UA target configured for EquipmentId=%s" % equipment_key,
                    400
                )
            return _target_from_config(target, equipment_key)

    target = _configured_target(interface_name, equipment_key)
    if target is not None:
        return _target_from_config(target, equipment_key)

    connection = environment.get_path("plcs", "primary", "opcua_connection")
    prefix = "nsu=http://agratas.com/UA/;s=" + equipment_key
    object_suffix = "/AGMethods"
    method_name = default_method_name
    method_suffix = "/%s" % method_name
    return {
        "opcua_connection": connection,
        "opcua_object_node_id": prefix + object_suffix,
        "opcua_method_node_id": prefix + object_suffix + method_suffix
    }


def _configured_target(interface_name, equipment_key):
    try:
        targets = environment.get_path("opcua_method_targets", interface_name)
        return targets.get(equipment_key)
    except Exception:
        return None


def _recipe_targets():
    try:
        return environment.get_path("recipe_download_targets")
    except Exception:
        return None


def _target_from_config(target, equipment_key):
    try:
        plc_key = target.get("plc", "primary")
        connection = environment.get_path("plcs", plc_key, "opcua_connection")
        object_node = target.get("opcua_object_node_id")
        method_node = target.get("opcua_method_node_id")
        if not object_node or not method_node:
            raise Exception("OPC UA target NodeIds are incomplete")
        return {
            "opcua_connection": connection,
            "opcua_object_node_id": object_node,
            "opcua_method_node_id": method_node
        }
    except Exception:
        raise ValidationError(
            "VALIDATION_FAILED",
            "VAL-0105",
            "No valid OPC UA target configured for EquipmentId=%s" % equipment_key,
            400
        )


def _validate_equipment_id(equipment_id):
    if equipment_id is None:
        equipment_key = ""
    else:
        equipment_key = str(equipment_id).strip()
    if not equipment_key:
        raise ValidationError("VALIDATION_FAILED", "VAL-0105", "RecipeDownload.EquipmentId is empty", 400)
    if not re.match(r"^[A-Za-z0-9_.-]+$", equipment_key):
        raise ValidationError(
            "VALIDATION_FAILED",
            "VAL-0105",
            "EquipmentId contains invalid OPC UA path characters: %s" % equipment_key,
            400
        )
    return equipment_key