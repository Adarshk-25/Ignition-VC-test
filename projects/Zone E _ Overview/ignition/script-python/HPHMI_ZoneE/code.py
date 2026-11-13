# HPHMI_ZoneE  -  project script library (Ignition 8.3, Jython 2.7)   v4
# Data model + popup helpers for the Zone E command-centre overview (Zone E/Zone E Overview).
# Layout: process matrix - columns = process areas (Mixing, Coating & Recovery, Calendering, Notching & Slitting),
#         rows = lines (Anode L1, Anode L2, Cathode L1, Cathode L2). Every equipment position gets a tile; positions
#         without PLC signals ("planned") are shown greyed with their value labels and "--".
# Only existing IN11_* nodeset tags are read. Machine alarms come from two sources (as in MIX11/NTC11_Alarms):
#   (1) PLC JSON document <unit>/AGAdmin/CurrentAlarms, described via [default]SCADA_Config/AlarmLookup
#   (2) Ignition alarms whose source path is inside the unit folder (+ gateway alarms such as PLC_Communication)
#   buildModel(width)  one poll per session (binding on viewport width + now(3000))
#   openQuickView(), openFaceplate(), openAreaScreen(), openEquipmentList()   helpers for events
#   unitAlarms(), driveStates(), equipmentList()                               data for the popups
# AREAS / LANES are generated from hmi_build/zoneE_model.js (edit the model there and re-run build.js).

PROVIDER = "[default]"
LOOKUP_TAG = "[default]SCADA_Config/AlarmLookup"
ALARM_DOC = "AGAdmin/CurrentAlarms"
POPUP_QUICKVIEW = "hphmiQuickView"
WIDE_PX = 1600
MAX_ALARM_ROWS = 50

