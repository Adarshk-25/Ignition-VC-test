###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : validation.py
# Module         : Request Validation
#
# Description:
# Parses WebDev request bodies, records request diagnostics and validates payload
# fields against handler schemas before business processing starts.
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

import system.util
from java.lang import Exception as JavaException
from scada_interface import constants, logger
from scada_interface.errors import ValidationError


TYPE_CHECKS = {
    "str": basestring,
    # Ignition/Jython may expose PLC integer tags as either PyInteger or PyLong.
    "int": (int, long),
    "float": float,
    "number": (int, long, float),
    "bool": bool,
    "dict": dict,
    "list": list
}


# -----------------------------------------------------------------------------
# Function    : _request_diagnostics
# Description : Handles request diagnostics logic for this module.
# -----------------------------------------------------------------------------
def _request_diagnostics(request, body):
    headers = {}
    if isinstance(request, dict):
        headers = request.get("headers") or {}
        request_keys = request.keys()
    else:
        headers = getattr(request, "headers", {}) or {}
        request_keys = []

    if isinstance(body, dict):
        body_type = "dict"
        body_keys = body.keys()
        body_length = None
        body_preview = None
    elif body is None:
        body_type = "None"
        body_keys = []
        body_length = 0
        body_preview = None
    else:
        body_text = str(body)
        body_type = type(body).__name__
        body_keys = []
        body_length = len(body_text)
        body_preview = body_text[:120].replace("\r", "\\r").replace("\n", "\\n")

    return {
        "request_type": type(request).__name__,
        "request_keys": list(request_keys),
        "header_names": list(headers.keys()),
        "postData_type": body_type,
        "postData_keys": list(body_keys),
        "postData_length": body_length,
        "postData_preview": body_preview,
        "body_type": body_type,
        "body_keys": list(body_keys),
        "body_length": body_length,
        "body_preview": body_preview
    }


# -----------------------------------------------------------------------------
# Function    : _is_empty_body
# Description : Handles is empty body logic for this module.
# -----------------------------------------------------------------------------
def _is_empty_body(body):
    return body is None or str(body).strip() == ""


# -----------------------------------------------------------------------------
# Function    : _body_from_request
# Description : Handles body from request logic for this module.
# -----------------------------------------------------------------------------
def _body_from_request(request):
    # WebDev request shape can vary between live Ignition and unit-style harnesses.
    if isinstance(request, dict):
        body = request.get("postData")

        if _is_empty_body(body):
            body = request.get("data") or request.get("body") or request.get("text")

        return body

    body = getattr(request, "postData", None)
    if _is_empty_body(body):
        body = getattr(request, "data", None) or getattr(request, "body", None) or getattr(request, "text", None)

    return body


# -----------------------------------------------------------------------------
# Function    : _unwrap_body
# Description : Handles unwrap body logic for this module.
# -----------------------------------------------------------------------------
def _unwrap_body(body):
    if not isinstance(body, dict):
        return body

    # Some callers wrap raw JSON under data/body/text; unwrap before decoding.
    for key in ["data", "body", "text"]:
        if key in body and not _is_empty_body(body.get(key)):
            return body.get(key)

    return body


# -----------------------------------------------------------------------------
# Function    : _raise_invalid_json
# Description : Handles raise invalid json logic for this module.
# -----------------------------------------------------------------------------
def _raise_invalid_json(request, ctx, body, ex):
    diagnostics = _request_diagnostics(request, body)
    diagnostics["parse_error"] = str(ex)
    logger.warn(
        ctx,
        "REQUEST_PARSE",
        "INVALID_JSON",
        "JSON request body could not be parsed",
        diagnostics
    )
    raise ValidationError(
        constants.STATUS_VALIDATION_FAILED,
        "VAL-0001",
        "Invalid JSON request body",
        400
    )


# -----------------------------------------------------------------------------
# Function    : parse_json_request
# Description : Handles parse json request logic for this module.
# -----------------------------------------------------------------------------
def parse_json_request(request, ctx):
    body = None
    try:
        body = _body_from_request(request)
        body = _unwrap_body(body)

        if hasattr(body, "decode"):
            body = body.decode("utf-8")

        if _is_empty_body(body):
            logger.warn(
                ctx,
                "REQUEST_PARSE",
                "EMPTY_BODY",
                "JSON request body is empty",
                _request_diagnostics(request, body)
            )
            raise ValidationError(
                constants.STATUS_VALIDATION_FAILED,
                "VAL-0001",
                "Empty JSON request body",
                400
            )

        if isinstance(body, dict):
            logger.debug(
                ctx,
                "REQUEST_PARSE",
                "SUCCESS",
                "JSON request body already decoded",
                _request_diagnostics(request, body)
            )
            return body

        payload = system.util.jsonDecode(body)
        logger.debug(
            ctx,
            "REQUEST_PARSE",
            "SUCCESS",
            "JSON request body parsed",
            _request_diagnostics(request, body)
        )
        return payload
    except ValidationError:
        raise
    except JavaException, ex:
        _raise_invalid_json(request, ctx, body, ex)
    except Exception, ex:
        _raise_invalid_json(request, ctx, body, ex)


# -----------------------------------------------------------------------------
# Function    : _get_path
# Description : Handles get path logic for this module.
# -----------------------------------------------------------------------------
def _get_path(payload, path):
    current = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


# -----------------------------------------------------------------------------
# Function    : validate_payload
# Description : Handles validate payload logic for this module.
# -----------------------------------------------------------------------------
def validate_payload(schema, payload):
    errors = []
    for path, rule in schema.items():
        value = _get_path(payload, path)
        label = rule.get("label", path)

        # Collect all field issues so MES receives one complete validation response.
        if rule.get("required") and value in [None, ""]:
            errors.append({"field": path, "errorCode": "MANDATORY_MISSING", "message": "%s is required" % label})
            continue

        if value is None:
            continue

        expected_type = rule.get("type")
        if expected_type and expected_type in TYPE_CHECKS and not isinstance(value, TYPE_CHECKS[expected_type]):
            errors.append({
                "field": path,
                "errorCode": "INVALID_TYPE",
                "message": "%s has invalid type" % label,
                "expectedType": expected_type,
                "actualType": value.__class__.__name__
            })

        allowed = rule.get("allowed")
        if allowed and value not in allowed:
            errors.append({"field": path, "errorCode": "INVALID_VALUE", "message": "%s has invalid value" % label})

        max_length = rule.get("max_length")
        if max_length and isinstance(value, basestring) and len(value) > max_length:
            errors.append({"field": path, "errorCode": "MAX_LENGTH", "message": "%s exceeds max length" % label})

    if errors:
        # Gateway event executors display the exception message but not custom
        # ValidationError.details. Include safe field diagnostics without values.
        summary = "; ".join([
            "%s [%s]%s" % (
                item.get("field"),
                item.get("errorCode"),
                (" expected=%s actual=%s" % (
                    item.get("expectedType"), item.get("actualType")
                )) if item.get("expectedType") else ""
            ) for item in errors
        ])
        raise ValidationError(
            constants.STATUS_VALIDATION_FAILED,
            "VAL-0002",
            "Payload validation failed: %s" % summary,
            400,
            {"errors": errors}
        )

    return True