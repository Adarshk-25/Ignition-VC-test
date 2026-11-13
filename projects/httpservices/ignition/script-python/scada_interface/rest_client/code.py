###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : rest_client.py
# Module         : Common MES REST Client
#
# Description:
# Sends outbound MES REST requests with bearer token injection, timeout handling,
# one-time token refresh on HTTP 401 and common MES error wrapping.
# Prepared-envelope delivery preserves headers and centrally classifies availability.
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
# 3     | 1.2     | 09-Sep-2026 | Hari   | Added opt-in per-interface HTTP delivery policy
# -----------------------------------------------------------------------------
###############################################################################

import system
import system.net
import system.util
from scada_interface import constants, logger, message_header, oauth
from scada_interface.errors import MesError
try:
    from java.lang import Exception as JavaException
except ImportError:
    JavaException = Exception


# -----------------------------------------------------------------------------
# Function    : _response_json
# Description : Handles response json logic for this module.
# -----------------------------------------------------------------------------
def _response_json(response):
    json_value = getattr(response, "json", None)
    # Support both Ignition response JSON forms and a text fallback for compatibility.
    if callable(json_value):
        return json_value()
    if json_value is not None:
        return json_value
    return system.util.jsonDecode(response.getText())


# -----------------------------------------------------------------------------
# Function    : _post_json
# Description : Handles post json logic for this module.
# -----------------------------------------------------------------------------
def _post_json(client, url, headers, payload):
    # Keep MES POST creation in one helper so initial call and 401 retry stay identical.
    return client.post(
        url=url,
        headers=headers,
        data=system.util.jsonEncode(payload)
    )


# -----------------------------------------------------------------------------
# Function    : _debug_enabled
# Description : Enables verbose MES transport logging only for an explicit True.
# -----------------------------------------------------------------------------
def _debug_enabled(config):
    return logger.debug_enabled(config)


# -----------------------------------------------------------------------------
# Function    : _response_text
# Description : Reads the raw MES response body for Gateway diagnostics.
# -----------------------------------------------------------------------------
def _response_text(response):
    try:
        return response.getText()
    except Exception:
        json_value = getattr(response, "json", None)
        if callable(json_value):
            json_value = json_value()
        if json_value is not None:
            return system.util.jsonEncode(json_value)
        return ""


# -----------------------------------------------------------------------------
# Function    : _post_json_with_debug
# Description : Logs the exact MES request and response when debug is enabled.
# -----------------------------------------------------------------------------
def _post_json_with_debug(ctx, config, client, url, headers, payload):
    if _debug_enabled(config):
        logger.diagnostic(
            ctx,
            config,
            "MES_REQUEST",
            "Sending MES request payload",
            {"mes_payload": payload}
        )

    response = _post_json(client, url, headers, payload)

    if _debug_enabled(config) and response is not None:
        logger.diagnostic(
            ctx,
            config,
            "MES_RESPONSE",
            "Received MES response",
            {
                "mes_http_status": int(response.getStatusCode()),
                "mes_response_body": _response_text(response)
            }
        )
    return response


# -----------------------------------------------------------------------------
# Function    : call_mes_api
# Description : Handles call mes api logic for this module.
# -----------------------------------------------------------------------------
def call_mes_api(ctx, config, payload):
    auth_required = config.get("outbound_auth_required", True) is True
    token = oauth.get_mes_access_token() if auth_required else None
    url = config.get("mes_url")
    timeout_ms = int(config.get("timeout_ms", 20000))
    client = system.net.httpClient(timeout=timeout_ms)

    # Propagate SCADA tracking ids to MES for cross-system troubleshooting.
    headers = {
        "Content-Type": "application/json",
        "X-Correlation-ID": ctx.get("correlation_id"),
        "X-Transaction-ID": ctx.get("transaction_id")
    }

    if auth_required:
        headers["Authorization"] = "Bearer %s" % token
    mes_payload = message_header.wrap_outbound(ctx, config, payload)

    try:
        response = _post_json_with_debug(ctx, config, client, url, headers, mes_payload)

        # Refresh the cached OAuth token once when MES reports an expired token.
        if auth_required and response.getStatusCode() == 401:
            token = oauth.get_mes_access_token(force_refresh=True)
            headers["Authorization"] = "Bearer %s" % token
            response = _post_json_with_debug(ctx, config, client, url, headers, mes_payload)

        status_code = response.getStatusCode()
        if status_code < 200 or status_code >= 300:
            raise Exception("MES API failed. Status=%s Response=%s" % (status_code, response.getText()))

        return _response_json(response)
    except Exception, ex:
        raise MesError(constants.STATUS_MES_ERROR, "MES-0001", str(ex), 502)