# AGStatus/CurrentState: 0 NotAvailable, 1 OutOfService, 2 NotExecuting, 3 Executing
# AGStatus/CurrentMode : 0 None, 1 Maintenance, 2 Setup, 3 Processing
LANES = [{u"id": u"AL1", u"side": u"Anode", u"line": u"Line 1"}, {u"id": u"AL2", u"side": u"Anode", u"line": u"Line 2"}, {u"id": u"CL1", u"side": u"Cathode", u"line": u"Line 1"}, {u"id": u"CL2", u"side": u"Cathode", u"line": u"Line 2"}]
AREAS = [
	{"id": u"mixing", "step": 1, "title": u"Mixing", "short": u"Mixing", "page": u"/sanand/zone-e/mixing", "kpiFolder": u"Mixing", "sim": False,
	 "cells": {
		u"AL1": {"units": [],
		 "planned": [{u"unitId": u"AMIX101", u"description": u"Anode mixer L1 #1 \u2013 not connected", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"AMIX102", u"description": u"Anode mixer L1 #2 \u2013 not connected", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"AMIX103", u"description": u"Anode mixer L1 #3 \u2013 not connected", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"AMIX104", u"description": u"Anode mixer L1 #4 \u2013 not connected", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}],
		 "summary": None},
		u"AL2": {"units": [],
		 "planned": [{u"unitId": u"AMIX201", u"description": u"Anode mixer L2 #1 \u2013 not connected", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"AMIX202", u"description": u"Anode mixer L2 #2 \u2013 not connected", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"AMIX203", u"description": u"Anode mixer L2 #3 \u2013 not connected", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"AMIX204", u"description": u"Anode mixer L2 #4 \u2013 not connected", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}],
		 "summary": None},
		u"CL1": {"units": [
			{u"unitId": u"MIX01", u"folder": u"IN11_E115_PCE_MIX01", u"description": u"Cathode mixer 01", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"Telemetry/WPA919/LIT004/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"Telemetry/WPA919/TT005/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Planetary", u"tl": u"Planetary", u"path": u"Telemetry/WPA919/ST01/PV", u"unit": u"rpm", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Disperser", u"tl": u"Disperser", u"path": u"Telemetry/WPA919/ST02/PV", u"unit": u"rpm", u"fmt": u"#,##0", u"kind": u"value"}, {u"label": u"Tank pressure", u"tl": u"Tank pressure", u"path": u"Telemetry/WPA919/PT010/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}, {u"label": u"NMP flow", u"tl": u"NMP flow", u"path": u"Telemetry/WPA900/FIT008/PV", u"unit": u"L/min", u"fmt": u"#,##0.0", u"kind": u"value"}], u"drives": [u"Telemetry/UCA019/TAC01/Running", u"Telemetry/UCA019/TAC02/Running", u"Telemetry/UCA019/TAC03/Running"], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/MIX01", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"MIX11", u"folder": u"IN11_E115_PCE_MIX11", u"description": u"Cathode mixer 11", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"Telemetry/WPA923/LIT010/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"Telemetry/WPA923/TT011/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Planetary", u"tl": u"Planetary", u"path": u"Telemetry/WPA923/ST01/PV", u"unit": u"rpm", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Disperser", u"tl": u"Disperser", u"path": u"Telemetry/WPA923/ST02/PV", u"unit": u"rpm", u"fmt": u"#,##0", u"kind": u"value"}, {u"label": u"Tank pressure", u"tl": u"Tank pressure", u"path": u"Telemetry/WPA923/PT021/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}, {u"label": u"NMP flow", u"tl": u"NMP flow", u"path": u"Telemetry/WPA900/FIT007/PV", u"unit": u"L/min", u"fmt": u"#,##0.0", u"kind": u"value"}], u"drives": [u"Telemetry/UCA025/TAC01/Running", u"Telemetry/UCA025/TAC02/Running", u"Telemetry/UCA025/TAC03/Running"], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/MIX11", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"MIX12", u"folder": u"IN11_E115_PCE_MIX12", u"description": u"Cathode mixer 12", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"Telemetry/WPA923/LIT005/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"Telemetry/WPA923/TT006/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Planetary", u"tl": u"Planetary", u"path": u"Telemetry/WPA923/ST01/PV", u"unit": u"rpm", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Disperser", u"tl": u"Disperser", u"path": u"Telemetry/WPA923/ST02/PV", u"unit": u"rpm", u"fmt": u"#,##0", u"kind": u"value"}, {u"label": u"Tank pressure", u"tl": u"Tank pressure", u"path": u"Telemetry/WPA923/PT012/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}, {u"label": u"NMP flow", u"tl": u"NMP flow", u"path": u"Telemetry/WPA900/FIT006/PV", u"unit": u"L/min", u"fmt": u"#,##0.0", u"kind": u"value"}], u"drives": [u"Telemetry/UCA028/TAC01/Running", u"Telemetry/UCA028/TAC02/Running", u"Telemetry/UCA028/TAC03/Running"], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/MIX12", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"MIX13", u"folder": u"IN11_E115_PCE_MIX13", u"description": u"Cathode mixer 13", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"Telemetry/WPA923/LIT004/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"Telemetry/WPA923/TT005/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Planetary", u"tl": u"Planetary", u"path": u"Telemetry/WPA923/ST01/PV", u"unit": u"rpm", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Disperser", u"tl": u"Disperser", u"path": u"Telemetry/WPA923/ST02/PV", u"unit": u"rpm", u"fmt": u"#,##0", u"kind": u"value"}, {u"label": u"Tank pressure", u"tl": u"Tank pressure", u"path": u"Telemetry/WPA923/PT010/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}, {u"label": u"NMP flow", u"tl": u"NMP flow", u"path": u"Telemetry/WPA900/FIT005/PV", u"unit": u"L/min", u"fmt": u"#,##0.0", u"kind": u"value"}], u"drives": [u"Telemetry/UCA031/TAC01/Running", u"Telemetry/UCA031/TAC02/Running", u"Telemetry/UCA031/TAC03/Running"], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/MIX13", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"MIX14", u"folder": u"IN11_E115_PCE_MIX14", u"description": u"Cathode mixer 14", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"Telemetry/WPA923/LIT003/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"Telemetry/WPA923/TT004/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Planetary", u"tl": u"Planetary", u"path": u"Telemetry/WPA923/ST01/PV", u"unit": u"rpm", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Disperser", u"tl": u"Disperser", u"path": u"Telemetry/WPA923/ST02/PV", u"unit": u"rpm", u"fmt": u"#,##0", u"kind": u"value"}, {u"label": u"Tank pressure", u"tl": u"Tank pressure", u"path": u"Telemetry/WPA923/PT008/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}, {u"label": u"NMP flow", u"tl": u"NMP flow", u"path": u"Telemetry/WPA900/FIT004/PV", u"unit": u"L/min", u"fmt": u"#,##0.0", u"kind": u"value"}], u"drives": [u"Telemetry/UCA034/TAC01/Running", u"Telemetry/UCA034/TAC02/Running", u"Telemetry/UCA034/TAC03/Running"], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/MIX14", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"SLU11", u"folder": u"IN11_E115_PCE_SLU11", u"description": u"Slurry transfer 11", u"keyValues": [], u"drives": [u"Telemetry/UCA037/TAC01/Running", u"Telemetry/UCA037/TAC02/Running", u"Telemetry/UCA037/TAC03/Running", u"Telemetry/UCA037/TAC04/Running", u"Telemetry/UCA037/TAC05/Running", u"Telemetry/UCA037/TAC06/Running", u"Telemetry/UCA037/TAC07/Running", u"Telemetry/UCA037/TAC08/Running", u"Telemetry/UCA037/TAC09/Running"], u"speed": False, u"sim": False, u"kind": u"", u"tile": 1, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/SLU11", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"STS11", u"folder": u"IN11_E115_PCE_STS11", u"description": u"Slurry storage 11", u"keyValues": [{u"label": u"SUL-STK1-1", u"tl": u"SUL-STK1-1", u"path": u"Telemetry/WPA923/LIT007/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"SUL-STK1-2", u"tl": u"SUL-STK1-2", u"path": u"Telemetry/WPA923/LIT006/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"CER-STK1-1", u"tl": u"CER-STK1-1", u"path": u"Telemetry/WPA919/LIT003/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"STK1-1 temp.", u"tl": u"STK1-1 temp.", u"path": u"Telemetry/WPA923/TT008/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"STK1-2 temp.", u"tl": u"STK1-2 temp.", u"path": u"Telemetry/WPA923/TT007/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"CER temp.", u"tl": u"CER temp.", u"path": u"Telemetry/WPA919/TT004/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}], u"drives": [], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/STS11", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"SCS11", u"folder": u"IN11_E117_PCE_SCS11", u"description": u"Slurry supply 11", u"keyValues": [{u"label": u"Tank 1 level", u"tl": u"Tank 1", u"path": u"Telemetry/WPA923/LIT008/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Tank 2 level", u"tl": u"Tank 2", u"path": u"Telemetry/WPA923/LIT009/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"CER tank level", u"tl": u"CER tank level", u"path": u"Telemetry/WPA919/LIT002/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"Telemetry/WPA923/TT010/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Tank pressure", u"tl": u"Tank pressure", u"path": u"Telemetry/WPA923/PT013/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}, {u"label": u"CER tank press.", u"tl": u"CER tank press.", u"path": u"Telemetry/WPA919/PT004/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}], u"drives": [], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/SCS11", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"SCS12", u"folder": u"IN11_E119_PCE_SCS12", u"description": u"Slurry supply 12", u"keyValues": [{u"label": u"Tank 1 level", u"tl": u"Tank 1", u"path": u"Telemetry/WPA923/LIT001/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Tank 2 level", u"tl": u"Tank 2", u"path": u"Telemetry/WPA923/LIT002/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"CER tank level", u"tl": u"CER tank level", u"path": u"Telemetry/WPA919/LIT001/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"Telemetry/WPA923/TT003/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Tank pressure", u"tl": u"Tank pressure", u"path": u"Telemetry/WPA923/PT004/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}, {u"label": u"CER tank press.", u"tl": u"CER tank press.", u"path": u"Telemetry/WPA919/PT002/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}], u"drives": [], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/SCS12", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"WES11", u"folder": u"IN11_E112_PCE_WES11", u"description": u"NMP weighing 11", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"Telemetry/WPA914/LIT002/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Temp.", u"tl": u"Temp.", u"path": u"Telemetry/WPA914/TT001/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Tank pressure", u"tl": u"Tank pressure", u"path": u"Telemetry/WPA914/PT002/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}, {u"label": u"Outlet pressure", u"tl": u"Outlet pressure", u"path": u"Telemetry/WPA914/PT001/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}], u"drives": [], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/WES11", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"LIQ11", u"folder": u"IN11_E205_PCE_LIQ11", u"description": u"Liquid dosing 11", u"keyValues": [], u"drives": [u"Telemetry/UCA016/TAC01/Running", u"Telemetry/UCA016/TAC02/Running", u"Telemetry/UCA016/TAC04/Running", u"Telemetry/UCA016/TAC05/Running", u"Telemetry/UCA016/TAC06/Running"], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/LIQ11", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"LIQ12", u"folder": u"IN11_E112_PCE_LIQ12", u"description": u"Liquid dosing 12", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"Telemetry/WPA900/LIT001/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Weight", u"tl": u"Weight", u"path": u"Telemetry/WPA900/BWA001/ForcePV", u"unit": u"kg", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Temp.", u"tl": u"Temp.", u"path": u"Telemetry/WPA900/TT001/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Tank pressure", u"tl": u"Tank pressure", u"path": u"Telemetry/WPA900/PT002/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}], u"drives": [u"Telemetry/UCA013/TAC01/Running", u"Telemetry/UCA013/TAC02/Running"], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/LIQ12", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"CNT11", u"folder": u"IN11_E205_PCE_CNT11", u"description": u"CNT dosing 11", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"Telemetry/WPA917/LIT001/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Weight", u"tl": u"Weight", u"path": u"Telemetry/WPA917/BWA001/ForcePV", u"unit": u"kg", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Temp.", u"tl": u"Temp.", u"path": u"Telemetry/WPA917/TT001/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Tank pressure", u"tl": u"Tank pressure", u"path": u"Telemetry/WPA917/PT002/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}], u"drives": [], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/CNT11", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"DSS11", u"folder": u"IN11_E205_PCE_DSS11", u"description": u"Dispersant dosing 11", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"Telemetry/WPA918/LIT001/LevelPV", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Weight", u"tl": u"Weight", u"path": u"Telemetry/WPA918/BWA002/ForcePV", u"unit": u"kg", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Tank pressure", u"tl": u"Tank pressure", u"path": u"Telemetry/WPA918/PT004/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}, {u"label": u"Out MPM1/2", u"tl": u"Out MPM1/2", u"path": u"Telemetry/WPA918/PT002/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}], u"drives": [], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/DSS11", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"CMS11", u"folder": u"IN11_E305_PCE_CMS11", u"description": u"CM feed 11", u"keyValues": [{u"label": u"Weigh wt.", u"tl": u"Weigh wt.", u"path": u"Telemetry/WPA916/BWA004/ForcePV", u"unit": u"kg", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Send wt.", u"tl": u"Send wt.", u"path": u"Telemetry/WPA916/BWA008/ForcePV", u"unit": u"kg", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Unpack wt.", u"tl": u"Unpack wt.", u"path": u"Telemetry/WPA916/BWA009/ForcePV", u"unit": u"kg", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Disch. FCV", u"tl": u"Disch. FCV", u"path": u"Telemetry/WPA916/FCV040/PV", u"unit": u"%", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Send dP", u"tl": u"Send dP", u"path": u"Telemetry/WPA916/PT007/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}], u"drives": [], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/CMS11", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"CMS12", u"folder": u"IN11_E305_PCE_CMS12", u"description": u"CM feed 12", u"keyValues": [{u"label": u"BWA002 wt.", u"tl": u"BWA002", u"path": u"Telemetry/WPA916/BWA002/ForcePV", u"unit": u"kg", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"BWA003 wt.", u"tl": u"BWA003", u"path": u"Telemetry/WPA916/BWA003/ForcePV", u"unit": u"kg", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"BWA005 wt.", u"tl": u"BWA005", u"path": u"Telemetry/WPA916/BWA005/ForcePV", u"unit": u"kg", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Disch. FCV", u"tl": u"Disch. FCV", u"path": u"Telemetry/WPA916/FCV026/PV", u"unit": u"%", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"PT006 dP", u"tl": u"PT006", u"path": u"Telemetry/WPA916/PT006/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}], u"drives": [], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/CMS12", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"CRS11", u"folder": u"IN11_E305_PCE_CRS11", u"description": u"Ceramic feed 11", u"keyValues": [{u"label": u"BWA001 wt.", u"tl": u"BWA001", u"path": u"Telemetry/WPA916/BWA001/ForcePV", u"unit": u"kg", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"BWA011 wt.", u"tl": u"BWA011", u"path": u"Telemetry/WPA916/BWA011/ForcePV", u"unit": u"kg", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"BWA012 wt.", u"tl": u"BWA012", u"path": u"Telemetry/WPA916/BWA012/ForcePV", u"unit": u"kg", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Disch. FCV", u"tl": u"Disch. FCV", u"path": u"Telemetry/WPA916/FCV018/PV", u"unit": u"%", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"PT004 dP", u"tl": u"PT004", u"path": u"Telemetry/WPA916/PT004/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}], u"drives": [], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/CRS11", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"POW11", u"folder": u"IN11_E305_PCE_POW11", u"description": u"Powder feed 11", u"keyValues": [], u"drives": [u"Telemetry/UCA004/TAC01/Running", u"Telemetry/UCA004/TAC02/Running", u"Telemetry/UCA004/TAC03/Running", u"Telemetry/UCA004/TAC04/Running", u"Telemetry/UCA004/TAC05/Running", u"Telemetry/UCA004/TAC06/Running", u"Telemetry/UCA004/TAC07/Running", u"Telemetry/UCA004/TAC08/Running", u"Telemetry/UCA004/TAC09/Running", u"Telemetry/UCA004/TAC10/Running", u"Telemetry/UCA004/TAC11/Running", u"Telemetry/UCA004/TAC12/Running", u"Telemetry/UCA004/TAC13/Running", u"Telemetry/UCA004/TAC14/Running"], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/POW11", u"page": u"/sanand/zone-e/mixing", u"openPage": False},
			{u"unitId": u"PVS11", u"folder": u"IN11_E305_PCE_PVS11", u"description": u"PVDF / SP feed 11", u"keyValues": [{u"label": u"BWA006 wt.", u"tl": u"BWA006", u"path": u"Telemetry/WPA916/BWA006/ForcePV", u"unit": u"kg", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"BWA007 wt.", u"tl": u"BWA007", u"path": u"Telemetry/WPA916/BWA007/ForcePV", u"unit": u"kg", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"BWA010 wt.", u"tl": u"BWA010", u"path": u"Telemetry/WPA916/BWA010/ForcePV", u"unit": u"kg", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"PT001 dP", u"tl": u"PT001", u"path": u"Telemetry/WPA916/PT001/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}], u"drives": [], u"speed": False, u"sim": False, u"kind": u"", u"tile": 2, u"tileWide": 0, u"faceplate": u"MIX11_HPHMI/Faceplates/PVS11", u"page": u"/sanand/zone-e/mixing", u"openPage": False}],
		 "planned": [],
		 "summary": None},
		u"CL2": {"units": [],
		 "planned": [{u"unitId": u"CMIX201", u"description": u"Cathode mixer L2 #1 \u2013 not connected", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"CMIX202", u"description": u"Cathode mixer L2 #2 \u2013 not connected", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"CMIX203", u"description": u"Cathode mixer L2 #3 \u2013 not connected", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"CMIX204", u"description": u"Cathode mixer L2 #4 \u2013 not connected", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"CMIX205", u"description": u"Cathode mixer L2 #5 \u2013 not connected", u"keyValues": [{u"label": u"Level", u"tl": u"Level", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0", u"kind": u"level"}, {u"label": u"Slurry temp.", u"tl": u"Slurry T.", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}],
		 "summary": None}}},
	{"id": u"coating", "step": 2, "title": u"Coating & Recovery", "short": u"Coating", "page": u"", "kpiFolder": u"Coating", "sim": False,
	 "cells": {
		u"AL1": {"units": [],
		 "planned": [{u"unitId": u"ACOAT101", u"description": u"Anode coater L1 #1 \u2013 not connected", u"keyValues": [{u"label": u"Coating speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Coat weight", u"tl": u"Coat wt.", u"path": u"-", u"unit": u"g/m\u00b2", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"ACOAT102", u"description": u"Anode coater L1 #2 \u2013 not connected", u"keyValues": [{u"label": u"Coating speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Coat weight", u"tl": u"Coat wt.", u"path": u"-", u"unit": u"g/m\u00b2", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"ARECV101", u"description": u"Anode NMP recovery L1 #1 \u2013 not connected", u"keyValues": [{u"label": u"NMP recovery", u"tl": u"Recovery", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"NMP in exhaust", u"tl": u"Exh. NMP", u"path": u"-", u"unit": u"ppm", u"fmt": u"#,##0", u"kind": u"value"}]}, {u"unitId": u"ARECV102", u"description": u"Anode NMP recovery L1 #2 \u2013 not connected", u"keyValues": [{u"label": u"NMP recovery", u"tl": u"Recovery", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"NMP in exhaust", u"tl": u"Exh. NMP", u"path": u"-", u"unit": u"ppm", u"fmt": u"#,##0", u"kind": u"value"}]}],
		 "summary": None},
		u"AL2": {"units": [],
		 "planned": [{u"unitId": u"ACOAT201", u"description": u"Anode coater L2 #1 \u2013 not connected", u"keyValues": [{u"label": u"Coating speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Coat weight", u"tl": u"Coat wt.", u"path": u"-", u"unit": u"g/m\u00b2", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"ACOAT202", u"description": u"Anode coater L2 #2 \u2013 not connected", u"keyValues": [{u"label": u"Coating speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Coat weight", u"tl": u"Coat wt.", u"path": u"-", u"unit": u"g/m\u00b2", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"ARECV201", u"description": u"Anode NMP recovery L2 #1 \u2013 not connected", u"keyValues": [{u"label": u"NMP recovery", u"tl": u"Recovery", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"NMP in exhaust", u"tl": u"Exh. NMP", u"path": u"-", u"unit": u"ppm", u"fmt": u"#,##0", u"kind": u"value"}]}, {u"unitId": u"ARECV202", u"description": u"Anode NMP recovery L2 #2 \u2013 not connected", u"keyValues": [{u"label": u"NMP recovery", u"tl": u"Recovery", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"NMP in exhaust", u"tl": u"Exh. NMP", u"path": u"-", u"unit": u"ppm", u"fmt": u"#,##0", u"kind": u"value"}]}],
		 "summary": None},
		u"CL1": {"units": [],
		 "planned": [{u"unitId": u"CCOAT101", u"description": u"Cathode coater L1 #1 \u2013 not connected", u"keyValues": [{u"label": u"Coating speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Coat weight", u"tl": u"Coat wt.", u"path": u"-", u"unit": u"g/m\u00b2", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"CCOAT102", u"description": u"Cathode coater L1 #2 \u2013 not connected", u"keyValues": [{u"label": u"Coating speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Coat weight", u"tl": u"Coat wt.", u"path": u"-", u"unit": u"g/m\u00b2", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"CRECV101", u"description": u"Cathode NMP recovery L1 #1 \u2013 not connected", u"keyValues": [{u"label": u"NMP recovery", u"tl": u"Recovery", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"NMP in exhaust", u"tl": u"Exh. NMP", u"path": u"-", u"unit": u"ppm", u"fmt": u"#,##0", u"kind": u"value"}]}, {u"unitId": u"CRECV102", u"description": u"Cathode NMP recovery L1 #2 \u2013 not connected", u"keyValues": [{u"label": u"NMP recovery", u"tl": u"Recovery", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"NMP in exhaust", u"tl": u"Exh. NMP", u"path": u"-", u"unit": u"ppm", u"fmt": u"#,##0", u"kind": u"value"}]}],
		 "summary": None},
		u"CL2": {"units": [],
		 "planned": [{u"unitId": u"CCOAT201", u"description": u"Cathode coater L2 #1 \u2013 not connected", u"keyValues": [{u"label": u"Coating speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Coat weight", u"tl": u"Coat wt.", u"path": u"-", u"unit": u"g/m\u00b2", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"CCOAT202", u"description": u"Cathode coater L2 #2 \u2013 not connected", u"keyValues": [{u"label": u"Coating speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Coat weight", u"tl": u"Coat wt.", u"path": u"-", u"unit": u"g/m\u00b2", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"CRECV201", u"description": u"Cathode NMP recovery L2 #1 \u2013 not connected", u"keyValues": [{u"label": u"NMP recovery", u"tl": u"Recovery", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"NMP in exhaust", u"tl": u"Exh. NMP", u"path": u"-", u"unit": u"ppm", u"fmt": u"#,##0", u"kind": u"value"}]}, {u"unitId": u"CRECV202", u"description": u"Cathode NMP recovery L2 #2 \u2013 not connected", u"keyValues": [{u"label": u"NMP recovery", u"tl": u"Recovery", u"path": u"-", u"unit": u"%", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"NMP in exhaust", u"tl": u"Exh. NMP", u"path": u"-", u"unit": u"ppm", u"fmt": u"#,##0", u"kind": u"value"}]}],
		 "summary": None}}},
	{"id": u"calendering", "step": 3, "title": u"Calendering", "short": u"Calendering", "page": u"/sanand/zone-e/calendering", "kpiFolder": u"Calendering", "sim": False,
	 "cells": {
		u"AL1": {"units": [],
		 "planned": [{u"unitId": u"ACAL101", u"description": u"Anode calender L1 #1 \u2013 not connected", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Roll gap", u"tl": u"Roll gap", u"path": u"-", u"unit": u"mm", u"fmt": u"#,##0.000", u"kind": u"value"}]}, {u"unitId": u"ACAL102", u"description": u"Anode calender L1 #2 \u2013 not connected", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Roll gap", u"tl": u"Roll gap", u"path": u"-", u"unit": u"mm", u"fmt": u"#,##0.000", u"kind": u"value"}]}],
		 "summary": None},
		u"AL2": {"units": [],
		 "planned": [{u"unitId": u"ACAL201", u"description": u"Anode calender L2 #1 \u2013 not connected", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Roll gap", u"tl": u"Roll gap", u"path": u"-", u"unit": u"mm", u"fmt": u"#,##0.000", u"kind": u"value"}]}, {u"unitId": u"ACAL202", u"description": u"Anode calender L2 #2 \u2013 not connected", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Roll gap", u"tl": u"Roll gap", u"path": u"-", u"unit": u"mm", u"fmt": u"#,##0.000", u"kind": u"value"}]}],
		 "summary": None},
		u"CL1": {"units": [
			{u"unitId": u"CLD11", u"folder": u"IN11_E122_PCE_CLD11", u"description": u"Cathode calender 11", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"AGStatus/ActualMachineSpeed", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Roll gap", u"tl": u"Roll gap", u"path": u"Telemetry/HLB001/BGC001/PV", u"unit": u"mm", u"fmt": u"#,##0.000", u"kind": u"value"}, {u"label": u"Hyd. pressure", u"tl": u"Hyd. press.", u"path": u"Telemetry/HLB001/BPA001/PV", u"unit": u"MPa", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Roll heating", u"tl": u"Roll heat", u"path": u"Telemetry/HLB001/EQC001/Temperature", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Unwind tension", u"tl": u"Unwind T.", u"path": u"Telemetry/UWD001/BWC001/PV", u"unit": u"N", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Rewind tension", u"tl": u"Rewind T.", u"path": u"Telemetry/RWD001/BWC001/PV", u"unit": u"N", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Upper roll", u"tl": u"Upper roll", u"path": u"Telemetry/HLB001/MAA001/MotorSpeedPV", u"unit": u"rpm", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Lower roll", u"tl": u"Lower roll", u"path": u"Telemetry/HLB001/MAA002/MotorSpeedPV", u"unit": u"rpm", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Pre-heater", u"tl": u"Pre-heater", u"path": u"Telemetry/IFD001/EBF001/Temperature", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}], u"drives": [], u"speed": True, u"sim": False, u"kind": u"", u"tile": 6, u"tileWide": 9, u"faceplate": u"CLD11_HPHMI/Popups/HLB001_Press", u"page": u"/sanand/zone-e/calendering", u"openPage": False}],
		 "planned": [{u"unitId": u"CCAL102", u"description": u"Cathode calender L1 #2 \u2013 not connected", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Roll gap", u"tl": u"Roll gap", u"path": u"-", u"unit": u"mm", u"fmt": u"#,##0.000", u"kind": u"value"}]}],
		 "summary": None},
		u"CL2": {"units": [],
		 "planned": [{u"unitId": u"CCAL201", u"description": u"Cathode calender L2 #1 \u2013 not connected", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Roll gap", u"tl": u"Roll gap", u"path": u"-", u"unit": u"mm", u"fmt": u"#,##0.000", u"kind": u"value"}]}, {u"unitId": u"CCAL202", u"description": u"Cathode calender L2 #2 \u2013 not connected", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Roll gap", u"tl": u"Roll gap", u"path": u"-", u"unit": u"mm", u"fmt": u"#,##0.000", u"kind": u"value"}]}],
		 "summary": None}}},
	{"id": u"notching", "step": 4, "title": u"Notching & Slitting", "short": u"Notching", "page": u"/sanand/zone-e/lasernotching/cathode-line-1/ntc11-overview", "kpiFolder": u"Notching", "sim": False,
	 "cells": {
		u"AL1": {"units": [
			{u"unitId": u"NTC11", u"folder": u"IN11_E155_PAE_NTC11", u"description": u"Anode notching 11", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"Telemetry/LNT001/BGA001/SpeedPV", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Laser temp. DS", u"tl": u"Laser DS", u"path": u"Telemetry/LNT001/BTA001/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Fume air vel.", u"tl": u"Fume air", u"path": u"Telemetry/LNT001/BFA001/PV", u"unit": u"m/s", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Laser temp. OS", u"tl": u"Laser OS", u"path": u"Telemetry/LNT001/BTA002/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Unwind tension", u"tl": u"Unwind T.", u"path": u"Telemetry/UWD001/IFD001/WT001/PV", u"unit": u"N", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Suction press.", u"tl": u"Suction press.", u"path": u"Telemetry/LNT001/PIT003/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}, {u"label": u"Slitter feed roll", u"tl": u"Slitter feed roll", u"path": u"Telemetry/SLT001/GLC001/MAA001/MotorSpeedPV", u"unit": u"rpm", u"fmt": u"#,##0", u"kind": u"value"}], u"drives": [], u"speed": True, u"sim": False, u"kind": u"", u"tile": 3, u"tileWide": 4, u"faceplate": u"NTC11_HPHMI/NotchingSlitting_Overview", u"page": u"/sanand/zone-e/lasernotching/cathode-line-1/ntc11-overview", u"openPage": False},
			{u"unitId": u"NTC12", u"folder": u"IN11_E155_PAE_NTC12", u"description": u"Anode notching 12", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"Telemetry/LNT001/BGA001/SpeedPV", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Laser temp. DS", u"tl": u"Laser DS", u"path": u"Telemetry/LNT001/BTA001/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Fume air vel.", u"tl": u"Fume air", u"path": u"Telemetry/LNT001/BFA001/PV", u"unit": u"m/s", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Laser temp. OS", u"tl": u"Laser OS", u"path": u"Telemetry/LNT001/BTA002/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Unwind tension", u"tl": u"Unwind T.", u"path": u"Telemetry/UWD001/IFD001/WT001/PV", u"unit": u"N", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Suction press.", u"tl": u"Suction press.", u"path": u"Telemetry/LNT001/PIT003/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}, {u"label": u"Slitter feed roll", u"tl": u"Slitter feed roll", u"path": u"Telemetry/SLT001/GLC001/MAA001/MotorSpeedPV", u"unit": u"rpm", u"fmt": u"#,##0", u"kind": u"value"}], u"drives": [], u"speed": True, u"sim": False, u"kind": u"", u"tile": 3, u"tileWide": 4, u"faceplate": u"NTC11_HPHMI/NotchingSlitting_Overview", u"page": u"/sanand/zone-e/lasernotching/cathode-line-1/ntc11-overview", u"openPage": False}],
		 "planned": [],
		 "summary": None},
		u"AL2": {"units": [],
		 "planned": [{u"unitId": u"ANOT201", u"description": u"Anode notching L2 #1 \u2013 not connected", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Laser temp. DS", u"tl": u"Laser DS", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"ANOT202", u"description": u"Anode notching L2 #2 \u2013 not connected", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Laser temp. DS", u"tl": u"Laser DS", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}],
		 "summary": None},
		u"CL1": {"units": [
			{u"unitId": u"NTC11", u"folder": u"IN11_E123_PCE_NTC11", u"description": u"Cathode notching 11", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"Telemetry/LNT001/BGA001/SpeedPV", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Laser temp. DS", u"tl": u"Laser DS", u"path": u"Telemetry/LNT001/BTA001/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Fume air vel.", u"tl": u"Fume air", u"path": u"Telemetry/LNT001/BFA001/PV", u"unit": u"m/s", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Laser temp. OS", u"tl": u"Laser OS", u"path": u"Telemetry/LNT001/BTA002/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Unwind tension", u"tl": u"Unwind T.", u"path": u"Telemetry/UWD001/IFD001/WT001/PV", u"unit": u"N", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Suction press.", u"tl": u"Suction press.", u"path": u"Telemetry/LNT001/PIT003/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}, {u"label": u"Slitter feed roll", u"tl": u"Slitter feed roll", u"path": u"Telemetry/SLT001/GLC001/MAA001/MotorSpeedPV", u"unit": u"rpm", u"fmt": u"#,##0", u"kind": u"value"}], u"drives": [], u"speed": True, u"sim": False, u"kind": u"", u"tile": 3, u"tileWide": 4, u"faceplate": u"NTC11_HPHMI/NotchingSlitting_Overview", u"page": u"/sanand/zone-e/lasernotching/cathode-line-1/ntc11-overview", u"openPage": True},
			{u"unitId": u"NTC12", u"folder": u"IN11_E123_PCE_NTC12", u"description": u"Cathode notching 12", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"Telemetry/LNT001/BGA001/SpeedPV", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Laser temp. DS", u"tl": u"Laser DS", u"path": u"Telemetry/LNT001/BTA001/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Fume air vel.", u"tl": u"Fume air", u"path": u"Telemetry/LNT001/BFA001/PV", u"unit": u"m/s", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Laser temp. OS", u"tl": u"Laser OS", u"path": u"Telemetry/LNT001/BTA002/PV", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Unwind tension", u"tl": u"Unwind T.", u"path": u"Telemetry/UWD001/IFD001/WT001/PV", u"unit": u"N", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Suction press.", u"tl": u"Suction press.", u"path": u"Telemetry/LNT001/PIT003/PV", u"unit": u"kPa", u"fmt": u"#,##0.00", u"kind": u"value"}, {u"label": u"Slitter feed roll", u"tl": u"Slitter feed roll", u"path": u"Telemetry/SLT001/GLC001/MAA001/MotorSpeedPV", u"unit": u"rpm", u"fmt": u"#,##0", u"kind": u"value"}], u"drives": [], u"speed": True, u"sim": False, u"kind": u"", u"tile": 3, u"tileWide": 4, u"faceplate": u"NTC11_HPHMI/NotchingSlitting_Overview", u"page": u"/sanand/zone-e/lasernotching/cathode-line-1/ntc11-overview", u"openPage": False}],
		 "planned": [],
		 "summary": None},
		u"CL2": {"units": [],
		 "planned": [{u"unitId": u"CNOT201", u"description": u"Cathode notching L2 #1 \u2013 not connected", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Laser temp. DS", u"tl": u"Laser DS", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}, {u"unitId": u"CNOT202", u"description": u"Cathode notching L2 #2 \u2013 not connected", u"keyValues": [{u"label": u"Line speed", u"tl": u"Speed", u"path": u"-", u"unit": u"m/min", u"fmt": u"#,##0.0", u"kind": u"value"}, {u"label": u"Laser temp. DS", u"tl": u"Laser DS", u"path": u"-", u"unit": u"\u00b0C", u"fmt": u"#,##0.0", u"kind": u"value"}]}],
		 "summary": None}}}
]

TILE_H = 96
TILE_MIN_W = 124
STATE_TEXT = {"running": u"Running", "stopped": u"Stopped", "starved": u"Starved \u2013 no input", "blocked": u"Blocked \u2013 output",
	"oos": u"Out of service", "na": u"Not available", "nocomm": u"No comm \u00b7 bad quality"}
SEVERITY_NAMES = ["Severity"]
DESC_NAMES = ["Alarm Description"]
RANK = {"none": -1, "Info": 0, "Advisory": 1, "Warning": 2, "Critical": 3}


# ------------------------------------------------------------------ helpers
def _allUnits():
	for a in AREAS:
		for l in LANES:
			for u in a["cells"][l["id"]]["units"]:
				yield a, l, u


def _find(tagRoot):
	folder = str(tagRoot).replace(PROVIDER, "")
	for a, l, u in _allUnits():
		if u["folder"] == folder:
			return a, l, u
	return None, None, None


def _assoc(ev, names):
	"""associated-data value from the alarm event or its active data; '' when missing (never raises)"""
	for src in (ev, ev.getActiveData()):
		if src is None:
			continue
		try:
			for p in src.getProperties():
				if str(p.getName()) in names:
					v = src.get(p)
					return "" if v is None else v
		except:
			pass
	return ""


def _alarmClass(severity, priority):
	"""Severity 5 HSE / 4 Trip -> Critical, 3 -> Warning, 2 -> Advisory, 1 -> Info; falls back to priority (P1..P4 or Ignition)"""
	try:
		sev = int(float(str(severity)))
	except:
		sev = None
	if sev is not None and sev > 0:
		return {5: "Critical", 4: "Critical", 3: "Warning", 2: "Advisory"}.get(sev, "Info"), sev
	cls = {"P1": "Critical", "P2": "Warning", "P3": "Advisory", "P4": "Info", "Critical": "Critical", "High": "Critical",
		"Medium": "Warning", "Low": "Advisory"}.get(str(priority).strip(), "Info")
	return cls, {"Critical": 4, "Warning": 3, "Advisory": 2}.get(cls, 1)


def _worse(a, b):
	return a if RANK.get(a, -1) >= RANK.get(b, -1) else b


def _toMillis(ts):
	"""Date / long / ISO-8601 string -> epoch ms (0 when unknown, never raises)"""
	try:
		if ts is None or ts == "":
			return 0
		if hasattr(ts, "getTime"):
			return long(ts.getTime())
		if isinstance(ts, (int, long, float)):
			return long(ts)
		from java.time import Instant
		return long(Instant.parse(unicode(ts).strip()).toEpochMilli())
	except:
		return 0


def _fmtTime(ms):
	return system.date.format(system.date.fromMillis(ms), "dd-MMM HH:mm:ss") if ms else u"\u2014"


def _bool(v):
	return str(v).strip().lower() in ("true", "1", "yes")


def _num(v):
	try:
		return str(int(float(str(v))))
	except:
		return str(v or "").strip()


def _get(d, *names):
	try:
		for n in names:
			if n in d and d[n] is not None:
				return d[n]
	except:
		pass
	return None


def _loadLookup():
	"""SCADA_Config/AlarmLookup -> ({AlarmID: row}, {FBSSource: row})"""
	byId, byFbs = {}, {}
	try:
		ds = system.tag.readBlocking([LOOKUP_TAG])[0].value
		cols = list(ds.getColumnNames())
		for r in range(ds.getRowCount()):
			rec = dict((c, ds.getValueAt(r, c)) for c in cols)
			byId[str(rec.get("AlarmID", "")).strip()] = rec
			if rec.get("FBSSource"):
				byFbs[str(rec.get("FBSSource")).strip()] = rec
	except:
		pass
	return byId, byFbs


def _plcEntries(qv):
	"""CurrentAlarms document (JSON array, or wrapper object) -> list of entries; [] when bad quality / empty"""
	try:
		if not qv.quality.isGood() or qv.value is None:
			return []
		v = qv.value
		if not isinstance(v, (list, tuple, dict)):
			txt = unicode(v).strip()
			if not txt:
				return []
			v = system.util.jsonDecode(txt)
		if isinstance(v, dict):
			for k in v.keys():
				if isinstance(v[k], (list, tuple)):
					return list(v[k])
			return [v]
		return list(v or [])
	except:
		return []


def _plcAlarms(a, u, qv, lookup):
	"""machine alarms from the PLC document of one unit"""
	byId, byFbs = lookup
	out = []
	for e in _plcEntries(qv):
		grp, code = _num(_get(e, "AlarmGroupID", "AlarmGroupId")), _num(_get(e, "AlarmCode"))
		if grp in ("", "0") and code in ("", "0"):
			continue                                   # empty slot
		active, acked = _bool(_get(e, "Active", "ActiveStatus")), _bool(_get(e, "Acknowledged", "Acked"))
		if not active and acked:
			continue                                   # cleared and acknowledged
		fbs = unicode(_get(e, "FBSSource", "FBS Source") or "").strip()
		rec = byId.get("%s.%s" % (grp, code)) or byFbs.get(fbs) or {}
		cls, sev = _alarmClass(_get(e, "Severity") or rec.get("Severity"), _get(e, "Priority") or rec.get("Priority"))
		desc = unicode(rec.get("AlarmDescription") or rec.get("Label") or (u"Alarm %s.%s %s" % (grp, code, fbs))).strip()
		ms = _toMillis(_get(e, "TimestampActive"))
		out.append({"ms": ms, "time": _fmtTime(ms), "area": a["short"], "unit": u["unitId"], "tagRoot": PROVIDER + u["folder"],
			"sev": sev, "cls": cls, "desc": desc, "source": u"PLC", "unacked": not acked,
			"state": (u"Active" if active else u"Cleared") + (u" \u00b7 Unacked" if not acked else u" \u00b7 Acked")})
	return out


def _ignitionAlarms():
	"""Ignition alarms (tag alarms configured on the gateway), mapped to units by source path"""
	rows = []
	try:
		events = system.alarm.queryStatus(state=["ActiveUnacked", "ActiveAcked"])
	except:
		return rows
	for ev in events:
		cls, sev = _alarmClass(_assoc(ev, SEVERITY_NAMES), ev.getPriority())
		desc = _assoc(ev, DESC_NAMES) or ev.getLabel() or ev.getName()
		try:
			ms = _toMillis(ev.getActiveData().getTimestamp())
		except:
			ms = 0
		source = str(ev.getSource())
		a, unit, root = None, u"Gateway", ""
		for a_, l_, u_ in _allUnits():
			if u_["folder"] in source:
				a, unit, root = a_, u_["unitId"], PROVIDER + u_["folder"]
				break
		unacked = "Unacked" in str(ev.getState())
		rows.append({"ms": ms, "time": _fmtTime(ms), "area": a["short"] if a else u"Zone E", "unit": unit, "tagRoot": root,
			"sev": sev, "cls": cls, "desc": unicode(desc), "source": u"Ignition", "unacked": unacked,
			"state": u"Active \u00b7 " + (u"Unacked" if unacked else u"Acked"), "folderSource": source})
	return rows


def _stateKey(stateQv, starvedQv, blockedQv):
	"""same rule as the EquipmentTile view: bad quality is never shown as a live state"""
	if not stateQv.quality.isGood() or stateQv.value is None:
		return "nocomm"
	state = int(stateQv.value)
	blocked = blockedQv.quality.isGood() and bool(blockedQv.value)
	starved = starvedQv.quality.isGood() and bool(starvedQv.value)
	if state in (2, 3):
		if blocked:
			return "blocked"
		if starved:
			return "starved"
		return "running" if state == 3 else "stopped"
	return {1: "oos", 0: "na"}.get(state, "nocomm")


def _kvRows(u, limit=None, short=False):
	rows = u["keyValues"] if limit is None else u["keyValues"][:limit]
	return [{"tagRoot": PROVIDER + u["folder"], "label": k["tl"] if short else k["label"], "path": k["path"], "unit": k["unit"], "fmt": k["fmt"], "kind": k["kind"]} for k in rows]


def _empty():
	return {"total": 0, "running": 0, "stopped": 0, "starved": 0, "blocked": 0, "oos": 0, "na": 0, "nocomm": 0}


def _sortAlarms(rows):
	rows.sort(key=lambda r: (-r["sev"], -r["ms"]))
	return rows


# ------------------------------------------------------------------ main model
def buildModel(width=1920):
	wide = (width or 0) >= WIDE_PX
	units = list(_allUnits())
	paths, spans = [], []
	for a, l, u in units:
		root = PROVIDER + u["folder"] + "/"
		start = len(paths)
		paths += [root + "AGStatus/CurrentState", root + "AGStatus/EquipmentStarved", root + "AGStatus/EquipmentBlocked",
			root + "AGStatus/MESRunning", root + ALARM_DOC]
		paths += [root + p for p in u["drives"]]
		spans.append((start, len(paths)))
	values = system.tag.readBlocking(paths) if paths else []
	lookup = _loadLookup()
	ignition = _ignitionAlarms()

	info, allAlarms, mesOn = {}, [], 0
	for (a, l, u), (s, e) in zip(units, spans):
		v = values[s:e]
		key = _stateKey(v[0], v[1], v[2])
		if v[3].quality.isGood() and bool(v[3].value):
			mesOn += 1
		drv = [(bool(q.value) if q.quality.isGood() and q.value is not None else None) for q in v[5:]]
		alarms = _plcAlarms(a, u, v[4], lookup) + [r for r in ignition if u["folder"] in r["folderSource"]]
		_sortAlarms(alarms)
		worst = "none"
		for r in alarms:
			worst = _worse(r["cls"], worst)
		info[u["folder"]] = {"key": key, "drv": drv, "alarms": alarms, "worst": worst}
		allAlarms += alarms
	allAlarms += [r for r in ignition if not r["tagRoot"]]          # gateway alarms (e.g. PLC communication)
	_sortAlarms(allAlarms)

	# ---- process headers: 2 KPIs per process (running, alarms) + state bar
	steps = []
	for a in AREAS:
		c = _empty()
		al = {"count": 0, "worst": "none"}
		planned = 0
		for l in LANES:
			cell = a["cells"][l["id"]]
			planned += len(cell["planned"])
			for u in cell["units"]:
				i = info[u["folder"]]
				c["total"] += 1
				c[i["key"]] += 1
				al["count"] += len(i["alarms"])
				al["worst"] = _worse(i["worst"], al["worst"])
		total = c["total"]
		stopped = c["stopped"] + c["oos"] + c["na"]
		pct = lambda n: ("%.2f%%" % (100.0 * n / total)) if total else "0%"
		steps.append({"step": a["step"], "title": a["title"], "page": a["page"], "connected": total > 0,
			"running": c["running"], "total": total, "runningText": u"%d / %d" % (c["running"], total), "planned": planned,
			"countsText": u"Not connected \u2013 no PLC signals" if not total else u"",
			"alarm": al, "nocomm": c["nocomm"],
			"bar": {"run": pct(c["running"]), "wait": pct(c["starved"] + c["blocked"]), "stop": pct(stopped), "nocomm": pct(c["nocomm"]) if total else "100%"}})

	# ---- matrix rows (lanes) x cells (areas): one tile per equipment position
	rows = []
	for l in LANES:
		cells = []
		for a in AREAS:
			cell = a["cells"][l["id"]]
			tiles = []
			for u in cell["units"]:
				i = info[u["folder"]]
				known = [d for d in i["drv"] if d is not None]
				showDrives = bool(u["drives"]) and len(u["keyValues"]) < 2
				tiles.append({"tagRoot": PROVIDER + u["folder"], "unitId": u["unitId"], "description": u["description"], "planned": False,
					"keyValues": _kvRows(u, 1 if showDrives else 2, True), "showDrives": showDrives,
					"drivesText": (u"%d / %d" % (len([d for d in known if d]), len(u["drives"]))) if known else (u"\u2014 / %d" % len(u["drives"])),
					"alarmCount": len(i["alarms"]), "alarmClass": i["worst"],
					"alarmText": i["alarms"][0]["desc"] if i["alarms"] else u"",
					"instancePosition": {"basis": "%dpx" % TILE_MIN_W, "grow": 1, "shrink": 0},
					"instanceStyle": {"height": "%dpx" % TILE_H, "classes": ""}})
			for p in cell["planned"]:
				tiles.append({"tagRoot": "", "unitId": p["unitId"], "description": p["description"], "planned": True,
					"keyValues": [{"tagRoot": "", "label": k["tl"], "path": "-", "unit": k["unit"], "fmt": k["fmt"], "kind": k["kind"]} for k in p["keyValues"]],
					"showDrives": False, "drivesText": u"", "alarmCount": 0, "alarmClass": "none", "alarmText": u"",
					"instancePosition": {"basis": "%dpx" % TILE_MIN_W, "grow": 1, "shrink": 0},
					"instanceStyle": {"height": "%dpx" % TILE_H, "classes": ""}})
			cells.append({"tiles": tiles, "tileCount": len(tiles)})
		rows.append({"side": l["side"].upper(), "line": l["line"], "cells": cells})

	totals = _empty()
	for a, l, u in units:
		totals["total"] += 1
		totals[info[u["folder"]]["key"]] += 1
	bySev = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
	worst = "none"
	for r in allAlarms:
		bySev[str(r["sev"]) if r["sev"] in (1, 2, 3, 4, 5) else "1"] += 1
		worst = _worse(r["cls"], worst)
	alarmRows = [dict((k, v) for k, v in r.items() if k != "folderSource") for r in allAlarms[:MAX_ALARM_ROWS]]
	return {"steps": steps, "rows": rows, "totals": totals, "alarmRows": alarmRows,
		"alarms": {"active": len(allAlarms), "unacked": len([r for r in allAlarms if r["unacked"]]), "worst": worst, "bySeverity": bySev,
			"shown": len(alarmRows)},
		"mesOn": mesOn, "wide": wide, "ok": True}


# ------------------------------------------------------------------ popup data
def unitAlarms(tagRoot):
	a, l, u = _find(tagRoot)
	if u is None:
		return {"rows": [], "count": 0, "worst": "none"}
	qv = system.tag.readBlocking([PROVIDER + u["folder"] + "/" + ALARM_DOC])[0]
	rows = _sortAlarms(_plcAlarms(a, u, qv, _loadLookup()) + [r for r in _ignitionAlarms() if u["folder"] in r["folderSource"]])
	worst = "none"
	for r in rows:
		worst = _worse(r["cls"], worst)
	return {"rows": [{"time": r["time"], "desc": r["desc"], "sev": r["sev"], "cls": r["cls"], "state": r["state"]} for r in rows],
		"count": len(rows), "worst": worst}


def driveStates(tagRoot):
	a, l, u = _find(tagRoot)
	if u is None or not u["drives"]:
		return {"text": "", "count": 0, "on": 0}
	values = system.tag.readBlocking([PROVIDER + u["folder"] + "/" + p for p in u["drives"]])
	parts, on = [], 0
	for p, q in zip(u["drives"], values):
		name = p.split("/")[-2]
		if not q.quality.isGood() or q.value is None:
			parts.append(u"? " + name)
		elif q.value:
			on += 1
			parts.append(u"\u25b6 " + name)
		else:
			parts.append(u"\u25a0 " + name)
	return {"text": u"     ".join(parts), "count": len(parts), "on": on}


def equipmentList(filter="all"):
	units = list(_allUnits())
	paths = []
	for a, l, u in units:
		root = PROVIDER + u["folder"] + "/AGStatus/"
		paths += [root + "CurrentState", root + "EquipmentStarved", root + "EquipmentBlocked"]
	values = system.tag.readBlocking(paths)
	model = buildModel()
	counts = {}
	for r in model["alarmRows"]:
		counts[r["tagRoot"]] = counts.get(r["tagRoot"], 0) + 1
	rows = []
	for n, (a, l, u) in enumerate(units):
		key = _stateKey(values[3 * n], values[3 * n + 1], values[3 * n + 2])
		count = counts.get(PROVIDER + u["folder"], 0)
		if filter == "abnormal" and key == "running" and not count:
			continue
		if filter == "nocomm" and key != "nocomm":
			continue
		rows.append({"tagRoot": PROVIDER + u["folder"], "area": a["short"], "line": u"%s L%s" % (l["side"], l["line"][-1]), "unitId": u["unitId"],
			"description": u["description"], "alarmCount": count, "sim": False, "planned": False})
	if filter == "all":
		for a in AREAS:
			for l in LANES:
				for p in a["cells"][l["id"]]["planned"]:
					rows.append({"tagRoot": "", "area": a["short"], "line": u"%s L%s" % (l["side"], l["line"][-1]), "unitId": p["unitId"],
						"description": u"Not connected \u2013 no PLC signals yet", "alarmCount": 0, "sim": False, "planned": True})
	return {"rows": rows, "count": len(rows)}


# ------------------------------------------------------------------ popup / navigation helpers (call from Perspective events)
def openQuickView(tagRoot):
	a, l, u = _find(tagRoot)
	if u is None:
		return
	params = {"tagRoot": PROVIDER + u["folder"], "unitId": u["unitId"], "description": u["description"], "areaTitle": a["title"],
		"keyValues": _kvRows(u), "kvRows": (len(u["keyValues"]) + 1) // 2, "hasDrives": bool(u["drives"]), "areaPage": a["page"],
		"sim": False, "hasFaceplate": bool(u["faceplate"]) or bool(u.get("openPage"))}
	system.perspective.openPopup(POPUP_QUICKVIEW, "Popups/HPHMI/EquipmentQuickView", params=params,
		title=u"%s  \u00b7  %s  \u00b7  %s  \u00b7  %s %s" % (u["unitId"], u["description"], a["title"], l["side"], l["line"]),
		position={"width": 840, "height": 680}, showCloseIcon=True, draggable=True, resizable=True, modal=True, overlayDismiss=True, viewportBound=True)


def openFaceplate(tagRoot):
	"""existing HPHMI faceplate or area screen for the unit (configured per unit in the model)"""
	a, l, u = _find(tagRoot)
	if u is None:
		return
	system.perspective.closePopup(POPUP_QUICKVIEW)
	if u.get("openPage"):
		system.perspective.navigate(page=u["page"])
	elif u["faceplate"]:
		system.perspective.openPopup("hphmiFaceplate", u["faceplate"],
			params={"tagRoot": PROVIDER + u["folder"], "provider": PROVIDER, "lookupTag": LOOKUP_TAG},
			title=u"%s \u00b7 %s" % (u["unitId"], u["description"]), showCloseIcon=True, draggable=True, resizable=True,
			modal=False, viewportBound=True)


def openAreaScreen(page):
	system.perspective.closePopup(POPUP_QUICKVIEW)
	if page:
		system.perspective.navigate(page=page)


def openEquipmentList(filter="all"):
	system.perspective.openPopup("hphmiEquipmentList", "Popups/HPHMI/EquipmentList", params={"filter": filter},
		title=u"Zone E equipment", position={"width": 1220, "height": 740}, showCloseIcon=True, draggable=True,
		resizable=True, modal=True, overlayDismiss=True, viewportBound=True)
