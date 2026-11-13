###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : router.py
# Module         : Common Interface Router
#
# Description:
# Main entry point for WebDev and AG Calls routes. It loads interface config,
# invokes authentication, validation, handlers, audit logging and responses.
# Store-and-Forward adds persistent submission, dispatcher audit and opt-in diagnostics.
#
# Author         : Hari
# Version        : 1.2
# Date           : 09-Sep-2026
#
# Change History
# -----------------------------------------------------------------------------
# Sl No | Version | Date        | Author | Fix/Change
# -----------------------------------------------------------------------------
# 1     | 1.0     | 07-Jul-2026 | Hari   | Initial documented version
# 2     | 1.1     | 06-Sep-2026 | Hari   | Store-and-Forward audit, debug and observability conventions
# 3     | 1.2     | 09-Sep-2026 | Hari   | Preserve structured AG-call validation diagnostics
# -----------------------------------------------------------------------------
###############################################################################

from java.lang import Exception as JavaException
from java.util.concurrent.atomic import AtomicBoolean
from scada_interface import ag_call_routing, audit, config, constants, context, environment, logger, message_header, oauth, response, validation
from scada_interface.errors import DuplicateTransactionError, InterfaceError, RoutingError


_SCHEDULE_ACTIVE = AtomicBoolean(False)
_SCHEDULE_OWNER = [None]


# -----------------------------------------------------------------------------
# Function    : _is_delivery_retryable
# Description : Classifies typed MES delivery failures inside the router.
# -----------------------------------------------------------------------------
def _is_delivery_retryable(failure):
    # Keep orchestration independent from Ignition's project-module attribute
    # proxy, which may not expose newly added rest_client helper functions until
    # its script cache is fully recompiled.
    from scada_interface.errors import MesDeliveryError
    return isinstance(failure, MesDeliveryError) and failure.eligible is True


# -----------------------------------------------------------------------------
# Function    : _normalize_handler_module
# Description : Handles normalize handler module logic for this module.
# -----------------------------------------------------------------------------
def _normalize_handler_module(handler_module):
    if not handler_module:
        raise Exception("Handler module is not configured")

    old_prefix = "project.scada_interface."
    if handler_module.startswith(old_prefix):
        return "scada_interface." + handler_module[len(old_prefix):]
    return handler_module


# -----------------------------------------------------------------------------
# Function    : _load_handler
# Description : Handles load handler logic for this module.
# -----------------------------------------------------------------------------
def _load_handler(handler_module):
    handler_module = _normalize_handler_module(handler_module)
    components = handler_module.split(".")
    module = __import__(handler_module)
    # Jython __import__ returns the package root, so walk to the final module.
    for component in components[1:]:
        module = getattr(module, component)
    return module


# -----------------------------------------------------------------------------
# Function    : _is_webdev_response
# Description : Handles is webdev response logic for this module.
# -----------------------------------------------------------------------------
def _is_webdev_response(value):
    return isinstance(value, dict) and "json" in value and "status" in value


# -----------------------------------------------------------------------------
# Function    : _success_response
# Description : Handles success response logic for this module.
# -----------------------------------------------------------------------------
def _success_response(handler, ctx, result):
    if _is_webdev_response(result):
        return result

    if hasattr(handler, "build_success_response"):
        custom = handler.build_success_response(ctx, result)
        if _is_webdev_response(custom):
            return custom

    return response.success(ctx, result)


# -----------------------------------------------------------------------------
# Function    : _failure_response
# Description : Handles failure response logic for this module.
# -----------------------------------------------------------------------------
def _failure_response(handler, ctx, ex):
    if hasattr(handler, "build_failure_response"):
        custom = handler.build_failure_response(ctx, ex.message)
        if _is_webdev_response(custom):
            return custom

    return response.failure(ctx, ex.status_code, ex.error_code, ex.message, ex.http_status, ctx.get("errors"))


# -----------------------------------------------------------------------------
# Function    : _system_failure_response
# Description : Handles system failure response logic for this module.
# -----------------------------------------------------------------------------
def _system_failure_response(handler, ctx, message):
    if hasattr(handler, "build_failure_response"):
        custom = handler.build_failure_response(ctx, message)
        if _is_webdev_response(custom):
            return custom

    return response.failure(ctx, constants.STATUS_SCADA_INTERNAL_ERROR, "SYS-0001", message, 500)


# -----------------------------------------------------------------------------
# Function    : _handle_system_failure
# Description : Handles handle system failure logic for this module.
# -----------------------------------------------------------------------------
def _handle_system_failure(handler, ctx, ex):
    message = str(ex)
    audit.log_step(ctx, constants.STEP_FAILED, "FAILED", None, "SYS-0001", message)
    audit.fail_transaction(ctx, constants.STATUS_SCADA_INTERNAL_ERROR, "SYS-0001", message)
    logger.error(ctx, constants.STEP_FAILED, "FAILED", message, {"error_code": "SYS-0001"})
    return _system_failure_response(handler, ctx, message)


