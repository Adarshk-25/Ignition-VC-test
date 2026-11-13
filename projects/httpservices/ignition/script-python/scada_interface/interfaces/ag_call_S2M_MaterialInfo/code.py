###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : ag_call_S2M_MaterialInfo.py
# Interface      : S2M.MaterialInfo
# Module         : Ignition Gateway Tag Change Script
# MES Operation  : ag_calls_S2M_MaterialInfo
#
# Description:
#   1. Monitors the AGSetItemInfo Handshake tag.
#   2. Processes the request when Handshake changes to 1.
#   3. Reads RequestData and RequestAckNumber from the Siemens PLC.
#   4. Maps PLC request fields into the MES MaterialInfo request.
#   5. Sends MessageHeader and MaterialInfo directly under Inputs.
#   6. Receives and decodes Outputs.ResponseJSON from MES.
#   7. Maps MES MaterialInfo values into the PLC AGItemResponse structure.
#   8. Maps MES Authorization dynamically to PLC Authorized Boolean.
#   9. Maps MES QualityStatus:
#          Pass -> True
#          Fail -> False
#          Missing/Null/Unknown -> False
#  10. Maps MES RecipeID to PLC RecipeId for StatusCode 200.
#  11. Maps MES WorkOrder to PLC WorkOrderID for StatusCode 200.
#  12. Uses empty RecipeId and WorkOrderID for every non-200 response.
#  13. Copies PLC RequestAckNumber to ResponseAckNumber when StatusCode is 200.
#  14. Writes ResponseData, StatusCode, ResponseTimestamp and
#      ResponseAckNumber first.
#  15. Writes Handshake last, only after all response writes succeed.
#
# Handshake:
#   1 = New request from PLC
#   2 = SCADA processing completed
#   3 = Invalid or cancelled request
#
# PLC RequestData:
# {
#     "ItemID": "HUCO-006",
#     "RecipeId": "PO_Mixing_100.07",
#     "WorkOrderID": "AGR_Mixing_0406_01"
# }
#
# MES Request:
# {
#     "Inputs": {
#         "MessageHeader": {
#             "InterfaceName": "S2M.MaterialInfo",
#             "TransactionId": "MAT-000001",
#             "SourceSystem": "SCADA",
#             "TargetSystem": "MES",
#             "EventTimestamp": "2026-07-16T16:30:00Z",
#             "Equipment": "IN11.E305.PCE.POW22",
#             "EmployeeNo": "ADMIN"
#         },
#         "MaterialInfo": {
#             "HuContainer": "HUCO-006",
#             "FeedingLocation": "IN11.E305.PCE.POW22",
#             "WorkOrder": "IIT_2612_17",
#             "RecipeID": "PO_Mixing_101.01"
#         }
#     }
# }
#
# MES to PLC Response Mapping:
# -----------------------------------------------------------------------------
# MES Field        | PLC Field       | PLC Datatype
# -----------------------------------------------------------------------------
# HuContainer      | ItemID          | WString
# BatchID          | BatchID         | WString
# ExpiryDate       | ExpiryDate      | WString
# QualityStatus    | QualityStatus   | Bool
# Authorization    | Authorized      | Bool
# RecipeID         | RecipeId        | WString
# WorkOrder        | WorkOrderID     | WString
#
# Positive PLC ResponseData / AGItemResponse:
# {
#     "ItemID": "HUCO-006",
#     "BatchID": "BATCH-001",
#     "ExpiryDate": "2027-01-01T00:00:00Z",
#     "QualityStatus": true,
#     "Authorized": true,
#     "RecipeId": "PO_Mixing_100.07",
#     "WorkOrderID": "AGR_Mixing_0406_01"
# }
#
# Technical Failure / Non-200 PLC ResponseData:
# {
#     "ItemID": "",
#     "BatchID": "",
#     "ExpiryDate": "",
#     "QualityStatus": false,
#     "Authorized": false,
#     "RecipeId": "",
#     "WorkOrderID": ""
# }
#
# Version History
# -----------------------------------------------------------------------------
# Version | Date       | Author | Description
# -----------------------------------------------------------------------------
# 1.0     | 22-Jul-2026| Hari   | Initial MaterialInfo implementation
# 1.1     | 22-Jul-2026| Hari   | Added dynamic MES request and response mapping
# 1.2     | 22-Jul-2026| Hari   | Corrected MES Inputs request structure
# 1.3     | 22-Jul-2026| Hari   | Removed OPC UA method call and changed
#         |            |        | ResponseData to normal PLC tag write
# 1.4     | 22-Jul-2026| Hari   | Added RequestAckNumber read and copied it to
#         |            |        | ResponseAckNumber for successful responses
# 1.5     | 22-Jul-2026| Hari   | Mapped MES Authorization and QualityStatus
#         |            |        | dynamically into the PLC response
# 1.6     | 23-Jul-2026| Hari   | Changed PLC QualityStatus datatype to Boolean.
#         |            |        | MES Pass maps to True. Fail, null, missing or
#         |            |        | unknown values map to False.
# 1.7     | 24-Jul-2026| Hari   | Added MES RecipeID to PLC RecipeId mapping and
#         |            |        | MES WorkOrder to PLC WorkOrderID mapping.
# 1.8     | 24-Jul-2026| Hari   | Ensured all non-200 responses use empty string
#         |            |        | fields and False Boolean fields.
# 1.9     | 24-Jul-2026| Hari   | Changed PLC completion Handshake write to occur
#         |            |        | only after response data and metadata succeed.
###############################################################################

