###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : environment.py
# Module         : Gateway Environment Configuration
#
# Description:
# Single point for values that change between LOCAL, DEV and QA. Update the
# dictionary once before importing/promoting the project into an environment.
###############################################################################


ENVIRONMENT_CONFIG = {
    # Change this label when promoting the project.
    "environment": "LOCAL",

    "zone": "B",
    "tag_provider": "default",

    # Ignition Gateway database connection names.
    "databases": {
        "audit": "MESDEV",
        "recipe": "MESDEV"
    },

    # Add future interface/equipment tag base paths here.
    "tags": {
        "recipe_download": "[Sample_Tags]M2E_RecipeDownload/RecipeDownload",
        "equipment_request": "[default]Interfaces/CELL-AT-01/EquipmentRequest",
        "material_info": (
            "[default]IN11_E305_PCE_POW22_Data/"
            "IN11_E305_PCE_POW22_IN11_E305_PCE_CMS21_AGCalls_AGSetItemInfo"
        ),
        # Runtime AG routing replaces this fallback with the base path resolved
        # from the triggering AGUnloadingMaterial/Handshake tag.
        "unloading_material": "[default]AGCalls/AGUnloadingMaterial/",
        # Runtime AG routing replaces this fallback from the trigger path.
        "scrap_report": "[default]AGCalls/AGScrapReport/",
        # Runtime AG routing replaces this fallback from the trigger path.
        "serial_inbound": "[default]AGCalls/AGSerialInbound/",
        # Runtime AG routing replaces this fallback from the trigger path.
        "user_login": "[default]AGCalls/AGUserLogin/",
        # Runtime AG routing replaces this fallback from the trigger path.
        "user_logout": "[default]AGCalls/AGUserLogout/",
        "operation_result": (
            "[default]IN11_E115_PCE_MIX21_Data/"
            "IN11_E115_PCE_MIX21_IN11_E115_PCE_MIX21_"
            "AGCalls_AGSetOperationResult/"
        )
    },

    # Add one entry per PLC/OPC connection when the project grows.
    "plcs": {
        "primary": {
            "opcua_connection": "PLC"
        }
    },

    # RecipeDownload EquipmentId-to-PLC method routing. Add equipment here to
    # support additional AGMethods targets without creating another WebDev URL.
    "recipe_download_targets": {
        "EQ_Mixing": {
            "plc": "primary",
            "opcua_object_node_id": (
                "nsu=http://agratas.com/UA/;"
                "s=IN11.E123.PAE.NTC11/AGMethods"
            ),
            "opcua_method_node_id": (
                "nsu=http://agratas.com/UA/;"
                "s=IN11.E123.PAE.NTC11/AGMethods/SetRecipe"
            )
        },
        "EQ_Mixing_2": {
            "plc": "primary",
            "opcua_object_node_id": (
                "nsu=http://agratas.com/UA/;"
                "s=IN11.E123.PAE.NTC11/AGMethods"
                    ),
                    "opcua_method_node_id": (
                        "nsu=http://agratas.com/UA/;"
                        "s=IN11.E123.PAE.NTC11/AGMethods/SetRecipe"
                    )
                }

    },

    # MES endpoints and OAuth client-credential configuration.
    "mes": {
        "equipment_url": (
            "https://aprisomespreprd.aginsndgf.prod/apriso/httpServices/"
            "operations/AGR_S2M_ASyncCommonInterface"
        ),
        "material_info_url": (
            "https://aprisomespreprd.aginsndgf.prod/apriso/httpServices/"
            "operations/AGR_S2M_ASyncCommonInterface"
        ),
        "unloading_material_url": (
            "https://aprisomespreprd.aginsndgf.prod/apriso/httpServices/"
            "operations/AGR_S2M_ASyncCommonInterface"
        ),
        "scrap_report_url": (
            "https://aprisomespreprd.aginsndgf.prod/apriso/httpServices/"
            "operations/AGR_S2M_ASyncCommonInterface"
        ),
        "operation_result_url": (
            "https://aprisomespreprd.aginsndgf.prod/apriso/httpServices/"
            "operations/AGR_S2M_ASyncCommonInterface"
        ),
        "unlink_data_url": (
            "https://aprisomespreprd.aginsndgf.prod/apriso/httpServices/"
            "operations/AGR_S2M_ASyncCommonInterface"
        ),
        "production_order_state_url": (
            "https://aprisomespreprd.aginsndgf.prod/apriso/httpServices/"
            "operations/AGR_S2M_ASyncCommonInterface"
        ),
        "serial_inbound_url": (
            "https://aprisomespreprd.aginsndgf.prod/apriso/httpServices/"
            "operations/AGR_S2M_ASyncCommonInterface"
        ),
        "user_logout_url": (
            "https://aprisomespreprd.aginsndgf.prod/apriso/httpServices/"
            "operations/AGR_S2M_ASyncCommonInterface"
        ),
        "user_login_url": (
            "https://aprisomespreprd.aginsndgf.prod/apriso/httpServices/"
            "operations/AGR_S2M_ASyncCommonInterface"
        ),
        "heartbeat_url": (
            "https://aprisomespreprd.aginsndgf.prod/apriso/httpServices/"
            "operations/AGR_S2M_SyncCommonInterface"
        ),
        "token_url": "https://aprisomesdev.agratas.com/Apriso/Portal/sts/2.0/token",
        "client_id": "0D7B8DBF-5612-4E5D-AD8A-9266880105C1",
        "client_secret": "221EBC13-369F-4CF4-80A6-E87D5CAD0C6A",
        "token_scope": "standard_operations",
        "token_state": "AgratasScadaIntegrations",
        "token_grant_type": "client_credentials"
    },

    "mes_heartbeat": {
        "plcs_by_zone": {
            "A": [
                "MOCK_IN11_B118_PPF_WRP11"],
            "B": [
                "MOCK_IN11_B118_PPF_WRP11", "MOCK_IN11_E112_PCE_CLD21",
                "MOCK_IN11_E115_PCE_MIX21", "MOCK_IN11_E117_PCE_COT21",
                "MOCK_IN11_E123_PAE_NTC11", "MOCK_IN11_E123_PCE_NTC11",
                "MOCK_IN11_E305_PCE_CMS21", "MOCK_IN11_E305_PCE_POW22"
            ],
            "C": [
                "MOCK_IN11_B118_PPF_WRP11", "MOCK_IN11_E112_PCE_CLD21",
                "MOCK_IN11_E115_PCE_MIX21", "MOCK_IN11_E117_PCE_COT21",
                "MOCK_IN11_E123_PAE_NTC11", "MOCK_IN11_E123_PCE_NTC11",
                "MOCK_IN11_E305_PCE_CMS21", "MOCK_IN11_E305_PCE_POW22"
            ],
            "D": [
                "MOCK_IN11_B118_PPF_WRP11", "MOCK_IN11_E112_PCE_CLD21",
                "MOCK_IN11_E115_PCE_MIX21", "MOCK_IN11_E117_PCE_COT21",
                "MOCK_IN11_E123_PAE_NTC11", "MOCK_IN11_E123_PCE_NTC11",
                "MOCK_IN11_E305_PCE_CMS21", "MOCK_IN11_E305_PCE_POW22"
            ]
        }
    },

    "material_info": {
        "equipment": "IN11.E305.PCE.POW22",
        "feeding_location": "IN11.E305.PCE.POW22",
        "employee_no": "ADMIN"
    }
}