# -----------------------------------------------------------------------------
# Function    : _audit_interface_failure
# Description : Persists failures raised before or after the normal audit insert.
# -----------------------------------------------------------------------------
def _audit_interface_failure(ctx, cfg, ex, payload, audit_started, fallback_transaction_id):
    logger.debug(
        ctx,
        constants.STEP_FAILED,
        "DEBUG",
        "Entering interface failure audit",
        {
            "audit_started": audit_started,
            "audit_db": constants.DB_NAME,
            "error_code": ex.error_code,
            "fallback_transaction_id": fallback_transaction_id,
            "payload_available": payload is not None,
            "router_revision": "fallback-audit-debug-v1"
        }
    )

    if not audit_started:
        submitted_transaction_id = ctx.get("transaction_id")
        ctx["transaction_id"] = fallback_transaction_id
        if submitted_transaction_id and submitted_transaction_id != fallback_transaction_id:
            ctx["correlation_id"] = submitted_transaction_id

        try:
            logger.debug(
                ctx,
                constants.STEP_FAILED,
                "DEBUG",
                "Creating fallback interface_transaction row",
                {"audit_db": constants.DB_NAME}
            )
            audit.start_transaction(ctx, cfg)
            audit_started = True
            logger.debug(
                ctx,
                constants.STEP_FAILED,
                "DEBUG",
                "Fallback interface_transaction row created",
                {"audit_db": constants.DB_NAME}
            )
        except Exception, audit_ex:
            logger.error(
                ctx,
                constants.STEP_FAILED,
                "FAILED",
                "Failed to create fallback audit transaction: %s" % str(audit_ex),
                {"audit_db": constants.DB_NAME, "error_code": "AUDIT-0001"}
            )
            return False

        if payload is not None:
            try:
                audit.save_payload(ctx, "REQUEST", payload, cfg.get("payload_logging_mode", "HASH_ONLY"))
                logger.debug(
                    ctx,
                    constants.STEP_FAILED,
                    "DEBUG",
                    "Rejected request payload audit saved",
                    {
                        "audit_db": constants.DB_NAME,
                        "payload_logging_mode": cfg.get("payload_logging_mode", "HASH_ONLY")
                    }
                )
            except Exception, audit_ex:
                logger.error(
                    ctx,
                    constants.STEP_FAILED,
                    "FAILED",
                    "Failed to save rejected request payload audit: %s" % str(audit_ex),
                    {"audit_db": constants.DB_NAME, "error_code": "AUDIT-0001"}
                )

    try:
        audit.log_step(ctx, constants.STEP_FAILED, "FAILED", ex.details, ex.error_code, ex.message)
        logger.debug(
            ctx,
            constants.STEP_FAILED,
            "DEBUG",
            "interface_transaction_step failure row created",
            {"audit_db": constants.DB_NAME, "error_code": ex.error_code}
        )
    except Exception, audit_ex:
        logger.error(
            ctx,
            constants.STEP_FAILED,
            "FAILED",
            "Failed to insert interface_transaction_step: %s" % str(audit_ex),
            {"audit_db": constants.DB_NAME, "error_code": "AUDIT-0002"}
        )

    try:
        audit.fail_transaction(ctx, ex.status_code, ex.error_code, ex.message)
        logger.debug(
            ctx,
            constants.STEP_FAILED,
            "DEBUG",
            "interface_transaction updated to FAILED",
            {"audit_db": constants.DB_NAME, "error_code": ex.error_code}
        )
    except Exception, audit_ex:
        logger.error(
            ctx,
            constants.STEP_FAILED,
            "FAILED",
            "Failed to update interface_transaction to FAILED: %s" % str(audit_ex),
            {"audit_db": constants.DB_NAME, "error_code": "AUDIT-0003"}
        )

    return audit_started


