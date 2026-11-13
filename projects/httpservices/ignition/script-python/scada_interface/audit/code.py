###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : audit.py
# Module         : Transaction Audit
#
# Description:
# Writes transaction headers, processing steps, payload audit records and final
# success/failure state to the SCADA interface audit database tables.
# Store-and-Forward records queue outcomes and independent dispatcher-cycle steps.
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

import system
import system.db
import system.util
from scada_interface import constants


# -----------------------------------------------------------------------------
# Function    : start_transaction
# Description : Handles start transaction logic for this module.
# -----------------------------------------------------------------------------
def start_transaction(ctx, config):
    query = """
    INSERT INTO interface_transaction
    (transaction_id, correlation_id, interface_name, direction, equipment_id,
     business_reference, source_system, target_system, request_time,
     overall_status, status_code, created_by)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME(), ?, ?, ?)
    """
    args = [
        ctx.get("transaction_id"),
        ctx.get("correlation_id"),
        ctx.get("interface_name"),
        ctx.get("direction"),
        ctx.get("equipment_id"),
        ctx.get("business_reference"),
        ctx.get("source_system"),
        ctx.get("target_system"),
        "RECEIVED",
        constants.STATUS_ACCEPTED,
        ctx.get("source_system")
    ]
    system.db.runPrepUpdate(query, args, constants.DB_NAME)


# -----------------------------------------------------------------------------
# Function    : transaction_exists
# Description : Checks whether a transaction ID already exists in the audit log.
# -----------------------------------------------------------------------------
def transaction_exists(transaction_id):
    query = """
    SELECT COUNT(1)
    FROM interface_transaction
    WHERE transaction_id = ?
    """
    count = system.db.runScalarPrepQuery(query, [transaction_id], constants.DB_NAME)
    return int(count or 0) > 0


# -----------------------------------------------------------------------------
# Function    : update_transaction_context
# Description : Persists business context discovered after transaction creation.
# -----------------------------------------------------------------------------
def update_transaction_context(ctx):
    """Persist business fields discovered after the transaction was started."""
    query = """
    UPDATE interface_transaction
    SET equipment_id = ?, business_reference = ?, source_system = ?,
        target_system = ?, updated_at = SYSUTCDATETIME()
    WHERE transaction_id = ?
    """
    args = [
        ctx.get("equipment_id"),
        ctx.get("business_reference"),
        ctx.get("source_system"),
        ctx.get("target_system"),
        ctx.get("transaction_id")
    ]
    system.db.runPrepUpdate(query, args, constants.DB_NAME)