# -----------------------------------------------------------------------------
# Function    : get_path
# Description : Resolves a nested environment configuration value by key path.
# -----------------------------------------------------------------------------
def get_path(*keys):
    value = ENVIRONMENT_CONFIG
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise Exception("Environment configuration is missing: %s" % ".".join(keys))
        value = value.get(key)
    return value


# -----------------------------------------------------------------------------
# Function    : name
# Description : Returns the configured environment name in uppercase.
# -----------------------------------------------------------------------------
def name():
    return str(get_path("environment")).upper()


def heartbeat_equipment_ids():
    zone = str(get_path("zone") or "").strip()
    ids = get_path("mes_heartbeat", "plcs_by_zone", zone)
    if not isinstance(ids, (list, tuple)) or len(ids) == 0:
        raise Exception("Heartbeat active zone contains no PLC equipment IDs: %s" % zone)
    result = []
    seen = set()
    for raw_id in ids:
        equipment_id = str(raw_id or "").strip()
        invalid = (not equipment_id or "[" in equipment_id or "]" in equipment_id
                   or ".." in equipment_id or equipment_id.startswith("/")
                   or equipment_id.endswith("/"))
        if invalid:
            raise Exception("Invalid heartbeat PLC equipment ID: %s" % equipment_id)
        if equipment_id in seen:
            raise Exception("Duplicate heartbeat PLC equipment ID: %s" % equipment_id)
        seen.add(equipment_id)
        result.append(equipment_id)
    return result


# -----------------------------------------------------------------------------
# Function    : non_secret_summary
# Description : Returns safe environment settings for diagnostics and health APIs.
# -----------------------------------------------------------------------------
def non_secret_summary():
    """Safe values for startup logging/diagnostics; credentials are excluded."""
    return {
        "environment": name(),
        "audit_db": get_path("databases", "audit"),
        "recipe_db": get_path("databases", "recipe"),
        "recipe_tag_base": get_path("tags", "recipe_download"),
        "ag_tag_base": get_path("tags", "equipment_request"),
        "material_info_tag_base": get_path("tags", "material_info"),
        "unloading_material_tag_base": get_path("tags", "unloading_material"),
        "scrap_report_tag_base": get_path("tags", "scrap_report"),
        "operation_result_tag_base": get_path("tags", "operation_result"),
        "opcua_connection": get_path("plcs", "primary", "opcua_connection"),
        "mes_equipment_url": get_path("mes", "equipment_url"),
        "mes_material_info_url": get_path("mes", "material_info_url"),
        "mes_unloading_material_url": get_path("mes", "unloading_material_url"),
        "mes_scrap_report_url": get_path("mes", "scrap_report_url"),
        "mes_serial_inbound_url": get_path("mes", "serial_inbound_url"),
        "mes_user_login_url": get_path("mes", "user_login_url"),
        "mes_user_logout_url": get_path("mes", "user_logout_url"),
        "mes_operation_result_url": get_path("mes", "operation_result_url"),
        "mes_production_order_state_url": get_path(
            "mes", "production_order_state_url"
        ),
        "zone": get_path("zone"),
        "tag_provider": get_path("tag_provider"),
        "mes_heartbeat_url": get_path("mes", "heartbeat_url"),
        "mes_heartbeat_plc_count": len(heartbeat_equipment_ids()),
        "mes_token_url": get_path("mes", "token_url")
    }