# -----------------------------------------------------------------------------
# Function    : handle_rest_request
# Description : Handles handle rest request logic for this module.
# -----------------------------------------------------------------------------
def handle_rest_request(interface_name, direction, request):
    cfg = config.get_interface_config(interface_name)
    handler = _load_handler(cfg.get("handler_module"))
    ctx = context.create_context(interface_name, direction, request=request)
    fallback_transaction_id = ctx.get("transaction_id")
    audit_started = False
    payload = None

    logger.diagnostic(ctx, cfg, constants.STEP_REQUEST_RECEIVED, "REST router processing started", {
        "route_interface_name": interface_name,
        "direction": direction
    })

    logger.debug(
        ctx,
        constants.STEP_REQUEST_RECEIVED,
        "DEBUG",
        "Router request handling started",
        {
            "audit_db": constants.DB_NAME,
            "fallback_transaction_id": fallback_transaction_id,
            "router_revision": "fallback-audit-debug-v1"
        }
    )

    try:
        # Parse and validate the MES-owned header before inserting audit data.
        payload = validation.parse_json_request(request, ctx)
        header = message_header.validate_inbound(payload, interface_name, cfg)
        message_header.bind_inbound_context(ctx, header, interface_name)

        if audit.transaction_exists(ctx.get("transaction_id")):
            raise DuplicateTransactionError(
                constants.STATUS_DUPLICATE_TRANSACTION,
                "DUP-0001",
                "Duplicate MessageHeader.TransactionId: %s" % ctx.get("transaction_id"),
                409
            )

        audit.start_transaction(ctx, cfg)
        audit_started = True
        logger.info(ctx, constants.STEP_REQUEST_RECEIVED, "RECEIVED", "REST request received")
        audit.log_step(ctx, constants.STEP_REQUEST_RECEIVED, "SUCCESS")

        if cfg.get("auth_required"):
            if not hasattr(oauth, "validate_inbound_request"):
                raise Exception(
                    "OAuth project script is missing validate_inbound_request; "
                    "deploy and publish scada_interface/oauth.py"
                )
            oauth.validate_inbound_request(request, ctx, cfg)
        else:
            logger.debug(
                ctx,
                constants.STEP_AUTHENTICATION,
                "SKIPPED",
                "Inbound authentication is disabled for this interface",
                {"router_revision": "fallback-audit-debug-v1"}
            )
        audit.log_step(ctx, constants.STEP_AUTHENTICATION, "SUCCESS")

        audit.save_payload(ctx, "REQUEST", payload, cfg.get("payload_logging_mode", "HASH_ONLY"))
        validation.validate_payload(handler.SCHEMA, payload)
        audit.log_step(ctx, constants.STEP_PAYLOAD_VALIDATION, "SUCCESS")

        handler.validate_business_rules(ctx, payload, cfg)
        audit.update_transaction_context(ctx)
        audit.log_step(ctx, constants.STEP_BUSINESS_VALIDATION, "SUCCESS")

        result = handler.process(ctx, payload, cfg)

        audit.save_payload(ctx, "RESPONSE", result, cfg.get("payload_logging_mode", "HASH_ONLY"))
        audit.complete_transaction(ctx, constants.STATUS_SUCCESS)
        audit.log_step(ctx, constants.STEP_COMPLETED, "SUCCESS")
        logger.info(ctx, constants.STEP_COMPLETED, "SUCCESS", "REST request completed")
        logger.diagnostic(ctx, cfg, constants.STEP_COMPLETED, "REST router processing completed")
        return _success_response(handler, ctx, result)

    except InterfaceError, ex:
        ctx["errors"].append({"error_code": ex.error_code, "error_message": ex.message})
        audit_started = _audit_interface_failure(
            ctx,
            cfg,
            ex,
            payload,
            audit_started,
            fallback_transaction_id
        )
        logger.error(ctx, constants.STEP_FAILED, "FAILED", ex.message, {"error_code": ex.error_code})
        return _failure_response(handler, ctx, ex)

    except JavaException, ex:
        if not audit_started:
            message = str(ex)
            logger.error(ctx, constants.STEP_FAILED, "FAILED", message, {"error_code": "SYS-0001"})
            return _system_failure_response(handler, ctx, message)
        return _handle_system_failure(handler, ctx, ex)

    except Exception, ex:
        if not audit_started:
            message = str(ex)
            logger.error(ctx, constants.STEP_FAILED, "FAILED", message, {"error_code": "SYS-0001"})
            return _system_failure_response(handler, ctx, message)
        return _handle_system_failure(handler, ctx, ex)


