###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : errors.py
# Module         : Framework Errors
#
# Description:
# Defines common exception classes used by authentication, validation, MES REST,
# OPC UA and generic interface processing paths.
# Delivery eligibility and persistence failures preserve the common error shape.
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

class InterfaceError(Exception):
    # -----------------------------------------------------------------------------
    # Function    : __init__
    # Description : Handles init  logic for this module.
    # -----------------------------------------------------------------------------
    def __init__(self, status_code, error_code, message, http_status=500, details=None):
        # One base error shape lets router responses and audit handling stay generic.
        Exception.__init__(self, message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.http_status = http_status
        self.details = details or {}


class AuthError(InterfaceError):
    pass


class ValidationError(InterfaceError):
    pass


class RoutingError(InterfaceError):
    pass


class DuplicateTransactionError(InterfaceError):
    pass


class MesError(InterfaceError):
    pass


class OpcuaError(InterfaceError):
    pass


class MesDeliveryError(MesError):
    # -----------------------------------------------------------------------------
    # Function    : __init__
    # Description : Initializes the typed error while preserving common router/audit fields.
    # -----------------------------------------------------------------------------
    def __init__(self, message, eligible=False, http_status=None, response_body=None):
        MesError.__init__(self, "MES_ERROR", "MES-SF-001", message,
                          http_status or 502, {"delivery_eligible": eligible,
                                               "mes_http_status": http_status})
        self.eligible = eligible
        self.mes_http_status = http_status
        self.response_body = response_body


class StoreForwardError(InterfaceError):
    # -----------------------------------------------------------------------------
    # Function    : __init__
    # Description : Initializes the typed error while preserving common router/audit fields.
    # -----------------------------------------------------------------------------
    def __init__(self, message):
        InterfaceError.__init__(self, "STORE_FORWARD_QUEUE_FAILED", "DB-SF-001", message)