# -----------------------------------------------------------------------------
# Function    : call_mes_api_status
# Description : Calls MES and returns the raw HTTP status and response body.
# -----------------------------------------------------------------------------
def call_mes_api_status(ctx, config, payload):
    """POST to MES and return the HTTP status/body without requiring JSON."""
    auth_required = config.get("outbound_auth_required", True) is True
    token = oauth.get_mes_access_token() if auth_required else None
    client = system.net.httpClient(timeout=int(config.get("timeout_ms", 20000)))
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Correlation-ID": ctx.get("correlation_id"),
        "X-Transaction-ID": ctx.get("transaction_id")
    }
    if auth_required:
        headers["Authorization"] = "Bearer %s" % token
    mes_payload = message_header.wrap_outbound(ctx, config, payload)
    try:
        response = _post_json_with_debug(
            ctx, config, client, config.get("mes_url"), headers, mes_payload
        )
        if auth_required and response.getStatusCode() == 401:
            token = oauth.get_mes_access_token(force_refresh=True)
            headers["Authorization"] = "Bearer %s" % token
            response = _post_json_with_debug(
                ctx, config, client, config.get("mes_url"), headers, mes_payload
            )
        if response is None:
            raise Exception("MES HTTP client returned no response")
        body = ""
        try:
            body = _response_text(response)
        except Exception:
            body = ""
        return {
            "status_code": int(response.getStatusCode()),
            "response_body": body
        }
    except Exception, ex:
        raise MesError(constants.STATUS_MES_ERROR, "MES-0001", str(ex), 502)


# -----------------------------------------------------------------------------
# Function    : is_delivery_retryable
# Description : Recognizes centrally classified MES availability failures.
# -----------------------------------------------------------------------------
def is_delivery_retryable(failure):
    from scada_interface.errors import MesDeliveryError
    return isinstance(failure, MesDeliveryError) and failure.eligible is True


# -----------------------------------------------------------------------------
# Function    : _http_delivery_policy
# Description : Applies an opt-in status policy while preserving shared defaults.
# -----------------------------------------------------------------------------
def _http_delivery_policy(config, status):
    success_statuses = config.get("mes_success_http_statuses")
    if success_statuses is None:
        successful = 200 <= status < 300
    else:
        successful = status in [int(value) for value in success_statuses]
    if successful:
        return True, False
    if config.get("retry_all_http_failures") is True:
        return False, True
    return False, status in (500, 502, 503, 504)


# -----------------------------------------------------------------------------
# Function    : _availability_exception
# Description : Inspects exception types and causes for transport availability failures.
# -----------------------------------------------------------------------------
def _availability_exception(ex):
    # Inspect types/causes, never exception message text or all generic failures.
    names = ("ConnectException", "SocketTimeoutException", "HttpTimeoutException",
             "UnknownHostException", "NoRouteToHostException", "SocketException",
             "TimeoutError", "ConnectionError", "ConnectionResetError",
             "ConnectionRefusedError")
    for unused in range(8):
        if ex.__class__.__name__ in names:
            return True
        cause = getattr(ex, "getCause", lambda: None)()
        if cause is None or cause is ex:
            break
        ex = cause
    return False


# -----------------------------------------------------------------------------
# Function    : call_mes_prepared
# Description : Sends a final MES envelope without regenerating its message header.
# -----------------------------------------------------------------------------
def call_mes_prepared(ctx, config, envelope, before_send=None):
    """Send a final envelope; return the existing raw status/body result shape."""
    import sys
    from scada_interface.errors import MesDeliveryError
    auth_required = config.get("outbound_auth_required", True) is True
    # OAuth failures are not MES delivery failures and must not be queued.
    token = oauth.get_mes_access_token() if auth_required else None
    client = system.net.httpClient(timeout=int(config.get("timeout_ms", 20000)))
    headers = {"Content-Type": "application/json", "Accept": "application/json",
               "X-Correlation-ID": ctx.get("correlation_id"),
               "X-Transaction-ID": ctx.get("transaction_id")}
    for attempt in range(2):
        if auth_required:
            headers["Authorization"] = "Bearer %s" % token
        if before_send is not None:
            before_send()
        try:
            response = _post_json_with_debug(ctx, config, client,
                                             config.get("mes_url"), headers, envelope)
        except (Exception, JavaException):
            ex = sys.exc_info()[1]
            raise MesDeliveryError("MES transport failed (%s)" % ex.__class__.__name__,
                                   _availability_exception(ex))
        if response is None:
            raise MesDeliveryError("MES returned no response", True)
        status = int(response.getStatusCode())
        if status == 401 and auth_required and attempt == 0:
            token = oauth.get_mes_access_token(force_refresh=True)
            continue
        result = {"status_code": status, "response_body": _response_text(response)}
        accepted, retryable = _http_delivery_policy(config, status)
        if not accepted:
            raise MesDeliveryError("MES HTTP status %s" % status,
                                   retryable, status, result["response_body"])
        # Future interfaces with body-level rejection must supply a pure validator.
        validator = config.get("mes_acceptance_validator")
        if validator is not None and validator(result) is not True:
            raise MesDeliveryError("MES business response rejected", False, status)
        return result