###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : message_header.py
# Module         : MES MessageHeader Helper
#
# Description:
#   Provides the shared inbound and outbound MES MessageHeader contract.
#   Validates required inbound header fields, parses event timestamps, binds
#   header values to the transaction context, generates transaction identifiers,
#   and wraps outbound business payloads in the MES Inputs envelope.
#
# Author         : Hari
# Version        : 1.1
# Date           : 12-Aug-2026
#
# Change History
# -----------------------------------------------------------------------------
# Sl No | Version | Date        | Author | Fix/Change
# -----------------------------------------------------------------------------
# 1     | 1.0     | 07-Jul-2026 | Hari   | Initial MessageHeader implementation.
# 2     | 1.1     | 12-Aug-2026 | Hari   | Added optional Equipment and EmployeeNo
#       |         |             |        | fields and standardized documentation.
###############################################################################

import random
from java.text import ParsePosition, SimpleDateFormat
from java.util import Date, TimeZone
from scada_interface import constants
from scada_interface.errors import ValidationError


REQUIRED_FIELDS = [
    "InterfaceName",
    "TransactionId",
    "SourceSystem",
    "TargetSystem",
    "EventTimestamp"
]


# -----------------------------------------------------------------------------
# Function    : utc_timestamp
# Description : Returns the current UTC time in the MES ISO-8601 format.
# -----------------------------------------------------------------------------
def utc_timestamp():
    formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    formatter.setTimeZone(TimeZone.getTimeZone("UTC"))
    return formatter.format(Date())


# -----------------------------------------------------------------------------
# Function    : generate_transaction_id
# Description : Generates a timestamped transaction ID with a random suffix.
# -----------------------------------------------------------------------------
def generate_transaction_id(prefix):
    formatter = SimpleDateFormat("yyyyMMddHHmmssSSS")
    formatter.setTimeZone(TimeZone.getTimeZone("UTC"))
    return "%s-%s-%s" % (
        str(prefix or "TXN").upper(),
        formatter.format(Date()),
        random.randint(1000, 9999)
    )


# -----------------------------------------------------------------------------
# Function    : parse_event_timestamp
# Description : Strictly parses a supported ISO-8601 MessageHeader timestamp.
# -----------------------------------------------------------------------------
def parse_event_timestamp(value):
    text = str(value or "").strip()
    # Accept timestamps with or without milliseconds and with Z or an explicit
    # numeric timezone offset. Parsing remains strict for the complete value.
    patterns = [
        "yyyy-MM-dd'T'HH:mm:ss.SSSX",
        "yyyy-MM-dd'T'HH:mm:ssX",
        "yyyy-MM-dd'T'HH:mm:ss.SSSXXX",
        "yyyy-MM-dd'T'HH:mm:ssXXX"
    ]
    for pattern in patterns:
        formatter = SimpleDateFormat(pattern)
        formatter.setLenient(False)
        position = ParsePosition(0)
        parsed = formatter.parse(text, position)
        if parsed is not None and position.getIndex() == len(text):
            return parsed
    raise ValidationError(
        constants.STATUS_VALIDATION_FAILED,
        "VAL-HDR-002",
        "MessageHeader.EventTimestamp must be a valid ISO-8601 timestamp",
        400
    )


# -----------------------------------------------------------------------------
# Function    : accepted_interface_names
# Description : Builds the allowed MessageHeader interface names for a route.
# -----------------------------------------------------------------------------
def accepted_interface_names(route_interface_name, config):
    names = [route_interface_name]
    configured = config.get("message_header_aliases") or []
    for name in configured:
        if name not in names:
            names.append(name)
    # M2S routes accept their directional MES name as well as the route name.
    direction = str(config.get("direction") or "")
    directional_name = "M2S.%s" % route_interface_name
    if direction.startswith("M2S") and directional_name not in names:
        names.append(directional_name)
    return names