import sys
import system
import system.util
from scada_interface import logger, rest_client


SCHEMA = {
    "MaterialInfo.RequestAckNumber": {"required": True, "type": "str"},
    "MaterialInfo.RequestData": {"required": True, "type": "dict"},
    "MaterialInfo.RequestData.ItemID": {"required": True, "type": "str"},
    "MaterialInfo.RequestData.RecipeId": {"required": True, "type": "str"},
    "MaterialInfo.RequestData.WorkOrderID": {"required": True, "type": "str"}
}


# -----------------------------------------------------------------------------
# Function    : _debug
# Description : Emits config-controlled MaterialInfo diagnostic log records.
# -----------------------------------------------------------------------------
def _debug(ctx, config, step, message, extra=None):
    logger.diagnostic(ctx, config, step, message, extra)


# -----------------------------------------------------------------------------
# Function    : _unicode
# Description : Safely converts a value to Unicode for Ignition/Jython.
# -----------------------------------------------------------------------------
def _unicode(value, default_value=""):
    if value is None:
        return unicode(default_value)
    try:
        return unicode(value)
    except Exception:
        return unicode(default_value)


# -----------------------------------------------------------------------------
# Function    : _empty_response
# Description : Builds the safe PLC response used for unsuccessful requests.
# -----------------------------------------------------------------------------
def _empty_response():
    return {
        "ItemID": "",
        "BatchID": "",
        "ExpiryDate": "",
        "QualityStatus": False,
        "Authorized": False,
        "RecipeId": "",
        "WorkOrderID": ""
    }


# -----------------------------------------------------------------------------
# Function    : _authorization
# Description : Maps supported MES authorization values to a PLC Boolean.
# -----------------------------------------------------------------------------
def _authorization(value):
    if value is None:
        return False
    if isinstance(value, basestring):
        return _unicode(value).strip().lower() in [
            "true", "1", "yes", "y", "pass", "passed", "good", "ok",
            "success", "authorized"
        ]
    return bool(value)


# -----------------------------------------------------------------------------
# Function    : _quality
# Description : Maps MES QualityStatus Pass to True and all other values to False.
# -----------------------------------------------------------------------------
def _quality(value):
    return _unicode(value).strip().lower() == "pass"


