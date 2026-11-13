###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : constants.py
# Module         : Common Constants
#
# Description:
# Central constants for database routing, standard statuses, processing steps
# and target types used by the shared SCADA interface framework.
# Store-and-Forward statuses and lifecycle steps share the framework vocabulary.
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

from scada_interface import environment


# Logical Ignition database connection used by audit writes. The physical
# server/database credentials remain in the Gateway database connection.
DB_NAME = environment.get_path("databases", "audit")

# Standard status codes stored in audit tables and returned in REST envelopes.
STATUS_SUCCESS = "SUCCESS"
STATUS_ACCEPTED = "ACCEPTED"
STATUS_FAILED = "FAILED"
STATUS_AUTH_FAILED = "AUTH_FAILED"
STATUS_VALIDATION_FAILED = "VALIDATION_FAILED"
STATUS_DUPLICATE_TRANSACTION = "DUPLICATE_TRANSACTION"
STATUS_MES_TIMEOUT = "MES_TIMEOUT"
STATUS_MES_ERROR = "MES_ERROR"
STATUS_MES_BUSINESS_REJECTED = "MES_BUSINESS_REJECTED"
STATUS_OPCUA_TIMEOUT = "OPCUA_TIMEOUT"
STATUS_OPCUA_BAD_STATUS = "OPCUA_BAD_STATUS"
STATUS_PLC_REJECTED = "PLC_REJECTED"
STATUS_SCADA_INTERNAL_ERROR = "SCADA_INTERNAL_ERROR"

# Standard step names keep transaction timelines consistent across interfaces.
STEP_REQUEST_RECEIVED = "REQUEST_RECEIVED"
STEP_AUTHENTICATION = "AUTHENTICATION"
STEP_PAYLOAD_VALIDATION = "PAYLOAD_VALIDATION"
STEP_BUSINESS_VALIDATION = "BUSINESS_VALIDATION"
STEP_OPCUA_CALL = "OPCUA_CALL"
STEP_MES_REST_CALL = "MES_REST_CALL"
STEP_AG_CALL_READ = "AG_CALL_READ"
STEP_AG_CALL_WRITE = "AG_CALL_WRITE"
STEP_RESPONSE_CREATED = "RESPONSE_CREATED"
STEP_COMPLETED = "COMPLETED"
STEP_FAILED = "FAILED"
STEP_RETRY = "RETRY"
STEP_MES_RESPONSE_VALIDATION = "MES_RESPONSE_VALIDATION"
STEP_PLC_TAG_WRITE = "PLC_TAG_WRITE"

# Target types define which downstream integration pattern a handler/config uses.
TARGET_OPCUA_METHOD = "OPCUA_METHOD"
TARGET_MES_REST = "MES_REST"
TARGET_SCADA_ONLY = "SCADA_ONLY"
TARGET_TAG_HANDSHAKE = "TAG_HANDSHAKE"
TARGET_MES_REST_TAG_WRITE = "MES_REST_TAG_WRITE"


SF_PENDING = "PENDING"
SF_IN_PROGRESS = "IN_PROGRESS"
SF_DELIVERED = "DELIVERED"
SF_EXPIRED = "EXPIRED"
SF_FAILED = "FAILED"
STEP_STORE_FORWARD_ENQUEUE = "STORE_FORWARD_ENQUEUE"
STEP_STORE_FORWARD_RETRY = "STORE_FORWARD_RETRY"
STEP_STORE_FORWARD_DELIVERED = "STORE_FORWARD_DELIVERED"
STEP_STORE_FORWARD_EXPIRED = "STORE_FORWARD_EXPIRED"
STEP_STORE_FORWARD_FAILED = "STORE_FORWARD_FAILED"
STATUS_STORE_FORWARD_QUEUE_FAILED = "STORE_FORWARD_QUEUE_FAILED"
STATUS_STORE_FORWARD_DISPATCH_FAILED = "STORE_FORWARD_DISPATCH_FAILED"