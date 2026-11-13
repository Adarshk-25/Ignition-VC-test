###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : mesclient_noauth.py
# Module         : Common MES REST Client
#
# Description:
# Common reusable REST client for SCADA -> MES and SCADA -> external system
# interfaces.
#
# This module provides:
#   1. OAuth Client Credential Token Generation
#   2. OAuth Token Caching
#   3. Automatic OAuth Token Refresh
#   4. Authenticated REST API POST using Bearer Token
#   5. Non-Authenticated REST API POST
#   6. JSON Request Encoding
#   7. JSON and Text Response Handling
#   8. Common Logging and Error Handling
#   9. HTTP Status Code Validation
#
# Available Methods:
#
#   getBearerToken(forceRefresh=False)
#       Generates or retrieves a cached OAuth Bearer Token.
#
#   postToMES(mesUrl, payload)
#       Posts a JSON payload to a target MES URL using OAuth Bearer Token.
#
#   postToMESNoAuth(targetUrl, payload)
#       Posts a JSON payload directly to a target URL without authentication.
#
# Security Notes:
#   - OAuth client credentials should be stored in secure Gateway configuration.
#   - Do not log access tokens, client secrets, passwords, or sensitive headers.
#   - HTTPS must be used for production REST API communication.
#
# Author         : Hari
# Version        : 1.1
# Date           : 22-Jul-2026
#
# Change History
# -----------------------------------------------------------------------------
# Sl No | Version | Date        | Author | Fix/Change
# -----------------------------------------------------------------------------
# 1     | 1.0     | 30-Jun-2026 | Hari   | Initial version with OAuth token
#       |         |             |        | generation and authenticated MES POST.
# -----------------------------------------------------------------------------
# 2     | 1.1     | 22-Jul-2026 | Hari   | Added postToMESNoAuth() for APIs that
#       |         |             |        | do not require an OAuth Bearer Token.
#       |         |             |        | Added common response parsing and
#       |         |             |        | improved validation and logging.
# -----------------------------------------------------------------------------
###############################################################################

import system
import time
import urllib


###############################################################################
# Logger Configuration
###############################################################################

logger = system.util.getLogger("PROJ_LIB_MES_API_CLIENT")


###############################################################################
# Configuration
###############################################################################

TOKEN_URL = (
    "https://aprisomesdev.agratas.com/"
    "Apriso/Portal/sts/2.0/token"
)

TOKEN_TIMEOUT = 30000
MES_TIMEOUT = 30000


###############################################################################
# OAuth Client Configuration
#
# IMPORTANT:
# Replace the placeholder values using secure Gateway configuration.
# Do not store production secrets directly in the project script.
###############################################################################

OAUTH_CLIENT_ID = "<OAUTH_CLIENT_ID>"
OAUTH_CLIENT_SECRET = "<OAUTH_CLIENT_SECRET>"
OAUTH_SCOPE = "standard_operations"
OAUTH_STATE = "AgratasScadaIntegrations"
OAUTH_GRANT_TYPE = "client_credentials"


###############################################################################
# Token Cache
#
# The access token is cached in memory until shortly before its expiry time.
###############################################################################

_token_cache = {
    "access_token": None,
    "expires_at": 100
}


###############################################################################
# Function : _encodePayload()
#
# Description:
# Converts the supplied payload into a JSON string.
#
# Behaviour:
#   - Dictionary/List payloads are JSON encoded.
#   - String payloads are sent without encoding again.
#
# This prevents double JSON encoding when the caller already provides a
# correctly formatted JSON string.
#
# Input:
#   payload - Dictionary, list, Java map, Java list, or JSON string.
#
# Returns:
#   JSON request body as a string.
###############################################################################

def _encodePayload(payload):

    if payload is None:
        return "{}"

    ###########################################################################
    # Preserve an existing JSON string without encoding it again
    ###########################################################################

    if isinstance(payload, basestring):
        return payload

    ###########################################################################
    # Convert dictionary/list/Java object into JSON text
    ###########################################################################

    return system.util.jsonEncode(payload)


