##############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : store_and_forward.py
# Module         : Store-and-Forward Persistent Queue
#
# Description:
# Owns SQL persistence, atomic claims, expiry and recovery; router owns logging/audit.
#
# Author         : Hari
# Version        : 1.0
# Date           : 06-Sep-2026
#
# Change History
# ----------------------------------------------------------------------------
# Sl No | Version | Date        | Author | Fix/Change
# ----------------------------------------------------------------------------
# 1     | 1.0     | 06-Sep-2026 | Hari   | Store-and-Forward framework conventions and observability
# ----------------------------------------------------------------------------
##############################################################################

"""SQL Server durable queue. HTTP transport and PLC behavior live elsewhere."""
import system
from scada_interface import config, constants
from scada_interface.errors import StoreForwardError
try:
    from java.lang import Exception as JavaException
except ImportError:
    JavaException = Exception


_CONTEXT_FIELDS = ("transaction_id", "correlation_id", "interface_name",
                   "route_interface_name", "direction", "equipment_id",
                   "source_system", "target_system", "business_reference",
                   "event_timestamp", "retry_count")


# -----------------------------------------------------------------------------
# Function    : is_enabled
# Description : Checks the validated per-interface persistence opt-in.
# -----------------------------------------------------------------------------
def is_enabled(cfg):
    return config.get_store_forward_config(cfg).get("enabled") is True


# -----------------------------------------------------------------------------
# Function    : _query
# Description : Runs parameterized queue SQL and raises a sanitized persistence failure.
# -----------------------------------------------------------------------------
def _query(sql, args):
    try:
        return list(system.db.runPrepQuery(sql, args, constants.DB_NAME))
    except (Exception, JavaException):
        raise StoreForwardError("Store-and-Forward database operation failed")


