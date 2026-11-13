###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : ag_call_routing.py
# Module         : Dynamic AG Call Routing
###############################################################################

from scada_interface.errors import RoutingError


INTERFACE_MARKERS = {
    "S2M.MaterialInfo": "AGSetItemInfo",
    "S2M.UnloadingMaterial": "AGUnloadingMaterial",
    "S2M.ScrapReport": "AGScrapReport",
    "S2M.OperationResult": "AGSetOperationResult",
    "S2M.UnlinkData": "AGUnlink",
    "EquipmentRequest": "EquipmentRequest"
}


def resolve(interface_name, trigger_tag_path):
    path = _text(trigger_tag_path).strip().rstrip("/")
    marker = INTERFACE_MARKERS.get(interface_name)
    if not path:
        raise RoutingError("ROUTING_FAILED", "ROUTE-0001", "AG trigger tag path is empty", 400)
    if interface_name == "EquipmentRequest" and (
        path.endswith("/EquipmentRequest")
        or path.endswith("/EquipmentRequest/Handshake")
    ):
        return _resolve_equipment_request(path)
    if interface_name == "S2M.UnlinkData":
        segments = path.split("/")
        if (not path.startswith("[") or "]" not in segments[0]
                or any(segment in ("", ".", "..") for segment in segments)):
            raise RoutingError("ROUTING_FAILED", "ROUTE-0005",
                               "Malformed UnlinkData trigger path: %s" % path, 400)
    if not marker or not path.endswith("/" + marker + "/Handshake"):
        raise RoutingError(
            "ROUTING_FAILED",
            "ROUTE-0002",
            "Unsupported %s AG trigger path: %s" % (interface_name, path),
            400
        )

    segments = path.split("/")
    marker_index = len(segments) - 2
    if marker_index < 1:
        raise RoutingError("ROUTING_FAILED", "ROUTE-0003", "AG trigger path has no equipment segment: %s" % path, 400)

    provider, first_segment = _provider_and_segment(segments[0])
    equipment_folder = _equipment_folder(first_segment)
    if not equipment_folder:
        raise RoutingError("ROUTING_FAILED", "ROUTE-0004", "AG equipment segment is empty: %s" % path, 400)

    if interface_name == "S2M.UnlinkData":
        # UnlinkData preserves its exact physical trigger parent, including
        # MOCK_, _Data and any intermediate folder spelling.
        base_path = "/".join(segments[:-1]) + "/"
    else:
        base_path = provider + equipment_folder + "/AGCalls/" + marker + "/"
    return {
        "route_type": "AG_CALL",
        "route_source": "TAG_PATH",
        "trigger_tag_path": path,
        "provider_prefix": provider,
        "equipment_folder": equipment_folder,
        "equipment_id": equipment_folder,
        "ag_tag_base_path": base_path,
        "route_interface_name": interface_name,
        "route_marker": marker
    }


def _resolve_equipment_request(path):
    segments = path.split("/")
    if len(segments) < 3:
        raise RoutingError("ROUTING_FAILED", "ROUTE-0003", "EquipmentRequest trigger path is incomplete: %s" % path, 400)
    equipment_segment_index = -2
    if segments[-1] == "Handshake":
        equipment_segment_index = -3
    provider, equipment_folder = _provider_and_segment(segments[equipment_segment_index])
    if not equipment_folder:
        raise RoutingError("ROUTING_FAILED", "ROUTE-0004", "EquipmentRequest equipment segment is empty: %s" % path, 400)
    return {
        "route_type": "AG_CALL",
        "route_source": "TAG_PATH",
        "trigger_tag_path": path,
        "provider_prefix": provider,
        "equipment_folder": equipment_folder,
        "equipment_id": equipment_folder,
        "ag_tag_base_path": "/".join(segments[:equipment_segment_index + 1]),
        "route_interface_name": "EquipmentRequest",
        "route_marker": "EquipmentRequest"
    }


def _provider_and_segment(segment):
    text = _text(segment)
    closing_bracket = text.find("]")
    if closing_bracket >= 0:
        return text[:closing_bracket + 1], text[closing_bracket + 1:]
    return "[default]", text


def _equipment_folder(segment):
    value = _text(segment).strip()
    if value.endswith("_Data"):
        value = value[:-5]
    return value


def _text(value):
    if value is None:
        return ""
    return str(value)