###############################################################################
# Function : _parseResponse()
#
# Description:
# Parses an HTTP response.
#
# Behaviour:
#   - Returns parsed JSON when the response contains valid JSON.
#   - Returns response text when the response is not JSON.
#   - Returns an empty dictionary when the response body is empty.
#
# Input:
#   response - Ignition HTTP response object.
#
# Returns:
#   Dictionary, list, string, or empty dictionary.
###############################################################################

def _parseResponse(response):

    responseText = response.getText()

    if responseText is None:
        return {}

    responseText = str(responseText).strip()

    if not responseText:
        return {}

    try:
        return system.util.jsonDecode(responseText)

    except Exception:

        logger.debug(
            "Response is not valid JSON. Returning response as text."
        )

        return responseText


###############################################################################
# Function : _validateHttpResponse()
#
# Description:
# Validates the HTTP response status code.
#
# Input:
#   response       - Ignition HTTP response object.
#   operationName  - Description used in log/error messages.
#
# Returns:
#   Parsed response body.
#
# Raises:
#   Exception when the HTTP response is outside the 2xx success range.
###############################################################################

def _validateHttpResponse(response, operationName):

    statusCode = response.getStatusCode()
    responseText = response.getText()

    logger.info(
        "%s Response Status : %s" %
        (operationName, statusCode)
    )

    ###########################################################################
    # Treat only HTTP 2xx responses as successful
    ###########################################################################

    if statusCode < 200 or statusCode >= 300:

        logger.error(
            "%s Failed. Status=%s Response=%s" %
            (operationName, statusCode, responseText)
        )

        raise Exception(
            "%s Failed. Status=%s Response=%s" %
            (operationName, statusCode, responseText)
        )

    return _parseResponse(response)


###############################################################################
# Function : getBearerToken()
#
# Description:
# Generates an OAuth Bearer Token using the client credentials flow.
#
# The method uses the cached access token when it is still valid. When
# forceRefresh=True, the cached token is ignored and a new token is requested.
#
# Input:
#   forceRefresh - False:
#                      Use valid cached token when available.
#                  True:
#                      Always request a new OAuth token.
#
# Returns:
#   OAuth access token as a string.
###############################################################################