# -----------------------------------------------------------------------------
# Function    : _paths
# Description : Builds all PLC tag paths used by the MaterialInfo interface.
# -----------------------------------------------------------------------------
def _paths(config):
    base = config.get("ag_tag_base_path")
    return {
        "RequestData": base + "RequestData",
        "RequestAckNumber": base + "RequestAckNumber",
        "ResponseData": base + "ResponseData",
        "StatusCode": base + "StatusCode",
        "ResponseTimestamp": base + "ResponseTimestamp",
        "ResponseAckNumber": base + "ResponseAckNumber",
        "Handshake": base + "Handshake"
    }


# -----------------------------------------------------------------------------
# Function    : _validate_qualities
# Description : Raises an error when any PLC read or write quality is not good.
# -----------------------------------------------------------------------------
def _validate_qualities(paths, values, qualities):
    failures = []
    for index in range(len(qualities)):
        if not qualities[index].isGood():
            failures.append("%s=%s" % (paths[index], qualities[index]))
    if failures:
        raise Exception("PLC tag operation failed: %s" % ", ".join(failures))


# -----------------------------------------------------------------------------
# Function    : read_ag_request
# Description : Reads and decodes the MaterialInfo request from PLC tags.
# -----------------------------------------------------------------------------
def read_ag_request(ctx, config, handshake_tag_path, handshake_value):
    paths = _paths(config)
    read_paths = [paths["RequestData"], paths["RequestAckNumber"]]
    _debug(ctx, config, "MATERIAL_INFO_PLC_READ", "Reading PLC request tags", {
        "handshake_tag_path": handshake_tag_path,
        "handshake_value": handshake_value,
        "read_paths": read_paths
    })
    results = system.tag.readBlocking(read_paths)
    _validate_qualities(read_paths, [], [result.quality for result in results])

    if results[0].value is None or _unicode(results[0].value).strip() == "":
        raise Exception("PLC RequestData is null or empty")
    if results[1].value is None or _unicode(results[1].value).strip() == "":
        raise Exception("PLC RequestAckNumber is null or empty")

    request_data = results[0].value
    # PLC values may arrive as serialized JSON, a Jython dictionary, or an
    # Ignition PyDocumentObjectAdapter returned by a Document tag.
    if isinstance(request_data, basestring):
        request_data = system.util.jsonDecode(_unicode(request_data))
    elif hasattr(request_data, "toDict"):
        request_data = request_data.toDict()
    if not isinstance(request_data, dict):
        raise Exception(
            "PLC RequestData must be a JSON object. ActualType=%s"
            % request_data.__class__.__name__
        )

    ack = _unicode(results[1].value).strip()
    ctx["business_reference"] = ack
    _debug(ctx, config, "MATERIAL_INFO_PLC_READ", "PLC request read successfully", {
        "request_ack_number": ack,
        "item_id": _unicode(request_data.get("ItemID")).strip()
    })
    return {"MaterialInfo": {"RequestAckNumber": ack, "RequestData": request_data}}


# -----------------------------------------------------------------------------
# Function    : validate_business_rules
# Description : Validates mandatory PLC fields and binds transaction context.
# -----------------------------------------------------------------------------
def validate_business_rules(ctx, payload, config):
    data = payload.get("MaterialInfo", {})
    request = data.get("RequestData", {})
    for key in ["ItemID", "RecipeId", "WorkOrderID"]:
        if _unicode(request.get(key)).strip() == "":
            raise Exception("Mandatory field %s is missing" % key)
    ctx["business_reference"] = data.get("RequestAckNumber")
    ctx["source_system"] = "SCADA"
    ctx["target_system"] = "MES"
    _debug(ctx, config, "MATERIAL_INFO_MAPPING", "PLC request validated and mapped", {
        "item_id": _unicode(request.get("ItemID")).strip(),
        "recipe_id": _unicode(request.get("RecipeId")).strip(),
        "work_order_id": _unicode(request.get("WorkOrderID")).strip(),
        "feeding_location": config.get("feeding_location")
    })
    return True