# -----------------------------------------------------------------------------
# Function    : handle_scheduled_request
# Description : Runs one non-overlapping scheduled interface transaction.
# -----------------------------------------------------------------------------
def handle_scheduled_request(interface_name):
    cfg = config.get_interface_config(interface_name)
    if (cfg.get("target_type") != constants.TARGET_MES_REST_TAG_WRITE
            or not str(cfg.get("direction") or "").startswith("SCHEDULED_")):
        raise RoutingError("CONFIGURATION_ERROR", "CFG-HB-002",
                           "Interface is not configured for scheduled MES/tag routing", 500)

    if not _SCHEDULE_ACTIVE.compareAndSet(False, True):
        skipped_ctx = {"interface_name": interface_name, "direction": cfg.get("direction"),
                       "transaction_id": None, "correlation_id": None,
                       "equipment_id": None, "retry_count": 0}
        logger.warn(skipped_ctx, "SCHEDULE_SKIPPED", "SKIPPED",
                    "Scheduled cycle is already running",
                    {"error_code": "SCH-HB-001", "active_transaction_id": _SCHEDULE_OWNER[0]})
        return {"success": False, "skipped": True, "error_code": "SCH-HB-001",
                "active_transaction_id": _SCHEDULE_OWNER[0]}

    handler = None
    ctx = None
    audit_started = False
    try:
        handler = _load_handler(cfg.get("handler_module"))
        ctx = context.create_context(interface_name, cfg.get("direction"),
                                     transaction_prefix=cfg.get("transaction_prefix"))
        _SCHEDULE_OWNER[0] = ctx.get("transaction_id")
        ctx["source_system"] = cfg.get("source_system", "SCADA")
        ctx["target_system"] = cfg.get("target_system", "MES")
        ctx["event_timestamp"] = message_header.utc_timestamp()
        ctx["request_time"] = message_header.parse_event_timestamp(ctx.get("event_timestamp"))
        ctx["active_zone"] = str(environment.get_path("zone"))
        ctx["business_reference"] = ctx.get("active_zone")

        business_payload = handler.build_request(ctx, cfg)
        audit.start_transaction(ctx, cfg)
        audit_started = True
        handler.validate_business_rules(ctx, business_payload, cfg)
        audit.log_step(ctx, constants.STEP_REQUEST_RECEIVED, "SUCCESS", {
            "environment": environment.name(),
            "active_zone": ctx.get("active_zone"),
            "configured_plc_count": ctx.get("configured_plc_count")
        })
        audit.save_payload(ctx, "REQUEST", message_header.wrap_outbound(ctx, cfg, business_payload),
                           cfg.get("payload_logging_mode", "HASH_ONLY"))
        audit.update_transaction_context(ctx)
        audit.log_step(ctx, constants.STEP_BUSINESS_VALIDATION, "SUCCESS")
        result = handler.process(ctx, business_payload, cfg)
        audit.save_payload(ctx, "RESPONSE", result.get("mes_response", result),
                           cfg.get("payload_logging_mode", "HASH_ONLY"))

        if result.get("success"):
            audit.complete_transaction(ctx, constants.STATUS_SUCCESS)
            audit.log_step(ctx, constants.STEP_COMPLETED, "SUCCESS", result)
            logger.info(ctx, constants.STEP_COMPLETED, "SUCCESS", "MES heartbeat completed", result)
        else:
            failed_writes = int(result.get("failed_write_count", 0))
            if failed_writes == int(result.get("configured_plc_count", 0)):
                error_code = "TAG-HB-001"
                status_code = "PLC_TAG_WRITE_FAILED"
                message = "All heartbeat PLC tag writes failed"
            elif failed_writes > 0:
                error_code = "TAG-HB-002"
                status_code = "PLC_TAG_WRITE_PARTIAL"
                message = "One or more heartbeat PLC tag writes failed"
            else:
                error_code = "MES-HB-STATUS-%s" % result.get("mes_status")
                status_code = constants.STATUS_MES_BUSINESS_REJECTED
                message = "MES heartbeat returned status %s" % result.get("mes_status")
            audit.fail_transaction(ctx, status_code, error_code, message)
            audit.log_step(ctx, constants.STEP_FAILED, "FAILED", result, error_code, message)
            logger.error(ctx, constants.STEP_FAILED, "FAILED", message, {"error_code": error_code})
        return result
    except InterfaceError, ex:
        if ctx is None:
            raise
        ctx.get("errors", []).append({"error_code": ex.error_code, "error_message": ex.message})
        if audit_started:
            audit.log_step(ctx, constants.STEP_FAILED, "FAILED", ex.details, ex.error_code, ex.message)
            audit.fail_transaction(ctx, ex.status_code, ex.error_code, ex.message)
        logger.error(ctx, constants.STEP_FAILED, "FAILED", ex.message,
                     {"error_code": ex.error_code, "details": ex.details})
        return {"success": False, "skipped": False, "transaction_id": ctx.get("transaction_id"),
                "error_code": ex.error_code, "error_message": ex.message, "details": ex.details}
    except Exception, ex:
        if ctx is not None:
            if audit_started:
                audit.log_step(ctx, constants.STEP_FAILED, "FAILED", None, "SYS-0001", str(ex))
                audit.fail_transaction(ctx, constants.STATUS_SCADA_INTERNAL_ERROR, "SYS-0001", str(ex))
            logger.error(ctx, constants.STEP_FAILED, "FAILED", str(ex), {"error_code": "SYS-0001"})
            return {"success": False, "skipped": False,
                    "transaction_id": ctx.get("transaction_id"),
                    "error_code": "SYS-0001", "error_message": str(ex)}
        raise
    finally:
        _SCHEDULE_OWNER[0] = None
        _SCHEDULE_ACTIVE.set(False)

