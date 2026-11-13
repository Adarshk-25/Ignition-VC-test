###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : config.py
# Module         : Static Interface Configuration
#
# Description:
# Holds interface routing and runtime configuration for WebDev endpoints,
# handler modules, target types, timeout/retry settings and audit behavior.
# Store-and-Forward settings keep all existing interfaces opted out by default.
#
# Author         : Hari
# Version        : 2.2
# Date           : 20-Sep-2026
#
# Change History
# -----------------------------------------------------------------------------
# Sl No | Version | Date        | Author | Fix/Change
# -----------------------------------------------------------------------------
# 1     | 1.0     | 07-Jul-2026 | Hari   | Initial documented version
# 2     | 1.1     | 06-Sep-2026 | Hari   | Store-and-Forward audit, debug and observability conventions
# 3     | 1.2     | 09-Sep-2026 | Hari   | Added S2M.UnlinkData durable delivery configuration
# 4     | 1.3     | 09-Sep-2026 | Hari   | Added M2S.MatStatusUpdate OPC UA method interface
# 5     | 1.4     | 11-Sep-2026 | Hari   | Added S2M.UnloadingMaterial AG Call interface
# 6     | 1.5     | 11-Sep-2026 | Hari   | Added asynchronous S2M.ScrapReport interface
# 7     | 1.6     | 11-Sep-2026 | Hari   | Enabled asynchronous UnloadingMaterial delivery
# 8     | 1.7     | 11-Sep-2026 | Hari   | Enabled asynchronous OperationResult delivery
# 9     | 1.8     | 15-Sep-2026 | Hari   | Added M2S.CreateSerial OPC UA method interface
# 10    | 1.9     | 20-Sep-2026 | Hari   | Added S2M.ProductionOrderState asynchronous interface
# 11    | 2.0     | 20-Sep-2026 | Hari   | Added S2M.SerialInbound asynchronous interface
# 12    | 2.1     | 20-Sep-2026 | Hari   | Added S2M.UserLogout asynchronous interface
# 13    | 2.2     | 20-Sep-2026 | Hari   | Added S2M.UserLogin synchronous interface
# -----------------------------------------------------------------------------
###############################################################################

from scada_interface import constants, environment