# -----------------------------------------------------------------------------
# Function    : _validate_no_credentials
# Description : Rejects credential fields before persisting a resend envelope.
# -----------------------------------------------------------------------------
def _validate_no_credentials(value):
    if hasattr(value, "items"):
        for key, child in value.items():
            normalized = str(key).lower().replace("_", "").replace("-", "")
            if normalized in ("authorization", "accesstoken", "refreshtoken", "clientsecret", "password"):
                raise StoreForwardError("Credentials must not be persisted in the MES envelope")
            _validate_no_credentials(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _validate_no_credentials(child)


# -----------------------------------------------------------------------------
# Function    : enqueue
# Description : Persists the final envelope once without extending an existing expiry.
# -----------------------------------------------------------------------------
def enqueue(ctx, cfg, request_payload, failure):
    policy = config.get_store_forward_config(cfg)
    if policy.get("enabled") is not True:
        raise StoreForwardError("Store-and-Forward is disabled")
    if not ctx.get("transaction_id") or ctx.get("interface_name") != cfg.get("interface_name"):
        raise StoreForwardError("A matching transaction/interface context is required")
    saved = dict((key, ctx.get(key)) for key in _CONTEXT_FIELDS)
    saved["start_time_ms"] = system.date.toMillis(ctx["start_time"])
    saved["request_time_ms"] = system.date.toMillis(ctx["request_time"])
    _validate_no_credentials(request_payload)
    payload = system.util.jsonEncode(request_payload)
    ctx_json = system.util.jsonEncode(saved)
    # One statement owns the insert; the range lock serializes duplicate enqueues.
    rows = _query("""
        INSERT INTO dbo.interface_store_forward
        (transaction_id, interface_name, equipment_id, request_payload, context_payload,
         retry_interval_seconds, next_retry_time, expires_at,
         last_http_status, last_error_code, last_error_message)
        OUTPUT inserted.*
        SELECT ?, ?, ?, ?, ?, ?, DATEADD(second, ?, SYSUTCDATETIME()),
               DATEADD(second, ?, SYSUTCDATETIME()), ?, ?, ?
        WHERE NOT EXISTS (SELECT 1 FROM dbo.interface_store_forward WITH (UPDLOCK, HOLDLOCK)
                          WHERE transaction_id=?)
        """, [ctx["transaction_id"], cfg["interface_name"], ctx.get("equipment_id"),
              payload, ctx_json, policy["retry_interval_seconds"],
              policy["retry_interval_seconds"], int(policy["max_age_hours"] * 3600),
              getattr(failure, "mes_http_status", None),
              getattr(failure, "error_code", "MES-SF-001"),
              getattr(failure, "message", "MES delivery unavailable"), ctx["transaction_id"]])
    if rows:
        return rows[0]
    rows = _query("SELECT * FROM dbo.interface_store_forward WHERE transaction_id=?",
                  [ctx["transaction_id"]])
    if (not rows or rows[0]["request_payload"] != payload
            or rows[0]["interface_name"] != cfg["interface_name"]):
        raise StoreForwardError("Transaction ID already belongs to a different request")
    return rows[0]


# -----------------------------------------------------------------------------
# Function    : claim_due_requests
# Description : Atomically claims due rows for one worker with a bounded lease.
# -----------------------------------------------------------------------------
def claim_due_requests(batch_size, worker_id, interface_names, lease_seconds):
    # Dispatcher passes batch_size=1 to avoid leases aging while HTTP work waits.
    if not interface_names:
        return []
    placeholders = ",".join(["?"] * len(interface_names))
    return _query("""
        ;WITH due AS (
            SELECT TOP (?) * FROM dbo.interface_store_forward
                WITH (UPDLOCK, READPAST, READCOMMITTEDLOCK)
            WHERE queue_status='PENDING' AND next_retry_time<=SYSUTCDATETIME()
              AND expires_at>SYSUTCDATETIME() AND interface_name IN (%s)
            ORDER BY next_retry_time, id
        )
        UPDATE due SET queue_status='IN_PROGRESS', locked_by=?,
            locked_at=SYSUTCDATETIME(), lease_expires_at=DATEADD(second, ?, SYSUTCDATETIME()),
            last_retry_at=SYSUTCDATETIME(), persistent_retry_count=persistent_retry_count+1,
            updated_at=SYSUTCDATETIME()
        OUTPUT inserted.*
        """ % placeholders, [int(batch_size)] + list(interface_names) + [worker_id, int(lease_seconds)])


# -----------------------------------------------------------------------------
# Function    : _finish
# Description : Commits a terminal state only while the worker still owns its lease.
# -----------------------------------------------------------------------------
def _finish(queue_id, worker_id, state, failure=None, http_status=None):
    return _query("""
        UPDATE dbo.interface_store_forward SET queue_status=?,
            completed_at=SYSUTCDATETIME(), last_http_status=?, last_error_code=?,
            last_error_message=?, locked_by=NULL, locked_at=NULL, lease_expires_at=NULL,
            updated_at=SYSUTCDATETIME()
        OUTPUT inserted.*
        WHERE id=? AND queue_status='IN_PROGRESS' AND locked_by=?
          AND lease_expires_at>SYSUTCDATETIME()
        """, [state, http_status, getattr(failure, "error_code", None),
              getattr(failure, "message", None), queue_id, worker_id])


# -----------------------------------------------------------------------------
# Function    : mark_delivered
# Description : Records confirmed MES acceptance under the current claim.
# -----------------------------------------------------------------------------
def mark_delivered(queue_id, worker_id, http_status=None):
    return _finish(queue_id, worker_id, "DELIVERED", http_status=http_status)


# -----------------------------------------------------------------------------
# Function    : mark_failed
# Description : Stops automatic delivery after permanent rejection or corrupt data.
# -----------------------------------------------------------------------------
def mark_failed(queue_id, worker_id, failure):
    return _finish(queue_id, worker_id, "FAILED", failure,
                   getattr(failure, "mes_http_status", None))


# -----------------------------------------------------------------------------
# Function    : mark_expired
# Description : Closes a claimed request when its business deadline prevents delivery.
# -----------------------------------------------------------------------------
def mark_expired(queue_id, worker_id, failure=None):
    return _finish(queue_id, worker_id, "EXPIRED", failure)


# -----------------------------------------------------------------------------
# Function    : schedule_next_retry
# Description : Reschedules a technical failure using the stored retry interval.
# -----------------------------------------------------------------------------
def schedule_next_retry(queue_id, worker_id, failure):
    return _query("""
        UPDATE dbo.interface_store_forward SET
            queue_status=CASE WHEN expires_at<=SYSUTCDATETIME() THEN 'EXPIRED' ELSE 'PENDING' END,
            completed_at=CASE WHEN expires_at<=SYSUTCDATETIME() THEN SYSUTCDATETIME() ELSE NULL END,
            next_retry_time=DATEADD(second, retry_interval_seconds, SYSUTCDATETIME()),
            last_http_status=?, last_error_code=?, last_error_message=?,
            locked_by=NULL, locked_at=NULL, lease_expires_at=NULL, updated_at=SYSUTCDATETIME()
        OUTPUT inserted.*
        WHERE id=? AND queue_status='IN_PROGRESS' AND locked_by=?
          AND lease_expires_at>SYSUTCDATETIME()
        """, [getattr(failure, "mes_http_status", None), failure.error_code,
              failure.message, queue_id, worker_id])


# -----------------------------------------------------------------------------
# Function    : release_stale_locks
# Description : Returns abandoned claims to the pending queue after lease expiry.
# -----------------------------------------------------------------------------
def release_stale_locks():
    # Never release a live worker based on the business expiry alone.
    return _query("""
        UPDATE dbo.interface_store_forward SET queue_status='PENDING',
            locked_by=NULL, locked_at=NULL, lease_expires_at=NULL, updated_at=SYSUTCDATETIME()
        OUTPUT inserted.*
        WHERE queue_status='IN_PROGRESS' AND lease_expires_at<=SYSUTCDATETIME()
        """, [])


# -----------------------------------------------------------------------------
# Function    : expire_due_requests
# Description : Closes overdue pending requests without sending to MES.
# -----------------------------------------------------------------------------
def expire_due_requests():
    return _query("""
        UPDATE dbo.interface_store_forward SET queue_status='EXPIRED',
            completed_at=SYSUTCDATETIME(), updated_at=SYSUTCDATETIME()
        OUTPUT inserted.*
        WHERE queue_status='PENDING' AND expires_at<=SYSUTCDATETIME()
        """, [])


# -----------------------------------------------------------------------------
# Function    : can_send
# Description : Checks current ownership and business expiry immediately before HTTP.
# -----------------------------------------------------------------------------
def can_send(queue_id, worker_id):
    return bool(_query("""
        SELECT id FROM dbo.interface_store_forward WHERE id=? AND locked_by=?
        AND queue_status='IN_PROGRESS' AND expires_at>SYSUTCDATETIME()
        AND lease_expires_at>SYSUTCDATETIME()
        """, [queue_id, worker_id]))