# -----------------------------------------------------------------------------
# Function    : handle_ag_call
# Description : Handles handle ag call logic for this module.
# -----------------------------------------------------------------------------
def handle_ag_call(interface_name, handshake_tag_path, handshake_value):
    cfg = config.get_interface_config(interface_name)
    handler = _load_handler(cfg.get("handler_module"))
    numeric_handshake = int(handshake_value)

    # Idle and already-completed states are not transactions.
    if numeric_handshake in (0, 2):
        return None

    try:
        route = ag_call_routing.resolve(interface_name, handshake_tag_path)
    except RoutingError, ex:
        route_ctx = context.create_context(
            interface_name,
            cfg.get("direction", "E2S_TO_S2M"),
            equipment_id=None,
            transaction_prefix=cfg.get("transaction_prefix")
        )
        route_ctx["trigger_tag_path"] = handshake_tag_path
        route_ctx["route_error"] = ex.error_code
        logger.error(route_ctx, constants.STEP_FAILED, "FAILED", ex.message, {
            "error_code": ex.error_code,
            "handshake_value": numeric_handshake
        })
        try:
            audit.start_transaction(route_ctx, cfg)
            audit.fail_transaction(route_ctx, ex.status_code, ex.error_code, ex.message)
        except Exception, audit_ex:
            logger.error(route_ctx, constants.STEP_FAILED, "FAILED", str(audit_ex), {
                "error_code": "AUDIT-0001"
            })
        raise

    request_config = dict(cfg)
    request_config.update(route)
    request_config["route_equipment_id"] = route.get("equipment_id")
    if interface_name == "S2M.MaterialInfo":
        request_config["equipment"] = route.get("equipment_id")
        request_config["feeding_location"] = route.get("equipment_id")

    ctx = context.create_context(
        interface_name,
        request_config.get("direction", "E2S_TO_S2M"),
        equipment_id=route.get("equipment_id"),
        transaction_prefix=request_config.get("transaction_prefix")
    )
    ctx["route_equipment_id"] = route.get("equipment_id")
    ctx["trigger_tag_path"] = route.get("trigger_tag_path")
    ctx["provider_prefix"] = route.get("provider_prefix")
    ctx["source_system"] = cfg.get("source_system", "SCADA")
    ctx["target_system"] = cfg.get("target_system", "MES")
    ctx["event_timestamp"] = message_header.utc_timestamp()
    ctx["request_time"] = message_header.parse_event_timestamp(
        ctx.get("event_timestamp")
    )
    logger.diagnostic(ctx, request_config, constants.STEP_REQUEST_RECEIVED, "AG call router processing started", {
        "handshake_tag_path": handshake_tag_path,
        "handshake_value": numeric_handshake,
        "route_equipment_id": route.get("equipment_id"),
        "ag_tag_base_path": route.get("ag_tag_base_path")
    })

    try:
        audit.start_transaction(ctx, request_config)

        # Handlers with richer PLC handshake contracts can complete a non-request
        # state without reading request tags or calling MES.
        if numeric_handshake != 1 and hasattr(handler, "handle_ag_handshake"):
            result = handler.handle_ag_handshake(ctx, request_config, numeric_handshake)
            audit.save_payload(ctx, "RESPONSE", result, request_config.get("payload_logging_mode", "HASH_ONLY"))
            audit.complete_transaction(ctx, constants.STATUS_SUCCESS)
            audit.log_step(ctx, constants.STEP_COMPLETED, "SUCCESS")
            logger.diagnostic(ctx, request_config, constants.STEP_COMPLETED, "AG call router processing completed")
            return result

        request_payload = handler.read_ag_request(ctx, request_config, handshake_tag_path, handshake_value)
        audit.log_step(ctx, constants.STEP_AG_CALL_READ, "SUCCESS")
        audit.save_payload(ctx, "REQUEST", request_payload, request_config.get("payload_logging_mode", "HASH_ONLY"))
        validation.validate_payload(handler.SCHEMA, request_payload)
        audit.log_step(ctx, constants.STEP_PAYLOAD_VALIDATION, "SUCCESS")
        handler.validate_business_rules(ctx, request_payload, request_config)
        audit.update_transaction_context(ctx)
        audit.log_step(ctx, constants.STEP_BUSINESS_VALIDATION, "SUCCESS")
        result = handler.process(ctx, request_payload, request_config)
        handler.write_ag_response(ctx, request_config, result)
        audit.log_step(ctx, constants.STEP_AG_CALL_WRITE, "SUCCESS")
        audit.save_payload(ctx, "RESPONSE", result, request_config.get("payload_logging_mode", "HASH_ONLY"))
        result_success = True
        if hasattr(handler, "is_success_result"):
            result_success = handler.is_success_result(result)
        delivery_outcome = result.get("DeliveryOutcome") if isinstance(result, dict) else None
        if delivery_outcome == "QUEUED":
            # The queue transition owns transaction state; do not overwrite it
            # with COMPLETED after the independent PLC acknowledgement succeeds.
            logger.diagnostic(ctx, request_config, "STORE_FORWARD_QUEUED",
                              "AG call accepted and queued for MES delivery")
        elif result_success:
            audit.complete_transaction(ctx, constants.STATUS_SUCCESS)
            audit.log_step(ctx, constants.STEP_COMPLETED, "SUCCESS")
            logger.diagnostic(ctx, request_config, constants.STEP_COMPLETED, "AG call router processing completed")
        else:
            audit.fail_transaction(
                ctx,
                constants.STATUS_MES_ERROR,
                "MES-HTTP-%s" % result.get("StatusCode"),
                "MES returned HTTP status %s" % result.get("StatusCode")
            )
            audit.log_step(
                ctx,
                constants.STEP_FAILED,
                "FAILED",
                {"status_code": result.get("StatusCode")},
                "MES-HTTP-%s" % result.get("StatusCode"),
                "MES returned a non-200 status"
            )
        return result
    except Exception, ex:
        error_code = getattr(ex, "error_code", "SYS-0001")
        status_code = getattr(ex, "status_code", constants.STATUS_SCADA_INTERNAL_ERROR)
        error_details = getattr(ex, "details", {}) or {}
        # ValidationError carries an errors array with the exact field paths.
        # Keep it in both operational logs and the transaction step audit.
        logger.error(ctx, constants.STEP_FAILED, "FAILED", str(ex), {
            "error_code": error_code,
            "validation_errors": error_details.get("errors", []),
            "details": error_details
        })
        try:
            audit.log_step(ctx, constants.STEP_FAILED, "FAILED", error_details,
                           error_code, str(ex))
        except Exception, audit_ex:
            logger.error(ctx, constants.STEP_FAILED, "FAILED", str(audit_ex), {
                "error_code": "AUDIT-0001",
                "original_error_code": error_code
            })
        try:
            handler.write_ag_failure(ctx, request_config, str(ex))
        except Exception, write_ex:
            logger.error(ctx, constants.STEP_AG_CALL_WRITE, "FAILED", str(write_ex))
        audit.fail_transaction(ctx, status_code, error_code, str(ex))
        raise