STATIC_CONFIG = {
    # Recipe download invokes the PLC SetRecipe OPC UA method.
    "RecipeDownload": {
        "interface_name": "RecipeDownload",
        "direction": "M2S_TO_S2E",
        "enabled": True,
        "schema_name": "RECIPE_DOWNLOAD_SCHEMA",
        "handler_module": "scada_interface.interfaces.ag_methods_M2S_RecipeDownload",
        "auth_required": False,
        "target_type": constants.TARGET_OPCUA_METHOD,
        "timeout_ms": 20000,
        "retry_count": 0,
        "retry_backoff_ms": 1000,
        "idempotent": False,
        "audit_enabled": True,
        "debug_enabled": True,
        "payload_logging_mode": "FULL"
    },
    "MaterialDownload": {
        "interface_name": "MaterialDownload",
        "direction": "M2S_TO_S2E",
        "enabled": True,
        "schema_name": "MATERIAL_DOWNLOAD_SCHEMA",
        "handler_module": "scada_interface.interfaces.material_download",
        "auth_required": True,
        "target_type": constants.TARGET_OPCUA_METHOD,
        "opcua_connection": environment.get_path("plcs", "primary", "opcua_connection"),
        "opcua_object_node_id": "ns=2;s=Equipment.Methods",
        "opcua_method_node_id": "ns=2;s=Equipment.Methods.MaterialDownload",
        "timeout_ms": 20000,
        "retry_count": 0,
        "retry_backoff_ms": 1000,
        "idempotent": False,
        "audit_enabled": True,
        "payload_logging_mode": "HASH_ONLY"
    },
    "ProductionOrderStatus": {
        "interface_name": "ProductionOrderStatus",
        "direction": "M2S_ONLY",
        "enabled": True,
        "schema_name": "PRODUCTION_ORDER_STATUS_SCHEMA",
        "handler_module": "scada_interface.interfaces.production_order_status",
        "auth_required": True,
        "target_type": constants.TARGET_SCADA_ONLY,
        "timeout_ms": 20000,
        "retry_count": 0,
        "retry_backoff_ms": 1000,
        "idempotent": False,
        "audit_enabled": True,
        "payload_logging_mode": "HASH_ONLY"
    },
    # EquipmentRequest is initiated by AG Calls tags and completed by outbound MES REST.
    "EquipmentRequest": {
        "interface_name": "EquipmentRequest",
        "direction": "E2S_TO_S2M",
        "enabled": True,
        "schema_name": "EQUIPMENT_REQUEST_SCHEMA",
        "handler_module": "scada_interface.interfaces.equipment_request",
        "auth_required": True,
        "target_type": constants.TARGET_MES_REST,
        "mes_url": environment.get_path("mes", "equipment_url"),
        "mes_interface_name": "S2M.EquipmentRequest",
        "mes_payload_key": "EquipmentRequest",
        "transaction_prefix": "EQP",
        "source_system": "SCADA",
        "target_system": "MES",
        "ag_tag_base_path": environment.get_path("tags", "equipment_request"),
        "timeout_ms": 20000,
        "retry_count": 1,
        "retry_backoff_ms": 1000,
        "idempotent": True,
        "audit_enabled": True,
        "payload_logging_mode": "FULL"
    },
    "S2M.MaterialInfo": {
        "interface_name": "S2M.MaterialInfo",
        "direction": "E2S_TO_S2M",
        "enabled": True,
        "schema_name": "S2M_MATERIAL_INFO_SCHEMA",
        "handler_module": "scada_interface.interfaces.ag_call_S2M_MaterialInfo",
        "auth_required": True,
        "target_type": constants.TARGET_MES_REST,
        "mes_url": environment.get_path("mes", "material_info_url"),
        "mes_interface_name": "S2M.MaterialInfo",
        "mes_payload_key": "MaterialInfo",
        "transaction_prefix": "MAT",
        "source_system": "SCADA",
        "target_system": "MES",
        "ag_tag_base_path": environment.get_path("tags", "material_info"),
        "equipment": environment.get_path("material_info", "equipment"),
        "feeding_location": environment.get_path("material_info", "feeding_location"),
        "employee_no": environment.get_path("material_info", "employee_no"),
        "timeout_ms": 20000,
        "retry_count": 1,
        "retry_backoff_ms": 1000,
        "idempotent": True,
        "audit_enabled": True,
        "debug_enabled": True,
        "payload_logging_mode": "FULL"
    },
    "S2M.OperationResult": {
        "interface_name": "S2M.OperationResult",
        "direction": "E2S_TO_S2M",
        "enabled": True,
        "schema_name": "S2M_OPERATION_RESULT_SCHEMA",
        "handler_module": "scada_interface.interfaces.ag_call_S2M_OperationResult",
        "auth_required": False,
        "outbound_auth_required": environment.name() != "LOCAL",
        "target_type": constants.TARGET_MES_REST,
        "mes_url": environment.get_path("mes", "operation_result_url"),
        "mes_interface_name": "S2M.OperationResult",
        "mes_payload_key": "OperationResults",
        "transaction_prefix": "OPR",
        "source_system": "SCADA",
        "target_system": "MES",
        "ag_tag_base_path": environment.get_path("tags", "operation_result"),
        "timeout_ms": 20000,
        "retry_count": 0,
        "retry_backoff_ms": 1000,
        "idempotent": True,
        "delivery_mode": "ASYNCHRONOUS",
        "mes_success_http_statuses": [200],
        "retry_all_http_failures": True,
        "store_and_forward": {
            "enabled": True,
            "retry_interval_seconds": 60,
            "max_age_hours": 24
        },
        "audit_enabled": True,
        "debug_enabled": environment.name() == "LOCAL",
        "payload_logging_mode": (
            "FULL" if environment.name() == "LOCAL" else "HASH_ONLY"
        )
    },
    "S2M.UnloadingMaterial": {
        "interface_name": "S2M.UnloadingMaterial",
        "direction": "E2S_TO_S2M",
        "enabled": True,
        "schema_name": "S2M_UNLOADING_MATERIAL_SCHEMA",
        "handler_module": "scada_interface.interfaces.ag_call_S2M_UnloadingMaterial",
        "auth_required": False,
        "outbound_auth_required": environment.name() != "LOCAL",
        "target_type": constants.TARGET_MES_REST,
        "mes_url": environment.get_path("mes", "unloading_material_url"),
        "mes_interface_name": "S2M.UnloadingMaterial",
        "mes_payload_key": "UnloadingInfo",
        "transaction_prefix": "UNMAT",
        "source_system": "SCADA",
        "target_system": "MES",
        "ag_tag_base_path": environment.get_path("tags", "unloading_material"),
        "timeout_ms": 20000,
        "retry_count": 0,
        "retry_backoff_ms": 1000,
        "idempotent": True,
        "delivery_mode": "ASYNCHRONOUS",
        "mes_success_http_statuses": [200],
        "retry_all_http_failures": True,
        "store_and_forward": {
            "enabled": True,
            "retry_interval_seconds": 60,
            "max_age_hours": 24
        },
        "audit_enabled": True,
        "debug_enabled": environment.name() == "LOCAL",
        "payload_logging_mode": (
            "FULL" if environment.name() == "LOCAL" else "HASH_ONLY"
        )
    },
    "S2M.ScrapReport": {
        "interface_name": "S2M.ScrapReport",
        "direction": "E2S_TO_S2M",
        "enabled": True,
        "schema_name": "S2M_SCRAP_REPORT_SCHEMA",
        "handler_module": "scada_interface.interfaces.ag_call_S2M_ScrapReport",
        "auth_required": False,
        "outbound_auth_required": environment.name() != "LOCAL",
        "target_type": constants.TARGET_MES_REST,
        "mes_url": environment.get_path("mes", "scrap_report_url"),
        "mes_interface_name": "S2M.ScrapReport",
        "mes_payload_key": "WastageReport",
        "transaction_prefix": "SCRAP",
        "source_system": "SCADA",
        "target_system": "MES",
        "ag_tag_base_path": environment.get_path("tags", "scrap_report"),
        "timeout_ms": 20000,
        "retry_count": 0,
        "retry_backoff_ms": 1000,
        "idempotent": True,
        "delivery_mode": "ASYNCHRONOUS",
        "mes_success_http_statuses": [200],
        "retry_all_http_failures": True,
        "store_and_forward": {
            "enabled": True,
            "retry_interval_seconds": 60,
            "max_age_hours": 24
        },
        "audit_enabled": True,
        "debug_enabled": environment.name() == "LOCAL",
        "payload_logging_mode": (
            "FULL" if environment.name() == "LOCAL" else "HASH_ONLY"
        )
    },
    "S2M.UnlinkData": {
        "interface_name": "S2M.UnlinkData",
        "direction": "E2S_TO_S2M",
        "enabled": True,
        "schema_name": "S2M_UNLINK_DATA_SCHEMA",
        "handler_module": "scada_interface.interfaces.ag_call_S2M_UnlinkData",
        "auth_required": False,
        "outbound_auth_required": environment.name() != "LOCAL",
        "target_type": constants.TARGET_MES_REST,
        "mes_url": environment.get_path("mes", "unlink_data_url"),
        "mes_interface_name": "S2M.UnlinkData",
        "mes_payload_key": "UnlinkData",
        "transaction_prefix": "UNL",
        "source_system": "SCADA",
        "target_system": "MES",
        "timeout_ms": 20000,
        "retry_count": 0,
        "retry_backoff_ms": 1000,
        "idempotent": True,
        "delivery_mode": "ASYNCHRONOUS",
        "mes_success_http_statuses": [200],
        "retry_all_http_failures": True,
        "store_and_forward": {
            "enabled": True,
            "retry_interval_seconds": 60,
            "max_age_hours": 24
        },
        "audit_enabled": True,
        "debug_enabled": environment.name() == "LOCAL",
        "payload_logging_mode": (
            "FULL" if environment.name() == "LOCAL" else "HASH_ONLY"
        )
    },
    "S2M.UserLogout": {
        "interface_name": "S2M.UserLogout",
        "direction": "E2S_TO_S2M",
        "enabled": True,
        "schema_name": "S2M_USER_LOGOUT_SCHEMA",
        "handler_module": "scada_interface.interfaces.ag_call_S2M_UserLogout",
        "auth_required": False,
        "outbound_auth_required": environment.name() != "LOCAL",
        "target_type": constants.TARGET_MES_REST,
        "mes_url": environment.get_path("mes", "user_logout_url"),
        "mes_interface_name": "S2M.UserLogout",
        "mes_payload_key": "UserLogout",
        "transaction_prefix": "LOGOUT",
        "source_system": "SCADA",
        "target_system": "MES",
        "ag_tag_base_path": environment.get_path("tags", "user_logout"),
        "timeout_ms": 20000,
        "retry_count": 0,
        "retry_backoff_ms": 1000,
        "idempotent": True,
        "delivery_mode": "ASYNCHRONOUS",
        "mes_success_http_statuses": [200],
        "retry_all_http_failures": True,
        "store_and_forward": {
            "enabled": True,
            "retry_interval_seconds": 60,
            "max_age_hours": 24
        },
        "audit_enabled": True,
        "debug_enabled": environment.name() == "LOCAL",
        "payload_logging_mode": (
            "FULL" if environment.name() == "LOCAL" else "HASH_ONLY"
        )
    },
    "S2M.UserLogin": {
        "interface_name": "S2M.UserLogin",
        "direction": "E2S_TO_S2M",
        "enabled": True,
        "schema_name": "S2M_USER_LOGIN_SCHEMA",
        "handler_module": "scada_interface.interfaces.ag_call_S2M_UserLogin",
        "auth_required": False,
        "outbound_auth_required": environment.name() != "LOCAL",
        "target_type": constants.TARGET_MES_REST,
        "mes_url": environment.get_path("mes", "user_login_url"),
        "mes_interface_name": "S2M.UserLogin",
        "mes_payload_key": "UserLogin",
        "transaction_prefix": "LOGIN",
        "source_system": "SCADA",
        "target_system": "MES",
        "ag_tag_base_path": environment.get_path("tags", "user_login"),
        "timeout_ms": 20000,
        "retry_count": 0,
        "retry_backoff_ms": 1000,
        "idempotent": False,
        "delivery_mode": "SYNCHRONOUS",
        "mes_success_http_statuses": [200],
        "store_and_forward": {"enabled": False},
        "audit_enabled": True,
        "debug_enabled": environment.name() == "LOCAL",
        "payload_logging_mode": (
            "FULL" if environment.name() == "LOCAL" else "HASH_ONLY"
        )
    },
    "S2M.ProductionOrderState": {
        "interface_name": "S2M.ProductionOrderState",
        "direction": "E2S_TO_S2M",
        "enabled": True,
        "schema_name": "S2M_PRODUCTION_ORDER_STATE_SCHEMA",
        "handler_module": "scada_interface.interfaces.ag_call_S2M_ProductionOrderState",
        "auth_required": False,
        "outbound_auth_required": environment.name() != "LOCAL",
        "target_type": constants.TARGET_MES_REST,
        "mes_url": environment.get_path("mes", "production_order_state_url"),
        "mes_interface_name": "S2M.ProductionOrderState",
        "mes_payload_key": "ProductionOrderState",
        "transaction_prefix": "POS",
        "source_system": "SCADA",
        "target_system": "MES",
        "timeout_ms": 20000,
        "retry_count": 0,
        "retry_backoff_ms": 1000,
        "idempotent": True,
        "delivery_mode": "ASYNCHRONOUS",
        "mes_success_http_statuses": [200],
        "retry_all_http_failures": True,
        "store_and_forward": {
            "enabled": True,
            "retry_interval_seconds": 60,
            "max_age_hours": 24
        },
        "audit_enabled": True,
        "debug_enabled": environment.name() == "LOCAL",
        "payload_logging_mode": (
            "FULL" if environment.name() == "LOCAL" else "HASH_ONLY"
        )
    },
    "S2M.SerialInbound": {
        "interface_name": "S2M.SerialInbound",
        "direction": "E2S_TO_S2M",
        "enabled": True,
        "schema_name": "S2M_SERIAL_INBOUND_SCHEMA",
        "handler_module": "scada_interface.interfaces.ag_call_S2M_SerialInbound",
        "auth_required": False,
        "outbound_auth_required": environment.name() != "LOCAL",
        "target_type": constants.TARGET_MES_REST,
        "mes_url": environment.get_path("mes", "serial_inbound_url"),
        "mes_interface_name": "S2M.SerialInbound",
        "mes_payload_key": "SerialInbound",
        "transaction_prefix": "SIN",
        "source_system": "SCADA",
        "target_system": "MES",
        "timeout_ms": 20000,
        "retry_count": 0,
        "retry_backoff_ms": 1000,
        "idempotent": True,
        "delivery_mode": "ASYNCHRONOUS",
        "mes_success_http_statuses": [200],
        "retry_all_http_failures": True,
        "max_serial_info_count": 100,
        "max_request_bytes": 262144,
        "store_and_forward": {
            "enabled": True,
            "retry_interval_seconds": 60,
            "max_age_hours": 24
        },
        "audit_enabled": True,
        "debug_enabled": environment.name() == "LOCAL",
        "payload_logging_mode": (
            "FULL" if environment.name() == "LOCAL" else "HASH_ONLY"
        )
    },
    # Work order download dynamically derives the PLC connection and
    # SetWorkOrder NodeIds from the dotted EquipmentId request value.
    "WorkOrderDownload": {
        "interface_name": "WorkOrderDownload",
        "direction": "M2S_TO_S2E",
        "enabled": True,
        "schema_name": "WORK_ORDER_DOWNLOAD_SCHEMA",
        "handler_module": "scada_interface.interfaces.ag_methods_M2S_WorkOrderDownload",
        "auth_required": False,
        "target_type": constants.TARGET_OPCUA_METHOD,
        # TEST ONLY: opcua_client intercepts MOCKME without contacting a PLC.
        # Set False before deploying this interface against a real PLC.
        "mock_plc_enabled": True,
        "timeout_ms": 20000,
        "retry_count": 0,
        "retry_backoff_ms": 1000,
        "idempotent": False,
        "audit_enabled": True,
        "debug_enabled": True,
        "payload_logging_mode": "FULL"
    },
    # Material status updates use the payload EquipmentId for dynamic PLC
    # routing. MOCKME is enabled until the live method contract is approved.
    "MatStatusUpdate": {
        "interface_name": "MatStatusUpdate",
        "direction": "M2S_TO_S2E",
        "enabled": True,
        "schema_name": "MAT_STATUS_UPDATE_SCHEMA",
        "handler_module": "scada_interface.interfaces.ag_methods_M2S_MatStatusUpdate",
        "message_header_aliases": ["M2S.MatStatusUpdate", "M2S.BlockProduct"],
        "auth_required": False,
        "target_type": constants.TARGET_OPCUA_METHOD,
        # TEST ONLY: opcua_client intercepts MOCKME without contacting a PLC.
        "mock_plc_enabled": True,
        "timeout_ms": 20000,
        "retry_count": 0,
        "retry_backoff_ms": 1000,
        "idempotent": False,
        "audit_enabled": True,
        "debug_enabled": True,
        "payload_logging_mode": "FULL"
    },
    # CreateSerial dynamically derives the PLC AGCreatSerial method target from
    # the dotted EquipmentID. MOCKME remains enabled until live PLC validation.
    "CreateSerial": {
        "interface_name": "M2S.CreateSerial",
        "direction": "M2S_TO_S2E",
        "enabled": True,
        "schema_name": "CREATE_SERIAL_SCHEMA",
        "handler_module": "scada_interface.interfaces.ag_methods_M2S_CreateSerial",
        "message_header_aliases": ["M2S.CreateSerial"],
        "auth_required": False,
        "target_type": constants.TARGET_OPCUA_METHOD,
        # TEST ONLY: opcua_client intercepts MOCKME without contacting a PLC.
        "mock_plc_enabled": True,
        "timeout_ms": 20000,
        "retry_count": 0,
        "retry_backoff_ms": 1000,
        "idempotent": False,
        "audit_enabled": True,
        "debug_enabled": True,
        "payload_logging_mode": "FULL"
    },
    # Production notifications dynamically derive the PLC connection and
    # AGProductionNotification method from the dotted EquipmentID. MOCKME is
    # enabled until the live PLC method is verified.
    "ProductionNotification": {
        "interface_name": "M2S.ProductionNotification",
        "direction": "M2S_TO_S2E",
        "enabled": True,
        "schema_name": "PRODUCTION_NOTIFICATION_SCHEMA",
        "handler_module": "scada_interface.interfaces.ag_methods_M2S_ProductionNotification",
        "message_header_aliases": ["M2S.ProductionNotification"],
        "auth_required": False,
        "target_type": constants.TARGET_OPCUA_METHOD,
        # TEST ONLY: opcua_client intercepts MOCKME without contacting a PLC.
        "mock_plc_enabled": True,
        "timeout_ms": 20000,
        "retry_count": 0,
        "retry_backoff_ms": 1000,
        "idempotent": False,
        "audit_enabled": True,
        "debug_enabled": True,
        "payload_logging_mode": "FULL"
    },
    "S2M.MESHeartbeat": {
        "interface_name": "S2M.MESHeartbeat",
        "direction": "SCHEDULED_S2M_TO_S2E",
        "enabled": True,
        "schema_name": "S2M_MES_HEARTBEAT_RESPONSE_SCHEMA",
        "handler_module": "scada_interface.interfaces.ag_status_mes_heartbeat",
        "auth_required": False,
        "outbound_auth_required": environment.name() != "LOCAL",
        "target_type": constants.TARGET_MES_REST_TAG_WRITE,
        "mes_url": environment.get_path("mes", "heartbeat_url"),
        "mes_interface_name": "S2M.MESHbit",
        "mes_payload_key": "HeartbeatInfo",
        "transaction_prefix": "HBIT",
        "source_system": "SCADA",
        "target_system": "MES",
        "relative_tag_path": "AGStatus/MESRunning",
        "success_status": "200",
        "timeout_ms": 5000,
        "retry_count": 1,
        "retry_backoff_ms": 1000,
        "idempotent": True,
        "audit_enabled": True,
        "debug_enabled": True,
        "payload_logging_mode": "FULL"
    }
   
}