def getBearerToken(forceRefresh=False):

    logger.info(
        "================ TOKEN GENERATION START ================"
    )

    startTime = system.date.now()
    now = int(time.time())

    try:

        #######################################################################
        # Use cached token if still valid
        #######################################################################

        if not forceRefresh:

            tokenAvailable = (
                _token_cache["access_token"] is not None
            )

            tokenValid = (
                now < _token_cache["expires_at"]
            )

            if tokenAvailable and tokenValid:

                logger.info("Using Cached Bearer Token.")

                return _token_cache["access_token"]

        logger.info("Generating New OAuth Token.")

        #######################################################################
        # Validate OAuth configuration
        #######################################################################

        if (
            not OAUTH_CLIENT_ID or
            OAUTH_CLIENT_ID == "<OAUTH_CLIENT_ID>"
        ):
            raise Exception(
                "OAuth Client ID is not configured."
            )

        if (
            not OAUTH_CLIENT_SECRET or
            OAUTH_CLIENT_SECRET == "<OAUTH_CLIENT_SECRET>"
        ):
            raise Exception(
                "OAuth Client Secret is not configured."
            )

        #######################################################################
        # Create HTTP client
        #######################################################################

        client = system.net.httpClient(
            timeout=TOKEN_TIMEOUT
        )

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }

        #######################################################################
        # OAuth Client Credential Request
        #######################################################################

        formData = {
            "client_id": OAUTH_CLIENT_ID,
            "client_secret": OAUTH_CLIENT_SECRET,
            "scope": OAUTH_SCOPE,
            "state": OAUTH_STATE,
            "grant_type": OAUTH_GRANT_TYPE
        }

        encodedBody = urllib.urlencode(formData)

        logger.info("Calling OAuth Token URL.")

        #######################################################################
        # Call OAuth Token API
        #######################################################################

        response = client.post(
            url=TOKEN_URL,
            headers=headers,
            data=encodedBody
        )

        statusCode = response.getStatusCode()
        responseText = response.getText()

        logger.info(
            "Token API Status Code : %s" %
            statusCode
        )

        #######################################################################
        # Validate OAuth response
        #######################################################################

        if statusCode < 200 or statusCode >= 300:

            logger.error(
                "Token API Failed : %s" %
                responseText
            )

            raise Exception(
                "Token API Failed. Status=%s Response=%s" %
                (statusCode, responseText)
            )

        try:
            tokenResponse = system.util.jsonDecode(
                responseText
            )

        except Exception as jsonEx:

            raise Exception(
                "Invalid JSON received from OAuth Token API. "
                "Error=%s Response=%s" %
                (str(jsonEx), responseText)
            )

        accessToken = tokenResponse.get("access_token")

        if not accessToken:

            logger.error(
                "access_token missing in OAuth response."
            )

            raise Exception(
                "access_token not found in OAuth response: %s" %
                responseText
            )

        expiresIn = tokenResponse.get(
            "expires_in",
            3600
        )

        try:
            expiresIn = int(expiresIn)

        except Exception:
            expiresIn = 3600

        #######################################################################
        # Keep minimum safe expiry value
        #######################################################################

        expiryBuffer = 60

        if expiresIn <= expiryBuffer:
            expiryBuffer = 0

        #######################################################################
        # Store token in memory cache
        #######################################################################

        _token_cache["access_token"] = accessToken
        _token_cache["expires_at"] = (
            now + expiresIn - expiryBuffer
        )

        logger.info(
            "Bearer Token Generated Successfully."
        )

        logger.info(
            "Token Expiry (Seconds) : %s" %
            expiresIn
        )

        return accessToken

    except Exception as ex:

        logger.error(
            "OAuth Token Generation Exception : %s" %
            str(ex)
        )

        raise

    finally:

        elapsed = system.date.secondsBetween(
            startTime,
            system.date.now()
        )

        logger.info(
            "Token Generation Time : %s Seconds" %
            elapsed
        )

        logger.info(
            "================ TOKEN GENERATION END =================="
        )


###############################################################################
# Function : postToMES()
#
# Description:
# Generic authenticated REST POST method.
#
# This method:
#   1. Obtains an OAuth Bearer Token.
#   2. JSON encodes the request payload.
#   3. Sends the request to the supplied MES URL.
#   4. Refreshes the token and retries once when HTTP 401 is returned.
#   5. Validates the HTTP response.
#   6. Returns JSON response or plain-text response.
#
# Input:
#   mesUrl  - Target MES REST API URL.
#   payload - Dictionary, list, Java object, or JSON string.
#
# Returns:
#   Parsed JSON response, response text, or empty dictionary.
#
# Raises:
#   Exception for token generation failure, communication failure,
#   non-2xx HTTP response, or unexpected processing error.
###############################################################################

