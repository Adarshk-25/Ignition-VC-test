###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : mesClient.py
# Module         : Common MES REST Client
#
# Description:
# Common reusable MES REST client for all SCADA -> MES interfaces.
# This module performs:
#   1. OAuth Client Credential Token Generation
#   2. Token Caching
#   3. Automatic Token Refresh
#   4. Generic MES REST API POST
#   5. Common Logging and Error Handling
#
# Author         : Hari
# Version        : 1.0
# Date           : 30-Jun-2026
#
# Change History
# -----------------------------------------------------------------------------
# Sl No | Version | Date       | Author | Fix/Change
# -----------------------------------------------------------------------------
# 1     | 1.0     | 30-Jun-2026| Hari   | Initial Version
# -----------------------------------------------------------------------------
###############################################################################

import system
import time
import urllib

logger = system.util.getLogger("PROJ_LIB_MES_API_CLIENT")

###############################################################################
# Configuration
###############################################################################

TOKEN_URL = "https://aprisomesdev.agratas.com/Apriso/Portal/sts/2.0/token"

TOKEN_TIMEOUT = 30000
MES_TIMEOUT = 30000

###############################################################################
# Token Cache
###############################################################################

_token_cache = {
    "access_token": None,
    "expires_at": 100
}

###############################################################################
# Function : getBearerToken()
#
# Description
# Generates OAuth Bearer Token.
# Uses cached token if not expired.
###############################################################################

def getBearerToken(forceRefresh=False):

    logger.info("================ TOKEN GENERATION START ================")

    startTime = system.date.now()

    now = int(time.time())

    try:

        #######################################################################
        # Use cached token if still valid
        #######################################################################

        if not forceRefresh:

            if (_token_cache["access_token"] is not None and
                    now < _token_cache["expires_at"]):

                logger.info("Using Cached Bearer Token.")

                return _token_cache["access_token"]

        logger.info("Generating New OAuth Token.")

        client = system.net.httpClient(timeout=TOKEN_TIMEOUT)

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        #######################################################################
        # OAuth Client Credentials
        #######################################################################

        formData = {
            "client_id": "0D7B8DBF-5612-4E5D-AD8A-9266880105C1",
            "client_secret": "221EBC13-369F-4CF4-80A6-E87D5CAD0C6A",
            "scope": "standard_operations",
            "state": "AgratasScadaIntegrations",
            "grant_type": "client_credentials"
        }

        encodedBody = urllib.urlencode(formData)

        logger.info("Calling OAuth Token URL.")

        response = client.post(
            url=TOKEN_URL,
            headers=headers,
            data=encodedBody
        )

        statusCode = response.getStatusCode()

        logger.info("Token API Status Code : %s" % statusCode)

        if statusCode < 200 or statusCode >= 300:

            logger.error("Token API Failed : %s" % response.getText())

            raise Exception(
                "Token API Failed. Status=%s Response=%s" %
                (statusCode, response.getText())
            )

        tokenResponse = response.json

        accessToken = tokenResponse.get("access_token")

        if not accessToken:

            logger.error("access_token missing in OAuth response.")

            raise Exception(
                "access_token not found : %s" %
                response.getText()
            )

        expiresIn = tokenResponse.get("expires_in", 3600)

        #######################################################################
        # Store Token in Memory Cache
        #######################################################################

        _token_cache["access_token"] = accessToken
        _token_cache["expires_at"] = now + int(expiresIn) - 60

        logger.info("Bearer Token Generated Successfully.")
        logger.info("Token Expiry (Seconds) : %s" % expiresIn)

        return accessToken

    finally:

        elapsed = system.date.secondsBetween(startTime, system.date.now())

        logger.info("Token Generation Time : %s Seconds" % elapsed)
        logger.info("================ TOKEN GENERATION END ==================")


###############################################################################
# Function : postToMES()
#
# Description
# Generic Common MES POST Method.
#
# Input
#   mesUrl  - MES REST URL
#   payload - JSON Payload
#
# Returns
#   JSON Response
###############################################################################

def postToMES(mesUrl, payload):

    logger.info("================ MES API START =========================")

    startTime = system.date.now()

    try:

        #######################################################################
        # Obtain OAuth Bearer Token
        #######################################################################

        token = getBearerToken()

        client = system.net.httpClient(timeout=MES_TIMEOUT)

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        }

        logger.info("MES URL : %s" % mesUrl)

        logger.debug("MES Payload : %s" %
                     system.util.jsonEncode(payload))

        #######################################################################
        # Call MES REST API
        #######################################################################

        response = client.post(
            url=mesUrl,
            headers=headers,
            data=system.util.jsonEncode(payload)
        )

        #######################################################################
        # If Token Expired, Generate New Token and Retry Once
        #######################################################################

        if response.getStatusCode() == 401:

            logger.warn("Bearer Token Expired. Refreshing Token.")

            token = getBearerToken(forceRefresh=True)

            headers["Authorization"] = "Bearer " + token

            response = client.post(
                url=mesUrl,
                headers=headers,
                data=system.util.jsonEncode(payload)
            )

        statusCode = response.getStatusCode()

        logger.info("MES Response Status : %s" % statusCode)

        if statusCode < 200 or statusCode >= 300:

            logger.error("MES API Failed : %s" % response.getText())

            raise Exception(
                "MES API Failed. Status=%s Response=%s" %
                (statusCode, response.getText())
            )

        logger.info("MES API Executed Successfully.")

        logger.debug("MES Response : %s" %
                     system.util.jsonEncode(response.json))

        return response.json

    except Exception as ex:

        logger.error("MES Client Exception : %s" % str(ex))

        raise

    finally:

        elapsed = system.date.secondsBetween(startTime, system.date.now())

        logger.info("MES API Execution Time : %s Seconds" % elapsed)
        logger.info("================ MES API END ===========================")