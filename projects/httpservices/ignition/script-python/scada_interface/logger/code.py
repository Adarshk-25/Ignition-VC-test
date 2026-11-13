###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : logger.py
# Module         : Structured Logger
#
# Description:
# Creates consistent Ignition Gateway log records with transaction, correlation,
# interface, equipment, step, status, retry count and message fields.
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
import system.util


# -----------------------------------------------------------------------------
# Function    : _log
# Description : Handles log logic for this module.
# -----------------------------------------------------------------------------
def _log(level, ctx, step, status, message, extra=None):
    logger_name = "SCADA.Interface.%s" % ctx.get("interface_name", "Framework")
    log = system.util.getLogger(logger_name)

    # Keep every framework log queryable by the same transaction/correlation fields.
    record = {
        "interface": ctx.get("interface_name"),
        "direction": ctx.get("direction"),
        "transaction_id": ctx.get("transaction_id"),
        "correlation_id": ctx.get("correlation_id"),
        "equipment_id": ctx.get("equipment_id"),
        "step": step,
        "status": status,
        "retry_count": ctx.get("retry_count", 0),
        "message": message
    }
    if extra:
        record.update(extra)

    text = system.util.jsonEncode(record)
    if level == "ERROR":
        log.error(text)
    elif level == "WARN":
        log.warn(text)
    elif level == "DEBUG":
        log.debug(text)
    else:
        log.info(text)


# -----------------------------------------------------------------------------
# Function    : info
# Description : Handles info logic for this module.
# -----------------------------------------------------------------------------
def info(ctx, step, status, message, extra=None):
    _log("INFO", ctx, step, status, message, extra)


# -----------------------------------------------------------------------------
# Function    : warn
# Description : Handles warn logic for this module.
# -----------------------------------------------------------------------------
def warn(ctx, step, status, message, extra=None):
    _log("WARN", ctx, step, status, message, extra)


# -----------------------------------------------------------------------------
# Function    : debug
# Description : Handles debug logic for this module.
# -----------------------------------------------------------------------------
def debug(ctx, step, status, message, extra=None):
    _log("DEBUG", ctx, step, status, message, extra)


# -----------------------------------------------------------------------------
# Function    : debug_enabled
# Description : Returns True only when interface diagnostics are explicitly on.
# -----------------------------------------------------------------------------
def debug_enabled(config):
    return config is not None and config.get("debug_enabled", False) is True


# -----------------------------------------------------------------------------
# Function    : diagnostic
# Description : Emits reusable config-controlled diagnostics at Gateway INFO.
# -----------------------------------------------------------------------------
def diagnostic(ctx, config, step, message, extra=None):
    if debug_enabled(config):
        # INFO is intentional so enabling the interface flag is sufficient and
        # does not also require changing the Gateway logger level to DEBUG.
        _log("INFO", ctx, step, "DEBUG_MODE", message, extra)


# -----------------------------------------------------------------------------
# Function    : error
# Description : Handles error logic for this module.
# -----------------------------------------------------------------------------
def error(ctx, step, status, message, extra=None):
    _log("ERROR", ctx, step, status, message, extra)