# -----------------------------------------------------------------------------
# Function    : validate_inbound
# Description : Validates and normalizes an inbound MES MessageHeader.
# -----------------------------------------------------------------------------
def validate_inbound(payload, route_interface_name, config):
    if not isinstance(payload, dict) or not isinstance(payload.get("MessageHeader"), dict):
        raise ValidationError(
            constants.STATUS_VALIDATION_FAILED,
            "VAL-HDR-001",
            "MessageHeader is required",
            400
        )

    header = payload.get("MessageHeader")
    for field in REQUIRED_FIELDS:
        value = header.get(field)
        if not isinstance(value, basestring) or not value.strip():
            raise ValidationError(
                constants.STATUS_VALIDATION_FAILED,
                "VAL-HDR-001",
                "MessageHeader.%s is required and must be a string" % field,
                400
            )

    accepted = accepted_interface_names(route_interface_name, config)
    if header.get("InterfaceName") not in accepted:
        raise ValidationError(
            constants.STATUS_VALIDATION_FAILED,
            "VAL-HDR-003",
            "MessageHeader.InterfaceName does not match route. Expected one of: %s"
            % ", ".join(accepted),
            400
        )

    # Retain both the original wire value and parsed Date used by the context.
    parsed_timestamp = parse_event_timestamp(header.get("EventTimestamp"))
    return {
        "InterfaceName": header.get("InterfaceName").strip(),
        "TransactionId": header.get("TransactionId").strip(),
        "SourceSystem": header.get("SourceSystem").strip(),
        "TargetSystem": header.get("TargetSystem").strip(),
        "EventTimestamp": header.get("EventTimestamp").strip(),
        "ParsedEventTimestamp": parsed_timestamp
    }


# -----------------------------------------------------------------------------
# Function    : bind_inbound_context
# Description : Copies validated inbound header values into transaction context.
# -----------------------------------------------------------------------------
def bind_inbound_context(ctx, header, route_interface_name):
    ctx["route_interface_name"] = route_interface_name
    ctx["transaction_id"] = header.get("TransactionId")
    # MES TransactionId is the correlation key for the complete inbound flow.
    ctx["correlation_id"] = header.get("TransactionId")
    ctx["interface_name"] = header.get("InterfaceName")
    ctx["source_system"] = header.get("SourceSystem")
    ctx["target_system"] = header.get("TargetSystem")
    ctx["event_timestamp"] = header.get("EventTimestamp")
    ctx["request_time"] = header.get("ParsedEventTimestamp")
    return ctx


# -----------------------------------------------------------------------------
# Function    : create_outbound
# Description : Creates a configured MessageHeader for an outbound MES request.
# -----------------------------------------------------------------------------
def create_outbound(ctx, config):
    header = {
        "InterfaceName": config.get("mes_interface_name"),
        "TransactionId": ctx.get("transaction_id"),
        "SourceSystem": config.get("source_system", "SCADA"),
        "TargetSystem": config.get("target_system", "MES"),
        "EventTimestamp": ctx.get("event_timestamp") or utc_timestamp()
    }
    # Some MES operations require equipment/operator context in addition to the
    # common header contract. Include these fields only when configured so other
    # interfaces retain their existing payload shape.
    if config.get("equipment") is not None:
        header["Equipment"] = config.get("equipment")
    if config.get("employee_no") is not None:
        header["EmployeeNo"] = config.get("employee_no")
    return header


# -----------------------------------------------------------------------------
# Function    : wrap_outbound
# Description : Wraps MessageHeader and business data in the MES Inputs envelope.
# -----------------------------------------------------------------------------
def wrap_outbound(ctx, config, business_payload):
    payload_key = config.get("mes_payload_key")
    if not config.get("mes_interface_name") or not payload_key:
        raise Exception("Outbound MES MessageHeader configuration is incomplete")
    return {
        "Inputs": {
            "RequestJSON": {
                "MessageHeader": create_outbound(ctx, config),
                payload_key: business_payload
            }
        }
    }