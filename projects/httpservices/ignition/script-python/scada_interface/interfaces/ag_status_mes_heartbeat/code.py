###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : mes_heartbeat.py
# Interface      : S2M.MESHeartbeat
# Module         : Scheduled MES Heartbeat Handler
#
# Description:
# Sends the scheduled MES heartbeat, maps the returned heartbeat status to MES
# availability, and distributes that state to every configured active-zone PLC tag.
###############################################################################

import sys
import system
import system.util
from scada_interface import audit, constants, environment, logger
from scada_interface import metrics, opcua_client, rest_client, retry
from scada_interface.errors import InterfaceError, MesError, ValidationError


def _debug(ctx, config, step, message, extra=None):
    """Emit diagnostics only when debug_enabled is the Boolean True."""
    logger.diagnostic(ctx, config, step, message, extra)


def build_request(ctx, config):
    request = {"MessageType": "HeartBeatRequest"}
    _debug(ctx, config, "MES_HEARTBEAT_REQUEST_BUILD",
           "Built MES heartbeat business request", {"message_type": request["MessageType"]})
    return request


def _configuration_error(code, message):
    return ValidationError("CONFIGURATION_ERROR", code, message, 500)


def build_tag_paths(config):
    provider = str(environment.get_path("tag_provider") or "").strip()
    relative = str(config.get("relative_tag_path") or "").strip()
    if not provider or "[" in provider or "]" in provider or "/" in provider:
        raise _configuration_error("CFG-HB-002", "Heartbeat tag provider is invalid")
    if (not relative or relative.startswith("/") or relative.endswith("/")
            or ".." in relative or "[" in relative or "]" in relative):
        raise _configuration_error("CFG-HB-002", "Heartbeat relative tag path is invalid")
    try:
        equipment_ids = environment.heartbeat_equipment_ids()
    except Exception:
        raise _configuration_error("CFG-HB-001", str(sys.exc_info()[1]))
    paths = []
    for equipment_id in equipment_ids:
        paths.append("[%s]%s/%s" % (provider, equipment_id, relative))
    return equipment_ids, paths


def validate_business_rules(ctx, payload, config):
    if not config.get("mes_url") or not config.get("mes_interface_name"):
        raise _configuration_error("CFG-HB-002", "Heartbeat MES configuration is incomplete")
    equipment_ids, paths = build_tag_paths(config)
    ctx["business_reference"] = str(environment.get_path("zone"))
    ctx["active_zone"] = ctx.get("business_reference")
    ctx["configured_plc_count"] = len(equipment_ids)
    ctx["heartbeat_equipment_ids"] = equipment_ids
    ctx["heartbeat_tag_paths"] = paths
    _debug(ctx, config, "MES_HEARTBEAT_CONFIGURATION",
           "Resolved active-zone heartbeat targets", {
               "active_zone": ctx.get("active_zone"),
               "configured_plc_count": len(equipment_ids),
               "tag_paths": paths
           })
    return True


def write_mes_running(ctx, config, value):
    equipment_ids = ctx.get("heartbeat_equipment_ids")
    paths = ctx.get("heartbeat_tag_paths")
    if equipment_ids is None or paths is None:
        equipment_ids, paths = build_tag_paths(config)
    _debug(ctx, config, "MES_HEARTBEAT_PLC_WRITE",
           "Starting grouped MESRunning tag write", {
               "mes_running": bool(value), "configured_plc_count": len(paths),
               "tag_paths": paths
           })
    qualities = opcua_client.write_tag_values(paths, [bool(value)] * len(paths))
    if qualities is None:
        qualities = []
    results = []
    success_count = 0
    for index in range(len(paths)):
        quality = qualities[index] if index < len(qualities) else None
        try:
            success = quality is not None and quality.isGood()
        except Exception:
            success = False
        if success:
            success_count += 1
        result = {
            "equipment_id": equipment_ids[index], "tag_path": paths[index],
            "quality": str(quality) if quality is not None else "Missing",
            "success": success
        }
        results.append(result)
        if not success:
            logger.error(ctx, constants.STEP_PLC_TAG_WRITE, "FAILED",
                         "Heartbeat PLC tag write failed", result)
    summary = {
        "configured_plc_count": len(paths),
        "successful_write_count": success_count,
        "failed_write_count": len(paths) - success_count,
        "write_results": results
    }
    audit.log_step(ctx, constants.STEP_PLC_TAG_WRITE,
                   "SUCCESS" if success_count == len(paths) else "FAILED", summary)
    _debug(ctx, config, "MES_HEARTBEAT_PLC_WRITE",
           "Grouped MESRunning tag write completed", summary)
    return summary


def write_fail_safe(ctx, config, cause):
    _debug(ctx, config, "MES_HEARTBEAT_FAIL_SAFE",
           "Starting fail-safe false distribution", {"cause": unicode(cause)})
    try:
        summary = write_mes_running(ctx, config, False)
        summary["fail_safe_cause"] = unicode(cause)
        _debug(ctx, config, "MES_HEARTBEAT_FAIL_SAFE",
               "Fail-safe false distribution completed", summary)
        return summary
    except Exception:
        summary = {"fail_safe_cause": unicode(cause),
                   "fail_safe_error": unicode(sys.exc_info()[1])}
        logger.error(ctx, "MES_HEARTBEAT_FAIL_SAFE", "FAILED",
                     "Fail-safe false distribution failed", summary)
        return summary


