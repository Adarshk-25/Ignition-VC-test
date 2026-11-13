# HPHMI_ZoneE  -  project script library (Ignition 8.x, Jython 2.7)
# Data model for the high-performance "Zone E Overview" (Zone E/Zone E Overview).
#   buildModel()  -> one poll per session (bound to now(3000) on the view) that returns
#                    areas (with equipment cards), equipment counts and the alarm summary.
# Equipment cards read their own AGStatus tags live; this poll only produces counts and alarm badges.
# To add / remove equipment, edit AREAS below (generated from hmi_build/build.js).

PROVIDER = "[default]"
LOOKUP_TAG = "[default]SCADA_Config/AlarmLookup"
SIM_ROOT = "[default]_Sim/ZoneE/"

# AGStatus/CurrentState: 0 NotAvailable, 1 OutOfService, 2 NotExecuting, 3 Executing
# AGStatus/CurrentMode : 0 None, 1 Maintenance, 2 Setup, 3 Processing
AREAS = [
	{"id": u"mixing", "step": 1, "title": u"Mixing", "page": u"/sanand/zone-e/mixing", "kpiFolder": u"Mixing",
	 "note": u"Anode mixing: no PLC signals mapped yet.",
	 "groups": [
		{"title": u"Cathode \u00b7 Mixers", "compact": False, "units": [
			{"unitId": u"MIX01", "folder": u"IN11_E115_PCE_MIX01", "description": u"Cathode mixer 01", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/MIX01"},
			{"unitId": u"MIX11", "folder": u"IN11_E115_PCE_MIX11", "description": u"Cathode mixer 11", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/MIX11"},
			{"unitId": u"MIX12", "folder": u"IN11_E115_PCE_MIX12", "description": u"Cathode mixer 12", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/MIX12"},
			{"unitId": u"MIX13", "folder": u"IN11_E115_PCE_MIX13", "description": u"Cathode mixer 13", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/MIX13"},
			{"unitId": u"MIX14", "folder": u"IN11_E115_PCE_MIX14", "description": u"Cathode mixer 14", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/MIX14"}]},
		{"title": u"Cathode \u00b7 Slurry", "compact": False, "units": [
			{"unitId": u"SLU11", "folder": u"IN11_E115_PCE_SLU11", "description": u"Slurry system 11", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/SLU11"},
			{"unitId": u"STS11", "folder": u"IN11_E115_PCE_STS11", "description": u"Slurry storage 11", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/STS11"},
			{"unitId": u"SCS11", "folder": u"IN11_E117_PCE_SCS11", "description": u"Slurry supply 11", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/SCS11"},
			{"unitId": u"SCS12", "folder": u"IN11_E119_PCE_SCS12", "description": u"Slurry supply 12", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/SCS12"}]},
		{"title": u"Cathode \u00b7 Material feed", "compact": True, "units": [
			{"unitId": u"WES11", "folder": u"IN11_E112_PCE_WES11", "description": u"Weighing system 11", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/WES11"},
			{"unitId": u"LIQ11", "folder": u"IN11_E205_PCE_LIQ11", "description": u"Liquid dosing 11", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/LIQ11"},
			{"unitId": u"LIQ12", "folder": u"IN11_E112_PCE_LIQ12", "description": u"Liquid dosing 12", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/LIQ12"},
			{"unitId": u"CNT11", "folder": u"IN11_E205_PCE_CNT11", "description": u"CNT dosing 11", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/CNT11"},
			{"unitId": u"DSS11", "folder": u"IN11_E205_PCE_DSS11", "description": u"Dosing system 11", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/DSS11"},
			{"unitId": u"CMS11", "folder": u"IN11_E305_PCE_CMS11", "description": u"CMS 11", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/CMS11"},
			{"unitId": u"CMS12", "folder": u"IN11_E305_PCE_CMS12", "description": u"CMS 12", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/CMS12"},
			{"unitId": u"CRS11", "folder": u"IN11_E305_PCE_CRS11", "description": u"CRS 11", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/CRS11"},
			{"unitId": u"POW11", "folder": u"IN11_E305_PCE_POW11", "description": u"Powder system 11", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/POW11"},
			{"unitId": u"PVS11", "folder": u"IN11_E305_PCE_PVS11", "description": u"PVS 11", "showSpeed": False, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"MIX11_HPHMI/Faceplates/PVS11"}]}]},
	{"id": u"coating", "step": 2, "title": u"Coating & Recovery", "page": u"", "kpiFolder": u"Coating",
	 "note": u"No PLC signals are mapped for Coating & Recovery yet (ACOAT / CCOAT / ARECV / CRECV). Equipment cards appear here once the tags exist.",
	 "groups": []},
	{"id": u"calendering", "step": 3, "title": u"Calendering", "page": u"/sanand/zone-e/calendering", "kpiFolder": u"Calendering",
	 "note": u"Anode calendering: no PLC signals mapped yet.",
	 "groups": [
		{"title": u"Cathode", "compact": False, "units": [
			{"unitId": u"CLD11", "folder": u"IN11_E122_PCE_CLD11", "description": u"Cathode calender 11", "showSpeed": True, "speedUnit": u"m/min", "actionType": u"page", "actionTarget": u"/sanand/zone-e/calendering"}]}]},
	{"id": u"notching", "step": 4, "title": u"Notching & Slitting", "page": u"/sanand/zone-e/lasernotching/cathode-line-1/ntc11-overview", "kpiFolder": u"Notching",
	 "note": u"",
	 "groups": [
		{"title": u"Cathode", "compact": False, "units": [
			{"unitId": u"NTC11", "folder": u"IN11_E123_PCE_NTC11", "description": u"Cathode notching 11", "showSpeed": True, "speedUnit": u"m/min", "actionType": u"page", "actionTarget": u"/sanand/zone-e/lasernotching/cathode-line-1/ntc11-overview"},
			{"unitId": u"NTC12", "folder": u"IN11_E123_PCE_NTC12", "description": u"Cathode notching 12", "showSpeed": True, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"NTC11_HPHMI/NotchingSlitting_Overview"}]},
		{"title": u"Anode", "compact": False, "units": [
			{"unitId": u"NTC11", "folder": u"IN11_E155_PAE_NTC11", "description": u"Anode notching 11", "showSpeed": True, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"NTC11_HPHMI/NotchingSlitting_Overview"},
			{"unitId": u"NTC12", "folder": u"IN11_E155_PAE_NTC12", "description": u"Anode notching 12", "showSpeed": True, "speedUnit": u"m/min", "actionType": u"popup", "actionTarget": u"NTC11_HPHMI/NotchingSlitting_Overview"}]}]}
]

# alarm associated-data names used on this gateway (see NTC11_Alarms.ASSOC)
SEVERITY_NAMES = ["Severity"]
# alarm class rank: shape + colour on the screen  (Critical=octagon red, Warning=triangle amber, Advisory=circle yellow)
RANK = {"none": -1, "Info": 0, "Advisory": 1, "Warning": 2, "Critical": 3}


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
	"""Severity 5 HSE / 4 Trip -> Critical, 3 -> Warning, 2 -> Advisory, 1 -> Info; falls back to priority"""
	try:
		sev = int(float(str(severity)))
	except:
		sev = None
	if sev is not None:
		return {5: "Critical", 4: "Critical", 3: "Warning", 2: "Advisory"}.get(sev, "Info"), sev
	return {"Critical": "Critical", "High": "Critical", "Medium": "Warning", "Low": "Advisory"}.get(str(priority), "Info"), None


def _worse(a, b):
	return a if RANK.get(a, -1) >= RANK.get(b, -1) else b


def _alarms(folders):
	"""active alarm summary: totals, count per severity and per unit folder"""
	res = {"active": 0, "unacked": 0, "worst": "none",
		"bySeverity": {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0},
		"byFolder": dict((f, {"count": 0, "worst": "none"}) for f in folders)}
	try:
		events = system.alarm.queryStatus(state=["ActiveUnacked", "ActiveAcked"])
	except:
		return res
	for ev in events:
		cls, sev = _alarmClass(_assoc(ev, SEVERITY_NAMES), ev.getPriority())
		res["active"] += 1
		if "Unacked" in str(ev.getState()):
			res["unacked"] += 1
		res["worst"] = _worse(cls, res["worst"])
		key = str(sev) if sev in (1, 2, 3, 4, 5) else {"Critical": "4", "Warning": "3", "Advisory": "2"}.get(cls, "1")
		res["bySeverity"][key] += 1
		source = str(ev.getSource())
		for f in folders:
			if f in source:
				res["byFolder"][f]["count"] += 1
				res["byFolder"][f]["worst"] = _worse(cls, res["byFolder"][f]["worst"])
	return res


def _stateKey(stateQv, starvedQv, blockedQv):
	"""same rule as the EquipmentCard view: bad quality is never shown as a live state"""
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


def _countsText(c):
	if c["total"] == 0:
		return "No units mapped"
	parts = ["%d running" % c["running"]]
	for key, text in (("stopped", "stopped"), ("starved", "starved"), ("blocked", "blocked"), ("oos", "out of service"), ("na", "not available"), ("nocomm", "no comm")):
		if c[key]:
			parts.append("%d %s" % (c[key], text))
	return u" \u00b7 ".join(parts) + "  (of %d)" % c["total"]


def buildModel():
	units = [u for a in AREAS for g in a["groups"] for u in g["units"]]
	paths = []
	for u in units:
		root = PROVIDER + u["folder"] + "/AGStatus/"
		paths += [root + "CurrentState", root + "EquipmentStarved", root + "EquipmentBlocked"]
	values = system.tag.readBlocking(paths) if paths else []
	alarms = _alarms([u["folder"] for u in units])

	keys = {}
	for i, u in enumerate(units):
		keys[u["folder"]] = _stateKey(values[3 * i], values[3 * i + 1], values[3 * i + 2])

	empty = lambda: {"total": 0, "running": 0, "stopped": 0, "starved": 0, "blocked": 0, "oos": 0, "na": 0, "nocomm": 0}
	totals = empty()
	areas = []
	for a in AREAS:
		counts = empty()
		areaAlarm = {"count": 0, "worst": "none"}
		groups = []
		for g in a["groups"]:
			cards = []
			for u in g["units"]:
				k = keys[u["folder"]]
				counts["total"] += 1
				counts[k] += 1
				al = alarms["byFolder"][u["folder"]]
				areaAlarm["count"] += al["count"]
				areaAlarm["worst"] = _worse(al["worst"], areaAlarm["worst"])
				cards.append({"tagRoot": PROVIDER + u["folder"], "unitId": u["unitId"], "description": u["description"],
					"showSpeed": u["showSpeed"], "speedUnit": u["speedUnit"],
					"alarmCount": al["count"], "alarmClass": al["worst"],
					"actionType": u["actionType"], "actionTarget": u["actionTarget"], "lookupTag": LOOKUP_TAG})
			groups.append({"title": g["title"], "compact": g["compact"], "units": cards})
		groupCount = len(groups)
		while len(groups) < 3:   # the AreaPanel has 3 fixed group slots
			groups.append({"title": "", "compact": False, "units": []})
		for key in totals:
			totals[key] += counts[key]
		areas.append({"id": a["id"], "step": a["step"], "title": a["title"], "page": a["page"], "note": a["note"],
			"oeeTag": SIM_ROOT + a["kpiFolder"] + "/OEE", "downtimeTag": SIM_ROOT + a["kpiFolder"] + "/DowntimeMin",
			"countsText": _countsText(counts), "groupCount": groupCount, "alarm": areaAlarm, "groups": groups})

	summary = dict((k, v) for k, v in alarms.items() if k != "byFolder")
	return {"areas": areas, "totals": totals, "alarms": summary, "ok": True}