# -----------------------------------------------------------------------------
# Function    : get_interface_config
# Description : Handles get interface config logic for this module.
# -----------------------------------------------------------------------------
def get_interface_config(interface_name):
    cfg = STATIC_CONFIG.get(interface_name)
    # Disabled or unknown interfaces are rejected before handler import.
    if cfg and cfg.get("enabled", True):
        return cfg

    raise Exception("Enabled interface configuration not found: %s" % interface_name)


# No existing interface opts in. A caller must explicitly declare its contract.
STORE_FORWARD_DISPATCHER = {"batch_size": 50, "lock_timeout_seconds": 120,
                            "debug_enabled": False}
STORE_FORWARD_DEFAULTS = {"enabled": False, "retry_interval_seconds": 60,
                          "max_age_hours": 24}


# -----------------------------------------------------------------------------
# Function    : get_store_forward_config
# Description : Validates the asynchronous idempotent contract and persistence settings.
# -----------------------------------------------------------------------------
def get_store_forward_config(cfg):
    result = dict(STORE_FORWARD_DEFAULTS)
    result.update(cfg.get("store_and_forward") or {})
    if result.get("enabled") is not True:
        return result
    if (cfg.get("enabled", True) is not True
            or cfg.get("delivery_mode") != "ASYNCHRONOUS"
            or cfg.get("idempotent") is not True
            or cfg.get("target_type") != constants.TARGET_MES_REST):
        raise ValueError("Store-and-Forward requires an enabled asynchronous idempotent MES interface")
    interval = int(result["retry_interval_seconds"])
    age = float(result["max_age_hours"])
    if interval <= 0 or not 0 < age <= 24 or int(age * 3600) < 1:
        raise ValueError("Invalid Store-and-Forward retry interval or maximum age")
    if int(cfg.get("timeout_ms", 20000)) <= 0:
        raise ValueError("A bounded positive HTTP timeout is required")
    validator = cfg.get("mes_acceptance_validator")
    if validator is not None and not callable(validator):
        raise ValueError("MES acceptance validator must be callable")
    result["retry_interval_seconds"] = interval
    result["max_age_hours"] = age
    return result