def postToMES(mesUrl, payload):

    logger.info(
        "================ MES AUTH API START ===================="
    )

    startTime = system.date.now()

    try:

        #######################################################################
        # Validate target URL
        #######################################################################

        if mesUrl is None or not str(mesUrl).strip():

            raise Exception(
                "MES target URL cannot be empty."
            )

        #######################################################################
        # Obtain OAuth Bearer Token
        #######################################################################

        token = getBearerToken()

        #######################################################################
        # Create HTTP client
        #######################################################################

        client = system.net.httpClient(
            timeout=MES_TIMEOUT
        )

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer " + token
        }

        #######################################################################
        # Prepare request body only once
        #######################################################################

        requestBody = _encodePayload(payload)

        logger.info(
            "Authenticated MES URL : %s" %
            mesUrl
        )

        logger.debug(
            "Authenticated MES Payload : %s" %
            requestBody
        )

        #######################################################################
        # Call MES REST API
        #######################################################################

        response = client.post(
            url=mesUrl,
            headers=headers,
            data=requestBody
        )

        #######################################################################
        # If token is expired or invalid, refresh and retry only once
        #######################################################################

        if response.getStatusCode() == 401:

            logger.warn(
                "MES returned HTTP 401. "
                "Refreshing Bearer Token and retrying once."
            )

            token = getBearerToken(
                forceRefresh=True
            )

            headers["Authorization"] = (
                "Bearer " + token
            )

            response = client.post(
                url=mesUrl,
                headers=headers,
                data=requestBody
            )

        #######################################################################
        # Validate and parse response
        #######################################################################

        responseData = _validateHttpResponse(
            response,
            "Authenticated MES API"
        )

        logger.info(
            "Authenticated MES API Executed Successfully."
        )

        try:
            logger.debug(
                "Authenticated MES Response : %s" %
                system.util.jsonEncode(responseData)
            )

        except Exception:
            logger.debug(
                "Authenticated MES Response : %s" %
                str(responseData)
            )

        return responseData

    except Exception as ex:

        logger.error(
            "Authenticated MES Client Exception : %s" %
            str(ex)
        )

        raise

    finally:

        elapsed = system.date.secondsBetween(
            startTime,
            system.date.now()
        )

        logger.info(
            "Authenticated MES API Execution Time : "
            "%s Seconds" %
            elapsed
        )

        logger.info(
            "================ MES AUTH API END ======================"
        )


###############################################################################
# Function : postToMESNoAuth()
#
# Description:
# Generic non-authenticated REST POST method.
#
# This method sends the supplied JSON payload directly to the target URL.
# It does not:
#   - Generate an OAuth token.
#   - Add an Authorization header.
#   - Retry based on token expiry.
#
# The method should only be used when the target endpoint is explicitly
# configured to accept requests without authentication or when another
# security control is applied at the network/API gateway layer.
#
# Input:
#   targetUrl - Target REST API URL.
#   payload   - Dictionary, list, Java object, or JSON string.
#
# Returns:
#   Parsed JSON response, response text, or empty dictionary.
#
# Raises:
#   Exception for communication failure, non-2xx HTTP response,
#   invalid target URL, or unexpected processing error.
###############################################################################

def postToMESNoAuth(targetUrl, payload):

    logger.info(
        "================ MES NO-AUTH API START ================="
    )

    startTime = system.date.now()

    try:

        #######################################################################
        # Validate target URL
        #######################################################################

        if targetUrl is None or not str(targetUrl).strip():

            raise Exception(
                "Non-authenticated target URL cannot be empty."
            )

        #######################################################################
        # Create HTTP client
        #######################################################################

        client = system.net.httpClient(
            timeout=MES_TIMEOUT
        )

        #######################################################################
        # No Authorization header is included
        #######################################################################

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        #######################################################################
        # Prepare JSON request body
        #######################################################################

        requestBody = _encodePayload(payload)

        logger.info(
            "Non-Authenticated Target URL : %s" %
            targetUrl
        )

        logger.debug(
            "Non-Authenticated Request Payload : %s" %
            requestBody
        )

        #######################################################################
        # Call target REST API directly without OAuth token
        #######################################################################

        response = client.post(
            url=targetUrl,
            headers=headers,
            data=requestBody
        )

        #######################################################################
        # Validate and parse response
        #######################################################################

        responseData = _validateHttpResponse(
            response,
            "Non-Authenticated MES API"
        )

        logger.info(
            "Non-Authenticated MES API Executed Successfully."
        )

        try:
            logger.debug(
                "Non-Authenticated MES Response : %s" %
                system.util.jsonEncode(responseData)
            )

        except Exception:
            logger.debug(
                "Non-Authenticated MES Response : %s" %
                str(responseData)
            )

        return responseData

    except Exception as ex:

        logger.error(
            "Non-Authenticated MES Client Exception : %s" %
            str(ex)
        )

        raise

    finally:

        elapsed = system.date.secondsBetween(
            startTime,
            system.date.now()
        )

        logger.info(
            "Non-Authenticated MES API Execution Time : "
            "%s Seconds" %
            elapsed
        )

        logger.info(
            "================ MES NO-AUTH API END ==================="
        )