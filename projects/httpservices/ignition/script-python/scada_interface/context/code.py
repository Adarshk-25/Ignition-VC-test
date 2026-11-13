###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : context.py
# Module         : Transaction Context
#
# Description:
# Creates transaction context values such as transaction id, correlation id,
# source/target metadata, start time, retry count and shared error collection.
# Persistent replay restores original identity and request timestamps.
#
# Author         : Hari
# Version        : 1.1
# Date           : 06-Sep-2026
#
# Change History
# -----------------------------------------------------------------------------
# Sl No | Version | Date        | Author | Fix/Change
# -----------------------------------------------------------------------------
# 1     | 1.0     | 07-Jul-2026 | Hari   | Initial documented version
# 2     | 1.1     | 06-Sep-2026 | Hari   | Store-and-Forward audit, debug and observability conventions
# -----------------------------------------------------------------------------
###############################################################################

import random
from java.text import SimpleDateFormat
from java.util import Date


# -----------------------------------------------------------------------------
# Function    : _timestamp
# Description : Handles timestamp logic for this module.
# -----------------------------------------------------------------------------
def _timestamp():
    return SimpleDateFormat("yyyyMMddHHmmssSSS").format(Date())


# -----------------------------------------------------------------------------
# Function    : get_header
# Description : Handles get header logic for this module.
# -----------------------------------------------------------------------------
def get_header(request, name):
    headers = getattr(request, "headers", {}) or {}
    return headers.get(name) or headers.get(name.lower())


# -----------------------------------------------------------------------------
# Function    : create_context
# Description : Handles create context logic for this module.
# -----------------------------------------------------------------------------
def create_context(
    interface_name,
    direction,
    request=None,
    equipment_id=None,
    transaction_prefix=None
):
    correlation_id = None
    source_system = None

    # Inbound REST calls can pass tracking metadata that should flow through audit/logs.
    if request is not None:
        correlation_id = get_header(request, "X-Correlation-ID")
        source_system = get_header(request, "X-Source-System")

    # Transaction ids are generated in SCADA so every downstream step can be joined.
    if transaction_prefix:
        transaction_id = "%s-%s-%s" % (
            str(transaction_prefix).upper(),
            _timestamp(),
            random.randint(1000, 9999)
        )
    else:
        transaction_id = "TXN-%s-%s-%s" % (
            interface_name.upper(),
            _timestamp(),
            random.randint(1000, 9999)
        )

    return {
        "transaction_id": transaction_id,
        "correlation_id": correlation_id or transaction_id,
        "interface_name": interface_name,
        "route_interface_name": interface_name,
        "direction": direction,
        "equipment_id": equipment_id,
        "source_system": source_system or "UNKNOWN",
        "target_system": None,
        "business_reference": None,
        "start_time": system.date.now(),
        "request_time": system.date.now(),
        "event_timestamp": None,
        "retry_count": 0,
        "errors": []
    }


# -----------------------------------------------------------------------------
# Function    : from_persisted_transaction
# Description : Restores original transaction identity and timestamps for replay.
# -----------------------------------------------------------------------------
def from_persisted_transaction(row):
    import system
    ctx = system.util.jsonDecode(row["context_payload"])
    if (ctx.get("transaction_id") != row["transaction_id"]
            or ctx.get("interface_name") != row["interface_name"]):
        raise ValueError("Persisted transaction identity mismatch")
    ctx["start_time"] = system.date.fromMillis(long(ctx.pop("start_time_ms")))
    ctx["request_time"] = system.date.fromMillis(long(ctx.pop("request_time_ms")))
    ctx["errors"] = []
    ctx["persistent_retry_count"] = row["persistent_retry_count"]
    return ctx