###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : opcua_client.py
# Module         : OPC UA Client
#
# Description:
# Wraps OPC UA method calls and tag read/write operations with consistent result
# shapes and common OPC UA error handling.
#
# Author         : Hari
# Version        : 1.0
# Date           : 07-Jul-2026
#
# Change History
# -----------------------------------------------------------------------------
# Sl No | Version | Date        | Author | Fix/Change
# -----------------------------------------------------------------------------
# 1     | 1.0     | 07-Jul-2026 | Hari   | Initial documented version
# -----------------------------------------------------------------------------
###############################################################################

import system
from scada_interface import constants
from scada_interface.errors import OpcuaError


MOCK_OPCUA_CONNECTION = "MOCKME"


# -----------------------------------------------------------------------------
# Function    : call_method
# Description : Handles call method logic for this module.
# -----------------------------------------------------------------------------
def call_method(ctx, config, method_args):
    try:
        # OPC UA method routing comes from interface config, not endpoint scripts.
        connection = config.get("opcua_connection")
        object_node = config.get("opcua_object_node_id")
        method_node = config.get("opcua_method_node_id")

        if connection == MOCK_OPCUA_CONNECTION:
            return {
                "opc_status": "Good",
                "method_node_id": method_node,
                "output": []
            }

        result = system.opcua.callMethod(connection, object_node, method_node, method_args)

        if result is None:
            raise OpcuaError(constants.STATUS_OPCUA_BAD_STATUS, "OPC-0001", "OPC UA method returned no result", 502)

        return {
            "opc_status": "Good",
            "method_node_id": method_node,
            "output": result
        }
    except OpcuaError:
        raise
    except Exception, ex:
        raise OpcuaError(constants.STATUS_OPCUA_BAD_STATUS, "OPC-0002", str(ex), 502)


# -----------------------------------------------------------------------------
# Function    : read_tags
# Description : Handles read tags logic for this module.
# -----------------------------------------------------------------------------
def read_tags(tag_paths):
    qualified_values = system.tag.readBlocking(tag_paths)
    result = {}
    # Return a path-keyed map so callers do not depend on read order.
    for index, path in enumerate(tag_paths):
        qv = qualified_values[index]
        result[path] = {"value": qv.value, "quality": str(qv.quality)}
    return result


# -----------------------------------------------------------------------------
# Function    : write_tags
# Description : Handles write tags logic for this module.
# -----------------------------------------------------------------------------
def write_tags(values_by_path):
    paths = list(values_by_path.keys())
    # Preserve the same key order for paths and values when building write arrays.
    values = [values_by_path[path] for path in paths]
    return system.tag.writeBlocking(paths, values)


def write_tag_values(paths, values):
    """Write parallel ordered path/value arrays in one blocking operation."""
    if len(paths) != len(values):
        raise OpcuaError(constants.STATUS_OPCUA_BAD_STATUS, "OPC-0003",
                          "Tag path and value counts do not match", 502)
    return system.tag.writeBlocking(list(paths), list(values))