_STORE_FORWARD_ACTIVE = AtomicBoolean(False)


# -----------------------------------------------------------------------------
# Function    : _sf_audit
# Description : Records queue lifecycle evidence without reversing committed delivery state.
# -----------------------------------------------------------------------------
def _sf_audit(ctx, state, row=None, extra=None):
    # Audit failure must never reverse a committed queue transition.
    details = {}
    if row is not None:
        for key in ("id", "persistent_retry_count", "next_retry_time", "expires_at",
                    "last_http_status", "last_error_code", "last_error_message"):
            details[key] = row[key]
    if extra:
        details.update(extra)
    try:
        audit.record_store_forward(ctx, state, details)
    except (Exception, JavaException):
        try:
            logger.error(ctx, "STORE_FORWARD_AUDIT_FAILED", "FAILED",
                         "Queue state committed; audit update failed", details)
        except (Exception, JavaException):
            pass
        try:
            system_logger = __import__("system").util.getLogger("SCADA.StoreForward")
            system_logger.error("STORE_FORWARD_AUDIT_FAILED: Queue state committed; audit update failed for "
                                + str(ctx.get("transaction_id")))
        except (Exception, JavaException):
            pass
    try:
        step = {"PENDING": "ENQUEUE", "IN_PROGRESS": "RETRY"}.get(state, state)
        if state == "PENDING" and details.get("persistent_retry_count", 0) > 0:
            step = "RETRY"
        log_method = logger.error if state in ("EXPIRED", "FAILED") else logger.info
        log_method(ctx, "STORE_FORWARD_" + step, state,
                   "Store-and-Forward delivery state", details)
    except (Exception, JavaException):
        pass


# -----------------------------------------------------------------------------
# Function    : _sf_diagnostic
# Description : Emits safe metadata only when project diagnostics are explicitly enabled.
# -----------------------------------------------------------------------------
def _sf_diagnostic(ctx, cfg, step, message, details=None):
    # Optional diagnostics must not change delivery or expose request payloads.
    try:
        if logger.debug_enabled(cfg):
            logger.diagnostic(ctx, cfg, step, message, details or {})
    except (Exception, JavaException):
        pass


# -----------------------------------------------------------------------------
# Function    : _sf_event
# Description : Records dispatcher evidence without creating a business transaction.
# -----------------------------------------------------------------------------
def _sf_event(ctx, step, status, details=None, error_code=None):
    # Operational events are best effort even during an audit/database outage.
    try:
        audit.log_store_forward_event(ctx, step, status, details, error_code)
    except (Exception, JavaException):
        try:
            logger.error(ctx, "STORE_FORWARD_AUDIT_FAILED", "FAILED",
                         "Could not persist Store-and-Forward operational event",
                         {"event_step": step})
        except (Exception, JavaException):
            pass
    try:
        method = logger.error if status == "FAILED" else logger.info
        method(ctx, step, status, "Store-and-Forward operational event", details)
    except (Exception, JavaException):
        pass


