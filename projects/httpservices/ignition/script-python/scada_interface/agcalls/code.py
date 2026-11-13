###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : ag_calls.py
# Module         : AG Calls Tag Helper
#
# Description:
# Reads AG Calls request tags and writes AG Calls response tags for
# PLC/equipment initiated SCADA-to-MES workflows.
#
# Author         : Hari
# Version        : 1.0
# Date           : 31-Jul-2026
#
# Change History
# -----------------------------------------------------------------------------
# Sl No | Version | Date        | Author | Fix/Change
# -----------------------------------------------------------------------------
# 1     | 1.0     | 31-Jul-2026 | Hari   | Initial documented version
# -----------------------------------------------------------------------------
###############################################################################

import system
import system.util
from scada_interface import opcua_client


AG_REQUEST_TAGS = [
    "senderFBS",
    "RequestAckNumber",
    "RequestTimestamp",
    "Handshake",
    "StatusCode",
    "RequestData"
]


# -----------------------------------------------------------------------------
# Function    : build_paths
# Description : Handles build paths logic for this module.
# -----------------------------------------------------------------------------
def build_paths(base_path, tag_names):
    return ["%s/%s" % (base_path, tag) for tag in tag_names]


# -----------------------------------------------------------------------------
# Function    : read_request
# Description : Handles read request logic for this module.
# -----------------------------------------------------------------------------
def read_request(base_path):
    paths = build_paths(base_path, AG_REQUEST_TAGS)
    values = opcua_client.read_tags(paths)
    request = {}
    # Convert full tag paths back into compact AG request field names.
    for path, data in values.items():
        request[path.split("/")[-1]] = data.get("value")
    return request


# -----------------------------------------------------------------------------
# Function    : write_response
# Description : Handles write response logic for this module.
# -----------------------------------------------------------------------------
def write_response(base_path, response_payload, status_code, ack_number):
    # PLC-facing response writes are grouped so the ACK/status fields change together.
    values = {
        "%s/ResponseData" % base_path: system.util.jsonEncode(response_payload),
        "%s/ResponseTime" % base_path: system.date.now(),
        "%s/ResponseAckNumber" % base_path: ack_number,
        "%s/StatusCode" % base_path: status_code
    }
    return opcua_client.write_tags(values)