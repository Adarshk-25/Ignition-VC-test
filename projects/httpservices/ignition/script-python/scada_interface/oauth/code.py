###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : oauth.py
# Module         : OAuth Authentication
#
# Description:
# Validates inbound bearer tokens and generates cached MES OAuth access tokens
# for outbound SCADA-to-MES REST calls using client credentials.
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

import time
import urllib

import system
import system.net

from scada_interface import constants
from scada_interface import environment
from scada_interface.errors import AuthError


TOKEN_TIMEOUT = 30000
TOKEN_EXPIRY_BUFFER_SECONDS = 60

_token_cache = {
    "access_token": None,
    "expires_at": 0
}


# -----------------------------------------------------------------------------
# Function    : _header
# Description : Handles header logic for this module.
# -----------------------------------------------------------------------------
def _header(request, name):
    headers = getattr(request, "headers", {}) or {}
    return headers.get(name) or headers.get(name.lower())


# -----------------------------------------------------------------------------
# Function    : _response_json
# Description : Handles response json logic for this module.
# -----------------------------------------------------------------------------
def _response_json(response):
    json_value = getattr(response, "json", None)
    # Ignition response JSON may appear as either a property or callable accessor.
    if callable(json_value):
        return json_value()
    if json_value is not None:
        return json_value
    raise Exception("OAuth response did not include JSON content")


# -----------------------------------------------------------------------------
# Function    : validate_inbound_request
# Description : Handles validate inbound request logic for this module.
# -----------------------------------------------------------------------------
def validate_inbound_request(request, ctx, config):
    if not config.get("auth_required"):
        return True

    auth = _header(request, "Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise AuthError(constants.STATUS_AUTH_FAILED, "AUTH-0001", "Missing or invalid Authorization header", 401)

    token = auth.replace("Bearer ", "", 1).strip()
    if not validate_bearer_token(token):
        raise AuthError(constants.STATUS_AUTH_FAILED, "AUTH-0002", "Bearer token validation failed", 401)

    return True


# -----------------------------------------------------------------------------
# Function    : validate_bearer_token
# Description : Handles validate bearer token logic for this module.
# -----------------------------------------------------------------------------
def validate_bearer_token(token):
    # Replace with OIDC introspection or JWKS validation.
    return token is not None and len(token) > 20


# -----------------------------------------------------------------------------
# Function    : get_mes_access_token
# Description : Handles get mes access token logic for this module.
# -----------------------------------------------------------------------------
def get_mes_access_token(force_refresh=False):
    now = int(time.time())

    # Refresh before real expiry so in-flight MES calls do not race token expiration.
    if (not force_refresh and
            _token_cache.get("access_token") is not None and
            now < int(_token_cache.get("expires_at", 0))):
        return _token_cache.get("access_token")

    token_url = environment.get_path("mes", "token_url")
    client_id = environment.get_path("mes", "client_id")
    client_secret = environment.get_path("mes", "client_secret")

    form_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": environment.get_path("mes", "token_scope"),
        "state": environment.get_path("mes", "token_state"),
        "grant_type": environment.get_path("mes", "token_grant_type")
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        client = system.net.httpClient(timeout=TOKEN_TIMEOUT)
        # OAuth token endpoint expects application/x-www-form-urlencoded body.
        response = client.post(
            url=token_url,
            headers=headers,
            data=urllib.urlencode(form_data)
        )

        status_code = response.getStatusCode()
        if status_code < 200 or status_code >= 300:
            raise Exception("Token API failed. Status=%s Response=%s" % (status_code, response.getText()))

        token_response = _response_json(response)
        access_token = token_response.get("access_token")
        if not access_token:
            raise Exception("access_token missing in OAuth response")

        expires_in = int(token_response.get("expires_in", 3600))
        cache_seconds = max(0, expires_in - TOKEN_EXPIRY_BUFFER_SECONDS)
        # Cache is process-local to the Ignition scripting runtime.
        _token_cache["access_token"] = access_token
        _token_cache["expires_at"] = now + cache_seconds

        return access_token

    except AuthError:
        raise
    except Exception, ex:
        raise AuthError(
            constants.STATUS_AUTH_FAILED,
            "AUTH-0101",
            "MES OAuth token generation failed: %s" % str(ex),
            502
        )