# -----------------------------------------------------------------------------
# Function    : submit_async_mes_request
# Description : Runs immediate retries and persists eligible exhausted requests.
# -----------------------------------------------------------------------------
def submit_async_mes_request(ctx, cfg, business_payload, prepared_envelope=None):
    """Future handler API. Caller owns the transaction audit and acknowledgement."""
    from scada_interface import rest_client, retry, store_and_forward
    from scada_interface.errors import StoreForwardError
    policy = config.get_store_forward_config(cfg)
    if (cfg.get("delivery_mode") != "ASYNCHRONOUS"
            or cfg.get("idempotent") is not True
            or cfg.get("enabled", True) is not True
            or cfg.get("target_type") != constants.TARGET_MES_REST):
        raise ValueError("Explicit asynchronous idempotent MES delivery is required")
    envelope = prepared_envelope
    if envelope is None:
        envelope = message_header.wrap_outbound(ctx, cfg, business_payload)
    _sf_diagnostic(ctx, cfg, "STORE_FORWARD_SUBMIT", "Prepared asynchronous MES submission",
                   {"store_forward_enabled": policy.get("enabled"),
                    "maximum_attempts": max(0, int(cfg.get("retry_count", 0))) + 1})
    # Freeze the final envelope; retries must not regenerate the event timestamp.
    # -----------------------------------------------------------------------------
    # Function    : send
    # Description : Sends the same prepared MES envelope on each immediate attempt.
    # -----------------------------------------------------------------------------
    def send():
        return rest_client.call_mes_prepared(ctx, cfg, envelope)
    def on_retry(operation, reason_type, reason, attempt, remaining, delay_ms):
        _sf_diagnostic(ctx, cfg, "STORE_FORWARD_IMMEDIATE_RETRY", "Retrying MES before persistence",
                       {"retry_number": attempt, "remaining_retries": remaining,
                        "retry_delay_ms": delay_ms,
                        "mes_http_status": getattr(reason, "mes_http_status", None)})
    try:
        result = retry.execute(ctx, "ASYNC_MES", send,
                               max(0, int(cfg.get("retry_count", 0))),
                               max(0, int(cfg.get("retry_backoff_ms", 1000))),
                               _is_delivery_retryable, on_retry=on_retry)
    except (Exception, JavaException):
        import sys
        failure = sys.exc_info()[1]
        if policy.get("enabled") is not True or not _is_delivery_retryable(failure):
            raise
        try:
            row = store_and_forward.enqueue(ctx, cfg, envelope, failure)
        except (Exception, JavaException):
            try:
                audit.fail_transaction(ctx, constants.STATUS_STORE_FORWARD_QUEUE_FAILED,
                                       "DB-SF-001", "Failed to persist MES request")
            except (Exception, JavaException):
                pass
            logger.error(ctx, "STORE_FORWARD_QUEUE_FAILED", "FAILED",
                         "Failed to persist MES request; request is not safely queued")
            raise
        state = row["queue_status"]
        if state in ("FAILED", "EXPIRED"):
            raise StoreForwardError("Existing transaction has terminal queue status " + state)
        _sf_audit(ctx, state, row)
        _sf_diagnostic(ctx, cfg, "STORE_FORWARD_STORED", "Durable MES request recorded",
                       {"queue_id": row["id"], "queue_status": state})
        return {"outcome": "DELIVERED" if state == "DELIVERED" else "QUEUED",
                "transaction_id": ctx["transaction_id"], "queue_id": row["id"],
                "mes_result": {
                    "status_code": getattr(failure, "mes_http_status", None),
                    "response_body": getattr(failure, "response_body", None)
                }}
    return {"outcome": "DELIVERED", "transaction_id": ctx["transaction_id"],
            "mes_result": result}