def _record_metrics(ctx, summary, cycle_success):
    """Publish operational counters through the project's metrics hook."""
    labels = {"environment": environment.name(), "zone": ctx.get("active_zone"),
              "interface": "MESHeartbeat"}
    metrics.record(ctx, "mes_heartbeat_running", 1 if summary.get("mes_running") else 0, labels)
    metrics.record(ctx, "mes_heartbeat_configured_plcs", summary.get("configured_plc_count", 0), labels)
    metrics.record(ctx, "mes_heartbeat_write_successes", summary.get("successful_write_count", 0), labels)
    metrics.record(ctx, "mes_heartbeat_write_failures", summary.get("failed_write_count", 0), labels)
    metrics.record(ctx, "mes_heartbeat_retries", ctx.get("retry_count", 0), labels)
    metrics.record(ctx, "mes_heartbeat_cycle_success", 1 if cycle_success else 0, labels)


def extract_heartbeat_status(response_body):
    """Return HeartbeatResponse.Status, or an empty string for an invalid body."""
    try:
        outer = response_body
        if not isinstance(outer, dict):
            outer = system.util.jsonDecode(unicode(response_body or ""))
        outputs = outer.get("Outputs")
        if not isinstance(outputs, dict):
            return ""
        response_json = outputs.get("ResponseJSON")
        if not isinstance(response_json, dict):
            response_json = system.util.jsonDecode(unicode(response_json or ""))
        heartbeat = response_json.get("HeartbeatResponse")
        if not isinstance(heartbeat, dict):
            return ""
        return unicode(heartbeat.get("Status") or "").strip()
    except Exception:
        return ""


def process(ctx, payload, config):
    retry_count = max(0, int(config.get("retry_count", 0)))
    backoff_ms = max(0, int(config.get("retry_backoff_ms", 1000)))

    def call_mes():
        _debug(ctx, config, "MES_HEARTBEAT_MES_ATTEMPT",
               "Sending heartbeat request to MES", {
                   "mes_url": config.get("mes_url"),
                   "maximum_attempts": retry_count + 1
               })
        result = rest_client.call_mes_api_status(ctx, config, payload)
        status_code = int(result.get("status_code"))
        if status_code != 200:
            raise MesError(constants.STATUS_MES_ERROR, "MES-0001",
                           "MES heartbeat failed. HTTP status=%s" % status_code,
                           502, {"mes_http_status": status_code,
                                 "mes_response_body": result.get("response_body")})
        return result

    def on_retry(operation_name, reason_type, reason, retry_number, remaining, delay_ms):
        details = {"retry_number": retry_number, "remaining_retries": remaining,
                   "retry_delay_ms": delay_ms, "reason_type": reason_type,
                   "reason": unicode(reason)}
        audit.log_step(ctx, constants.STEP_RETRY, "RETRYING", details)
        logger.warn(ctx, constants.STEP_RETRY, "RETRYING", "Retrying MES heartbeat", details)

    try:
        result = retry.execute(ctx, "S2M.MESHeartbeat", call_mes, retry_count,
                               backoff_ms, lambda ex: isinstance(ex, MesError), None, on_retry)
        status_code = int(result.get("status_code"))
        heartbeat_status = extract_heartbeat_status(result.get("response_body"))
        running = heartbeat_status == "200"
        audit.log_step(ctx, constants.STEP_MES_REST_CALL, "SUCCESS",
                       {"http_status": status_code})
        audit.log_step(ctx, constants.STEP_MES_RESPONSE_VALIDATION,
                       "SUCCESS" if running else "FAILED",
                       {"validation_mode": "HEARTBEAT_STATUS_ONLY",
                        "http_status": status_code,
                        "heartbeat_status": heartbeat_status})
        _debug(ctx, config, "MES_HEARTBEAT_STATUS_MAPPING",
               "Mapped MES heartbeat response status to PLC state", {
                   "mes_http_status": status_code,
                   "heartbeat_status": heartbeat_status,
                   "mes_running": running
               })
        writes = write_mes_running(ctx, config, running)
        summary = {"mes_status": heartbeat_status,
                   "mes_http_status": status_code,
                   "mes_running": running, "active_zone": ctx.get("active_zone"),
                    "mes_response": result.get("response_body")}
        summary.update(writes)
        summary["success"] = running and summary.get("failed_write_count") == 0
        _record_metrics(ctx, summary, summary.get("success"))
        _debug(ctx, config, "MES_HEARTBEAT_COMPLETED",
               "MES heartbeat handler cycle completed", summary)
        return summary
    except InterfaceError, ex:
        fail_safe = write_fail_safe(ctx, config, ex.message)
        ex.details.update({"fail_safe_distribution": fail_safe})
        _record_metrics(ctx, fail_safe, False)
        raise
    except Exception:
        ex = sys.exc_info()[1]
        fail_safe = write_fail_safe(ctx, config, ex)
        wrapped = InterfaceError(constants.STATUS_SCADA_INTERNAL_ERROR, "SYS-0001",
                                 unicode(ex), 500, {"fail_safe_distribution": fail_safe})
        _record_metrics(ctx, fail_safe, False)
        raise wrapped