# -----------------------------------------------------------------------------
# Function    : log_step
# Description : Handles log step logic for this module.
# -----------------------------------------------------------------------------
def log_step(ctx, step_name, step_status, details=None, error_code=None, error_message=None):
    query = """
    INSERT INTO interface_transaction_step
    (transaction_id, interface_name, step_name, step_status, details, error_code, error_message, retry_count)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    args = [
        ctx.get("transaction_id"),
        ctx.get("interface_name"),
        step_name,
        step_status,
        system.util.jsonEncode(details or {}),
        error_code,
        error_message,
        ctx.get("retry_count", 0)
    ]
    system.db.runPrepUpdate(query, args, constants.DB_NAME)


# -----------------------------------------------------------------------------
# Function    : save_payload
# Description : Handles save payload logic for this module.
# -----------------------------------------------------------------------------
def save_payload(ctx, payload_type, payload, mode):
    if mode == "NONE":
        return

    body = system.util.jsonEncode(payload) if payload is not None else None
    payload_hash = str(hash(body)) if body is not None else None

    # HASH_ONLY proves payload capture occurred without storing sensitive body data.
    if mode == "HASH_ONLY":
        body = None

    query = """
    INSERT INTO interface_payload_audit
    (transaction_id, interface_name, payload_type, payload_hash, payload_body)
    VALUES (?, ?, ?, ?, ?)
    """
    args = [
        ctx.get("transaction_id"),
        ctx.get("interface_name"),
        payload_type,
        payload_hash,
        body
    ]
    system.db.runPrepUpdate(query, args, constants.DB_NAME)


# -----------------------------------------------------------------------------
# Function    : complete_transaction
# Description : Handles complete transaction logic for this module.
# -----------------------------------------------------------------------------
def complete_transaction(ctx, status_code, http_status=None, opc_status=None):
    duration_ms = system.date.millisBetween(ctx.get("start_time"), system.date.now())
    query = """
    UPDATE interface_transaction
    SET overall_status = ?, status_code = ?, end_time = SYSUTCDATETIME(),
        total_duration_ms = ?, http_status = ?, opc_status = ?, retry_count = ?,
        updated_at = SYSUTCDATETIME()
    WHERE transaction_id = ?
    """
    args = [
        "COMPLETED",
        status_code,
        duration_ms,
        http_status,
        opc_status,
        ctx.get("retry_count", 0),
        ctx.get("transaction_id")
    ]
    system.db.runPrepUpdate(query, args, constants.DB_NAME)


# -----------------------------------------------------------------------------
# Function    : fail_transaction
# Description : Handles fail transaction logic for this module.
# -----------------------------------------------------------------------------
def fail_transaction(ctx, status_code, error_code, error_message):
    duration_ms = system.date.millisBetween(ctx.get("start_time"), system.date.now())
    query = """
    UPDATE interface_transaction
    SET overall_status = ?, status_code = ?, end_time = SYSUTCDATETIME(),
        total_duration_ms = ?, error_code = ?, error_message = ?,
        retry_count = ?, updated_at = SYSUTCDATETIME()
    WHERE transaction_id = ?
    """
    args = [
        "FAILED",
        status_code,
        duration_ms,
        error_code,
        error_message,
        ctx.get("retry_count", 0),
        ctx.get("transaction_id")
    ]
    system.db.runPrepUpdate(query, args, constants.DB_NAME)


# -----------------------------------------------------------------------------
# Function    : record_store_forward
# Description : Updates business audit state and records separate persistent counters.
# -----------------------------------------------------------------------------
def record_store_forward(ctx, state, details=None):
    """Queue state has already committed. This method never controls delivery."""
    terminal = state in ("DELIVERED", "EXPIRED", "FAILED")
    overall = "COMPLETED" if state == "DELIVERED" else ("FAILED" if terminal else "QUEUED")
    system.db.runPrepUpdate("""
        UPDATE interface_transaction SET overall_status=?, status_code=?,
        end_time=CASE WHEN ?=1 THEN SYSUTCDATETIME() ELSE NULL END,
        retry_count=COALESCE(?, retry_count), http_status=COALESCE(?, http_status),
        error_code=?, error_message=?,
        total_duration_ms=CASE WHEN ?=1 THEN DATEDIFF_BIG(millisecond,request_time,SYSUTCDATETIME())
                               ELSE total_duration_ms END,
        updated_at=SYSUTCDATETIME() WHERE transaction_id=?
        """, [overall, "STORE_FORWARD_" + state, 1 if terminal else 0,
              ctx.get("retry_count"), (details or {}).get("last_http_status"),
              (details or {}).get("last_error_code"), (details or {}).get("last_error_message"),
              1 if terminal else 0, ctx["transaction_id"]], constants.DB_NAME)
    step = {"PENDING": "ENQUEUE", "IN_PROGRESS": "RETRY"}.get(state, state)
    if state == "PENDING" and (details or {}).get("persistent_retry_count", 0) > 0:
        step = "RETRY"
    log_step(ctx, "STORE_FORWARD_" + step, state, details,
             (details or {}).get("last_error_code"),
             (details or {}).get("last_error_message"))


# -----------------------------------------------------------------------------
# Function    : log_store_forward_event
# Description : Writes operational step evidence using the existing audit schema.
# -----------------------------------------------------------------------------
def log_store_forward_event(ctx, step, status, details=None, error_code=None):
    """Dispatcher events have a cycle ID and do not update business transactions."""
    log_step(ctx, step, status, details, error_code)