# -----------------------------------------------------------------------------
# Function    : _mes_business_payload
# Description : Maps PLC MaterialInfo fields to the MES business payload.
# -----------------------------------------------------------------------------
def _mes_business_payload(payload, config):
    request = payload["MaterialInfo"]["RequestData"]
    return {
        "HuContainer": _unicode(request.get("ItemID")).strip(),
        "FeedingLocation": config.get("feeding_location"),
        "WorkOrder": _unicode(request.get("WorkOrderID")).strip(),
        "RecipeID": _unicode(request.get("RecipeId")).strip()
    }


# -----------------------------------------------------------------------------
# Function    : _decode_mes_response
# Description : Extracts and decodes MaterialInfo from the MES response envelope.
# -----------------------------------------------------------------------------
def _decode_mes_response(response):
    if not isinstance(response, dict) or not isinstance(response.get("Outputs"), dict):
        raise Exception("MES response is missing Outputs")
    value = response["Outputs"].get("ResponseJSON")
    if value is None:
        raise Exception("MES response is missing Outputs.ResponseJSON")
    if isinstance(value, dict):
        inner = value
    else:
        text = _unicode(value).strip()
        if not text:
            raise Exception("MES Outputs.ResponseJSON is empty")
        # Normalize non-standard Python Boolean literals returned by some MES
        # responses before passing the text to the strict JSON decoder.
        text = text.replace(":False", ":false").replace(":True", ":true")
        text = text.replace(": False", ": false").replace(": True", ": true")
        inner = system.util.jsonDecode(text)
    if not isinstance(inner, dict) or not isinstance(inner.get("MaterialInfo"), dict):
        raise Exception("MES ResponseJSON is missing MaterialInfo")
    return inner["MaterialInfo"]


# -----------------------------------------------------------------------------
# Function    : process
# Description : Calls MES and maps its MaterialInfo response to the PLC contract.
# -----------------------------------------------------------------------------
def process(ctx, payload, config):
    request_payload = _mes_business_payload(payload, config)
    _debug(ctx, config, "MATERIAL_INFO_MES_ATTEMPT", "Sending material info request to MES", {
        "mes_url": config.get("mes_url"),
        "request_ack_number": payload["MaterialInfo"].get("RequestAckNumber"),
        "item_id": request_payload.get("HuContainer"),
        "work_order_id": request_payload.get("WorkOrder"),
        "recipe_id": request_payload.get("RecipeID")
    })
    try:
        mes_response = rest_client.call_mes_api(ctx, config, request_payload)
        material = _decode_mes_response(mes_response)
    except Exception:
        ex = sys.exc_info()[1]
        _debug(ctx, config, "MATERIAL_INFO_MES_FAILURE", "MES material info call failed", {
            "error_message": _unicode(ex)
        })
        raise
    request = payload["MaterialInfo"]["RequestData"]
    result = {
        "ResponseData": {
            "ItemID": _unicode(material.get("HuContainer", request.get("ItemID"))).strip(),
            "BatchID": _unicode(material.get("BatchID")).strip(),
            "ExpiryDate": _unicode(material.get("ExpiryDate")).strip(),
            "QualityStatus": _quality(material.get("QualityStatus")),
            "Authorized": _authorization(material.get("Authorization")),
            "RecipeId": _unicode(material.get("RecipeID")).strip(),
            "WorkOrderID": _unicode(material.get("WorkOrder")).strip()
        },
        "StatusCode": 200,
        "ResponseAckNumber": payload["MaterialInfo"]["RequestAckNumber"],
        "Handshake": 2
    }
    _debug(ctx, config, "MATERIAL_INFO_MES_CALL", "MES material info call completed", {
        "status_code": result["StatusCode"],
        "item_id": result["ResponseData"].get("ItemID"),
        "quality_status": result["ResponseData"].get("QualityStatus"),
        "authorized": result["ResponseData"].get("Authorized")
    })
    return result