# -----------------------------------------------------------------------------
# Function    : handle_store_and_forward
# Description : Dispatches bounded due work with ownership, audit and diagnostics.
# -----------------------------------------------------------------------------
def handle_store_and_forward():
    """Bounded dispatcher, one claim immediately before each delivery cycle."""
    import sys
    import system
    import time
    from java.util import UUID
    from scada_interface import oauth, rest_client, store_and_forward
    from scada_interface.errors import MesDeliveryError, StoreForwardError
    cycle_ctx = {"transaction_id": "SF-CYCLE-" + str(UUID.randomUUID()),
                 "interface_name": "StoreForwardDispatcher", "direction": "INTERNAL",
                 "retry_count": 0}
    if not _STORE_FORWARD_ACTIVE.compareAndSet(False, True):
        _sf_event(cycle_ctx, "STORE_FORWARD_DISPATCH_SKIPPED", "SKIPPED")
        return {"skipped": True, "attempted": 0}
    attempted = 0
    cycle_started = time.time()
    try:
        _sf_event(cycle_ctx, "STORE_FORWARD_DISPATCH_STARTED", "IN_PROGRESS")
        _sf_diagnostic(cycle_ctx, config.STORE_FORWARD_DISPATCHER,
                       "STORE_FORWARD_DISPATCH_CONFIG", "Dispatcher settings",
                       dict(config.STORE_FORWARD_DISPATCHER))
        for recovered in store_and_forward.release_stale_locks():
            _sf_event({"transaction_id": recovered["transaction_id"],
                       "interface_name": recovered["interface_name"]},
                      "STORE_FORWARD_STALE_LOCK", "RECOVERED", {"queue_id": recovered["id"]})
        for row in store_and_forward.expire_due_requests():
            _sf_audit({"transaction_id": row["transaction_id"],
                       "interface_name": row["interface_name"]}, "EXPIRED", row)
        configs = {}
        lease = max(120, int(config.STORE_FORWARD_DISPATCHER["lock_timeout_seconds"]))
        for name, cfg in config.STATIC_CONFIG.items():
            if not cfg.get("enabled", True) or not (cfg.get("store_and_forward") or {}).get("enabled"):
                continue
            try:
                if store_and_forward.is_enabled(cfg):
                    if name != cfg.get("interface_name"):
                        raise ValueError("Interface configuration key does not match its name")
                    # Two token acquisitions + two MES calls + scheduling margin.
                    bound = 2 * int(cfg.get("timeout_ms", 20000))
                    if cfg.get("outbound_auth_required", True) is True:
                        bound += 2 * int(oauth.TOKEN_TIMEOUT)
                    lease = max(lease, int((bound + 999) // 1000) + 60)
                    configs[name] = dict(cfg)
            except (Exception, JavaException):
                _sf_event(cycle_ctx, "STORE_FORWARD_CONFIG_FAILED", "FAILED",
                          {"affected_interface": name}, "CFG-SF-001")
        for unused in range(max(0, min(50, int(config.STORE_FORWARD_DISPATCHER["batch_size"])))):
            worker_id = str(UUID.randomUUID())
            rows = store_and_forward.claim_due_requests(1, worker_id, sorted(configs), lease)
            if not rows:
                break
            row = rows[0]
            attempted += 1
            ctx = {"transaction_id": row["transaction_id"], "interface_name": row["interface_name"]}
            failure = None
            result = None
            delivery_started = time.time()
            _sf_diagnostic(ctx, configs[row["interface_name"]], "STORE_FORWARD_CLAIM",
                           "Claimed due MES delivery", {"queue_id": row["id"],
                           "worker_id": worker_id, "lease_seconds": lease,
                           "persistent_retry_count": row["persistent_retry_count"]})
            try:
                ctx = context.from_persisted_transaction(row)
                envelope = system.util.jsonDecode(row["request_payload"])
                inputs = envelope["Inputs"]
                request_body = inputs["RequestJSON"]
                header = request_body["MessageHeader"]
                if header["TransactionId"] != row["transaction_id"]:
                    raise ValueError("Persisted message header identity mismatch")
                # -----------------------------------------------------------------------------
                # Function    : before_send
                # Description : Prevents HTTP sends after expiry or loss of SQL claim ownership.
                # -----------------------------------------------------------------------------
                def before_send():
                    if not store_and_forward.can_send(row["id"], worker_id):
                        raise MesDeliveryError("Queue deadline or ownership lost", False)
                _sf_audit(ctx, "IN_PROGRESS", row)
                result = rest_client.call_mes_prepared(ctx, configs[row["interface_name"]],
                                                       envelope, before_send=before_send)
            except (Exception, JavaException):
                failure = sys.exc_info()[1]
            if isinstance(failure, StoreForwardError):
                # A DB failure in the pre-send ownership check is infrastructure
                # failure, not permanent business rejection. Retain the claim.
                raise failure
            # Keep persistence writes outside the delivery catch: a DB update failure
            # leaves the claim for recovery and must not cause an immediate second send.
            if result is not None:
                changed = store_and_forward.mark_delivered(row["id"], worker_id, result["status_code"])
            elif not store_and_forward.can_send(row["id"], worker_id):
                changed = store_and_forward.mark_expired(row["id"], worker_id)
            elif _is_delivery_retryable(failure):
                changed = store_and_forward.schedule_next_retry(row["id"], worker_id, failure)
            else:
                safe_failure = MesDeliveryError("Persistent delivery failed (%s)" % failure.__class__.__name__)
                if isinstance(failure, MesDeliveryError):
                    safe_failure = failure
                changed = store_and_forward.mark_failed(row["id"], worker_id, safe_failure)
            if changed:
                _sf_audit(ctx, changed[0]["queue_status"], changed[0],
                          {"delivery_duration_ms": max(0, int((time.time() - delivery_started) * 1000))})
            else:
                _sf_event(ctx, "STORE_FORWARD_OWNERSHIP_LOST", "FAILED",
                          {"queue_id": row["id"]}, "DB-SF-002")
        _sf_event(cycle_ctx, "STORE_FORWARD_DISPATCH_COMPLETED", "SUCCESS",
                  {"attempted": attempted,
                   "duration_ms": max(0, int((time.time() - cycle_started) * 1000))})
        return {"skipped": False, "attempted": attempted}
    except (Exception, JavaException):
        _sf_event(cycle_ctx, "STORE_FORWARD_DISPATCH_FAILED", "FAILED",
                  {"attempted": attempted,
                   "duration_ms": max(0, int((time.time() - cycle_started) * 1000))}, "DB-SF-003")
        raise
    finally:
        _STORE_FORWARD_ACTIVE.set(False)