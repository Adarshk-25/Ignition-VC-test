# NTC11_Alarms  -  project script library (Ignition 8.1, Jython 2.7)
# Shared alarm logic for the NTC11 overview and equipment faceplates:
#   * per-equipment alarm state  -> ACTIVE_UNACKED (blink) / ACTIVE_ACKED (solid red) / CLEARED_UNACKED (blink) / NORMAL
#   * latest alarms joined with the central lookup table (Excel "Alarm List mapping file")
# Call from bindings:  NTC11_Alarms.poll(tagRoot, lookupTag)  or  NTC11_Alarms.poll(tagRoot, lookupTag, "LNT001", 50)

# associated-data names on the alarm configuration (edit here if the alarm configuration uses other names)
ASSOC = {"group": ["Alarm Group Id", "Alarm GroupID", "AlarmGroupId"],
         "code": ["Alarm Code", "AlarmCode"],
         "severity": ["Severity"],
         "priority": ["Alarm Priority", "Priority"],
         "fbs": ["FBS Source", "FBSSource"]}
EQUIPMENT = ["UWD001", "LNT001", "SLT001", "RWD001", "RWD002"]
PRIORITY_COLOUR = {"Critical": "#D7262E", "High": "#D2680C", "Medium": "#9A7B00", "Low": "#8E4FC9", "Diagnostic": "#3C86C6"}
SEVERITY_TEXT = {"1": "EVENT", "2": "WARNING", "3": "ALARM", "4": "TRIP", "5": "HSE HAZARD"}


def _prop(ev, names):
	"""read an alarm property / associated-data value; '' when missing (never raises)"""
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


def _ms(data):
	try:
		if data is None:
			return 0
		t = data.getTimestamp()
		return t.getTime() if hasattr(t, "getTime") else long(t)
	except:
		return 0


def _fmt(m):
	return system.date.format(system.date.fromMillis(m), "dd-MMM HH:mm:ss") if m else ""


def _num(v):
	try:
		return str(int(float(str(v))))
	except:
		return str(v or "").strip()


def loadLookup(lookupTag):
	"""dataset tag -> {AlarmID: row}, {FBSSource: row}"""
	byId, byFbs = {}, {}
	try:
		ds = system.tag.readBlocking([lookupTag])[0].value
		cols = list(ds.getColumnNames())
		for r in range(ds.getRowCount()):
			rec = dict((c, ds.getValueAt(r, c)) for c in cols)
			byId[str(rec.get("AlarmID", "")).strip()] = rec
			if rec.get("FBSSource"):
				byFbs[str(rec.get("FBSSource")).strip()] = rec
	except:
		pass
	return byId, byFbs


def equipmentOf(fbs, sourcePath):
	for e in EQUIPMENT:
		if e in fbs or e in sourcePath:
			return e
	return ""


def poll(tagRoot, lookupTag, equipment=None, maxRows=5):
	"""returns {"rows": [...table rows...], "eq": {EQ: {"active", "unacked", "state", "count"}}}"""
	result = {"rows": [], "eq": dict((e, {"active": False, "unacked": False, "state": "NORMAL", "count": 0}) for e in EQUIPMENT)}
	try:
		root = str(tagRoot or "")
		srcFilter = "*" + root.split("]")[-1] + "*"
		events = system.alarm.queryStatus(source=[srcFilter], state=["ActiveUnacked", "ActiveAcked", "ClearUnacked"])
	except:
		events = []
	byId, byFbs = loadLookup(lookupTag)
	recs = []
	for ev in events:
		try:
			grp = _num(_prop(ev, ASSOC["group"])); code = _num(_prop(ev, ASSOC["code"]))
			fbs = str(_prop(ev, ASSOC["fbs"]) or "")
			eq = equipmentOf(fbs, str(ev.getSource()))
			active = not ev.isCleared(); acked = ev.isAcked()
			if eq:
				st = result["eq"][eq]
				st["count"] += 1
				if active:
					st["active"] = True
				if not acked:
					st["unacked"] = True
			if equipment and eq != equipment:
				continue
			alarmId = "%s.%s" % (grp, code)
			lk = byId.get(alarmId) or byFbs.get(fbs) or {}
			recs.append((_ms(ev.getActiveData()), ev, grp, code, fbs, active, acked, alarmId, lk))
		except:
			pass
	# equipment border state: blinking while anything is unacknowledged, solid while active & acknowledged
	for e, st in result["eq"].items():
		if st["unacked"]:
			st["state"] = "ACTIVE_UNACKED" if st["active"] else "CLEARED_UNACKED"
		elif st["active"]:
			st["state"] = "ACTIVE_ACKED"
	recs.sort(key=lambda x: x[0], reverse=True)
	for tAct, ev, grp, code, fbs, active, acked, alarmId, lk in recs[:int(maxRows)]:
		prio = str(_prop(ev, ASSOC["priority"]) or lk.get("Priority") or ev.getPriority())
		sev = _num(lk.get("Severity") or _prop(ev, ASSOC["severity"]))
		colour = PRIORITY_COLOUR.get(str(ev.getPriority()), "#262626")
		style = {"color": colour, "fontWeight": "bold"} if not acked else {"color": "#262626"}
		def cell(v):
			return {"value": v, "style": style}
		missing = "(no entry in alarm list)"
		result["rows"].append({
			"eventId": str(ev.getId()),
			"TimestampActive": cell(_fmt(tAct)),
			"TimestampReset": cell(_fmt(_ms(ev.getClearedData())) if not active else ""),
			"AlarmGroupId": cell(grp), "AlarmCode": cell(code),
			"Severity": cell(SEVERITY_TEXT.get(sev, sev)),
			"Priority": cell(prio),
			"FBSSource": cell(str(lk.get("FBSSource") or fbs)),
			"Label": cell(str(lk.get("Label") or ev.getName() or "")),
			"Description": cell(str(lk.get("AlarmDescription") or ev.getDisplayPath() or "")),
			"OperatorMessage": cell(str(lk.get("OperatorMessage") or missing)),
			"Troubleshooting": cell(str(lk.get("Troubleshooting") or missing)),
			"ActiveStatus": cell("ACTIVE" if active else "CLEARED"),
			"Acknowledged": cell("YES" if acked else "NO")})
	return result


def acknowledge(eventIds, note="Acknowledged from NTC11 SCADA"):
	ids = [str(i) for i in (eventIds or []) if i]
	if ids:
		system.alarm.acknowledge(ids, note)
	return len(ids)


def reloadLookupFromCsv(csvPath, lookupTag="[default]SCADA_Config/AlarmLookup"):
	"""re-load the central lookup from a CSV export of the Excel 'Alarm List' sheet (first row = column names)"""
	text = system.file.readFileAsString(csvPath, "UTF-8")
	ds = system.dataset.fromCSV(text) if text.startswith("#NAMES") else _csvToDataset(text)
	system.tag.writeBlocking([lookupTag], [ds])
	return ds.getRowCount()


def _csvToDataset(text):
	import csv, StringIO
	rows = list(csv.reader(StringIO.StringIO(text.encode("utf-8"))))
	header = rows[0]
	data = [[unicode(c, "utf-8") for c in r] + [""] * (len(header) - len(r)) for r in rows[1:] if any(r)]
	return system.dataset.toDataSet(header, data)