# -----------------------------------------------------------------------------
# Function    : _write_response
# Description : Writes PLC response data and metadata, then writes handshake last.
# -----------------------------------------------------------------------------
def _write_response(config, response_data, status_code, ack_number, handshake):
    paths = _paths(config)
    document = system.util.jsonDecode(system.util.jsonEncode(response_data))
    # PLC ResponseTimestamp is OPC UA LDT, exposed by Ignition as java.util.Date.
    # Write the Date object directly; formatted strings fail tag type coercion.
    response_time = system.date.now()
    write_paths = [
        paths["ResponseData"], paths["StatusCode"],
        paths["ResponseTimestamp"], paths["ResponseAckNumber"]
    ]
    write_values = [document, int(status_code), response_time, ack_number or ""]
    results = system.tag.writeBlocking(write_paths, write_values)
    _validate_qualities(write_paths, write_values, results)
    # Handshake is written only after the response payload and metadata succeed,
    # preventing the PLC from consuming an incomplete response.
    handshake_result = system.tag.writeBlocking([paths["Handshake"]], [int(handshake)])
    _validate_qualities([paths["Handshake"]], [handshake], handshake_result)


# -----------------------------------------------------------------------------
# Function    : _write_failure_with_fallback
# Description : Writes an empty failure response, falling back to metadata only.
# -----------------------------------------------------------------------------
def _write_failure_with_fallback(config, status_code, handshake):
    try:
        _write_response(config, _empty_response(), status_code, "", handshake)
    except Exception:
        # If the structured ResponseData tag rejects the empty document, still
        # publish failure metadata and complete the PLC handshake safely.
        paths = _paths(config)
        # Preserve the LDT/java.util.Date contract in the fallback path too.
        response_time = system.date.now()
        metadata_paths = [
            paths["StatusCode"], paths["ResponseTimestamp"], paths["ResponseAckNumber"]
        ]
        metadata_values = [int(status_code), response_time, ""]
        results = system.tag.writeBlocking(metadata_paths, metadata_values)
        _validate_qualities(metadata_paths, metadata_values, results)
        result = system.tag.writeBlocking([paths["Handshake"]], [int(handshake)])
        _validate_qualities([paths["Handshake"]], [handshake], result)


# -----------------------------------------------------------------------------
# Function    : write_ag_response
# Description : Writes a successful MES result to the MaterialInfo PLC tags.
# -----------------------------------------------------------------------------
def write_ag_response(ctx, config, result):
    _debug(ctx, config, "MATERIAL_INFO_PLC_WRITE", "Writing MES response to PLC", {
        "status_code": result.get("StatusCode"),
        "response_ack_number": result.get("ResponseAckNumber", ""),
        "handshake": result.get("Handshake")
    })
    _write_response(
        config, result["ResponseData"], result["StatusCode"],
        result["ResponseAckNumber"], result["Handshake"]
    )
    _debug(ctx, config, "MATERIAL_INFO_PLC_WRITE", "PLC response and handshake written successfully")


# -----------------------------------------------------------------------------
# Function    : write_ag_failure
# Description : Writes the standard technical-failure response to the PLC.
# -----------------------------------------------------------------------------
def write_ag_failure(ctx, config, message):
    _debug(ctx, config, "MATERIAL_INFO_FAILURE", "Writing technical failure to PLC", {
        "error_message": _unicode(message)
    })
    _write_failure_with_fallback(config, 410, 2)


# -----------------------------------------------------------------------------
# Function    : handle_ag_handshake
# Description : Handles invalid or cancelled PLC handshake values.
# -----------------------------------------------------------------------------
def handle_ag_handshake(ctx, config, handshake_value):
    _debug(ctx, config, "MATERIAL_INFO_HANDSHAKE", "Handling non-request handshake", {
        "handshake_value": handshake_value
    })
    _write_failure_with_fallback(config, 510, handshake_value)
    return {
        "ResponseData": _empty_response(),
        "StatusCode": 510,
        "ResponseAckNumber": "",
        "Handshake": handshake_value
    }