# MIX11_Alarms  -  project script library (Ignition 8.1, Jython 2.7)
# Mixing - Cathode Line 1 (supplier Yunsung).  One overview, many nodesets: every nodeset (OPC UA FBS unit, e.g.
# [default]IN11_E115_PCE_MIX11) has its own AGStatus, AGAdmin/CurrentAlarms and Telemetry.
# Alarms of every nodeset are merged from TWO sources (as NTC11 V8):
#   (1) the PLC Document tag <nodeset>/AGAdmin/CurrentAlarms (JSON array, one entry per alarm slot):
#       {"AlarmGroupID": 9, "AlarmCode": 1, "Severity": 4, "TimestampActive": "...Z", "TimestampReset": "...Z",
#        "Active": true, "FBSSource": "MIX11.UCA025.QAB01", "Acknowledged": false, "Priority": "P1"}
#       empty slots (GroupID 0 and Code 0) are ignored; Active=false + Acknowledged=true -> gone; the PLC acknowledges
#   (2) Ignition alarms configured on tags under the nodeset (system.alarm.queryStatus)
# Lookup ([default]SCADA_Config/AlarmLookup, column Line = nodeset code e.g. MIX11 / SLU11 / CMS12) adds Label,
# Description, Operator Message and Troubleshooting from the supplier alarm lists (C1_*_Alarm_List_260903.xlsx).
# Station of an alarm = first segment of its FBS Source (MIX11.UCA025.QAB01 -> MIX11; GPA11 in the path -> GPA11),
# otherwise the nodeset it came from.
# Severity (1 Event .. 5 HSE) -> Alarm Severity Visual Matrix for table rows and station borders (BORDER_MODE).
#
# Bindings:
#   view.custom.alarmInfo <- now(2000) + transform  MIX11_Alarms.poll(provider, lookupTag [, "MIX11", 50])
#   AlarmTable.props.data <- view.custom.blink + transform  MIX11_Alarms.styleRows(view.custom.alarmInfo.rows, value)

ALARM_DOC = "AGAdmin/CurrentAlarms"          # relative to tagRoot
# nodesets polled (tag folder names under the provider)
NODESETS = ["IN11_E305_PCE_POW11", "IN11_E305_PCE_PVS11", "IN11_E305_PCE_CRS11", "IN11_E305_PCE_CMS11", "IN11_E305_PCE_CMS12",
            "IN11_E205_PCE_LIQ11", "IN11_E205_PCE_CNT11", "IN11_E205_PCE_DSS11", "IN11_E112_PCE_WES11", "IN11_E112_PCE_LIQ12",
            "IN11_E115_PCE_MIX01", "IN11_E115_PCE_MIX11", "IN11_E115_PCE_MIX12", "IN11_E115_PCE_MIX13", "IN11_E115_PCE_MIX14",
            "IN11_E115_PCE_SLU11", "IN11_E115_PCE_STS11", "IN11_E117_PCE_SCS11", "IN11_E119_PCE_SCS12"]
# stations on the overview (nodeset codes; GPA11 = vacuum system inside the MIX11 nodeset)
EQUIPMENT = ["PVS11", "CRS11", "CMS11", "CMS12", "CNT11", "DSS11", "LIQ12", "WES11", "MIX01", "MIX11", "MIX12", "MIX13", "MIX14",
             "GPA11", "STS11", "SCS11", "SCS12", "POW11", "LIQ11", "SLU11"]
SEVERITY_TEXT = {"1": "EVENT", "2": "WARNING", "3": "ALARM", "4": "TRIP", "5": "HSE HAZARD"}
LEVEL_NAME = {5: "SAFETY CRITICAL / HSE", 4: "PRIORITY LEVEL 4", 3: "PRIORITY LEVEL 3", 2: "PRIORITY LEVEL 2", 1: "PRIORITY LEVEL 1"}
PRIORITY_LEVEL = {"P1": 4, "P2": 3, "P3": 2, "P4": 1}
IGNITION_LEVEL = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "Diagnostic": 1}

# ---------------------------------------------------------------- colours of the matrix
TEXT = "#262626"          # default table text
RED, ORANGE, YELLOW, GREY = "#FF0000", "#FF8C00", "#FFCC00", "#7F7F7F"
YELLOW_EDGE = "0 0 1px rgba(0,0,0,0.9), 0 1px 1px rgba(0,0,0,0.5)"   # keeps yellow text legible on light rows
B = {"fontWeight": "bold"}


def _st(**kw):
    d = dict(kw)
    return d


# (level, acked) -> (style while blink ON, style while blink OFF).  Equal styles = solid (no flashing).
ROW_STYLE = {
    (5, False): (_st(color="#FFFFFF", backgroundColor="#000000", fontWeight="bold"),
                 _st(color="#000000", backgroundColor="#000000", fontWeight="bold")),
    (5, True): (_st(color="#FFFFFF", backgroundColor=RED, fontWeight="bold"),) * 2,
    (4, False): (_st(color=RED, fontWeight="bold"), _st(color=TEXT, fontWeight="bold")),
    (4, True): (_st(color=RED), _st(color=TEXT)),
    (3, False): (_st(color=ORANGE, fontWeight="bold"), _st(color=TEXT, fontWeight="bold")),
    (3, True): (_st(color=ORANGE),) * 2,
    (2, False): (_st(color=YELLOW, textShadow=YELLOW_EDGE, fontWeight="bold"), _st(color=TEXT, fontWeight="bold")),
    (2, True): (_st(color=YELLOW, textShadow=YELLOW_EDGE),) * 2,
    (1, False): (_st(color=GREY),) * 2,
    (1, True): (_st(color=GREY),) * 2,
}
NO_BORDER = "0px solid transparent"
# equipment border: (ON phase, OFF phase)
BORDER = {
    (5, False): ("4px solid #000000", "4px solid #FFFFFF"),
    (5, True): ("4px solid " + RED,) * 2,
    (4, False): ("4px solid " + RED, "4px solid transparent"),
    (4, True): ("4px solid " + RED, "4px solid transparent"),
    (3, False): ("4px solid " + ORANGE, "4px solid transparent"),
    (3, True): ("4px solid " + ORANGE,) * 2,
    (2, False): ("4px solid " + YELLOW, "4px solid transparent"),
    (2, True): ("4px solid " + YELLOW,) * 2,
    (1, False): ("2px solid " + GREY,) * 2,
    (1, True): ("2px solid " + GREY,) * 2,
}
FIELDS = ["TimestampActive", "TimestampReset", "Unit", "AlarmGroupId", "AlarmCode", "Severity", "Priority", "FBSSource", "Label",
          "Description", "OperatorMessage", "Troubleshooting", "ActiveStatus", "Acknowledged"]


def emptyEq():
    return dict((e, {"active": False, "unacked": False, "state": "NORMAL", "count": 0, "level": 0, "levelName": "",
                     "borderOn": NO_BORDER, "borderOff": NO_BORDER}) for e in EQUIPMENT)


def emptyResult(error=""):
    return {"rows": [], "eq": emptyEq(), "error": error, "diag": "", "sources": {"plc": 0, "ignition": 0}}


def levelOf(severity, priority="", ignitionPriority=""):
    """matrix level 1..5 from the Severity (preferred), the Priority text (P1..P4) or the Ignition priority"""
    try:
        s = int(float(str(severity)))
        if 1 <= s <= 5:
            return s
    except:
        pass
    p = str(priority or "").strip().upper()
    if p in PRIORITY_LEVEL:
        return PRIORITY_LEVEL[p]
    return IGNITION_LEVEL.get(str(ignitionPriority), 3)


def rowStyle(level, acked, blinkOn):
    on, off = ROW_STYLE.get((int(level or 3), bool(acked)), ROW_STYLE[(3, bool(acked))])
    return dict(on if blinkOn else off)


# Equipment border: "SEVERITY" = colour of the highest-severity alarm on the equipment (Alarm Severity Visual Matrix),
#                  "RED"      = red for any alarm.  Flashing while an alarm at that level is unacknowledged.
BORDER_MODE = "SEVERITY"


def border(level, acked):
    if not level:
        return NO_BORDER, NO_BORDER
    if BORDER_MODE == "RED":
        return ("4px solid " + RED, "4px solid " + RED) if acked else ("4px solid " + RED, "4px solid transparent")
    return BORDER.get((int(level), bool(acked)), BORDER[(3, bool(acked))])


def unitOf(folder):
    """IN11_E115_PCE_MIX11 -> MIX11"""
    return str(folder or "").split("]")[-1].split("/")[0].split("_")[-1].upper()


lineOf = unitOf


def loadLookupAll(lookupTag):
    """dataset tag -> {LINE: ({AlarmID: row}, {FBSSource: row})}; rows without Line under key "" (fallback)"""
    out = {}
    try:
        ds = system.tag.readBlocking([lookupTag])[0].value
        cols = list(ds.getColumnNames())
        for r in range(ds.getRowCount()):
            rec = dict((c, ds.getValueAt(r, c)) for c in cols)
            line = str(rec.get("Line") or "").strip().upper()
            byId, byFbs = out.setdefault(line, ({}, {}))
            byId[str(rec.get("AlarmID", "")).strip()] = rec
            f = str(rec.get("FBSSource") or "").strip()
            if f:
                byFbs[f] = rec
    except:
        pass
    return out


def loadLookup(lookupTag, line=""):
    """single-line view of the lookup (rows of this line, then rows without Line)"""
    allL = loadLookupAll(lookupTag)
    byId, byFbs = dict(allL.get("", ({}, {}))[0]), dict(allL.get("", ({}, {}))[1])
    mine = allL.get(str(line or "").upper(), ({}, {}))
    byId.update(mine[0]); byFbs.update(mine[1])
    return byId, byFbs


def _find(lk, unit, alarmId, fbs):
    for key in (unit, ""):
        byId, byFbs = lk.get(key, ({}, {}))
        r = byId.get(alarmId) or byFbs.get(fbs)
        if r:
            return r
    return {}


def _fmt(m):
    try:
        return system.date.format(system.date.fromMillis(m), "dd-MMM HH:mm:ss") if m else ""
    except:
        return ""


def _num(v):
    try:
        return str(int(float(str(v))))
    except:
        return str(v if v is not None else "").strip()


def _bool(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in ("true", "1", "yes", "on", "active")


def _ts(v):
    """ISO-8601 text from the PLC -> epoch ms; 0 when empty or the PLC default 1601-01-01"""
    s = str(v or "").strip()
    if not s or s.startswith("1601") or s.startswith("0001") or s.startswith("1970-01-01T00:00:00"):
        return 0
    try:
        from java.time import Instant, OffsetDateTime
    except ImportError:                                    # CPython (offline tests)
        import datetime, calendar
        try:
            d = datetime.datetime.strptime(s.replace("Z", "")[:19], "%Y-%m-%dT%H:%M:%S")
            return calendar.timegm(d.timetuple()) * 1000
        except:
            return 0
    try:
        return Instant.parse(s).toEpochMilli()
    except:
        try:
            return OffsetDateTime.parse(s).toInstant().toEpochMilli()
        except:
            return 0


def _get(entry, *names):
    """read a JSON field tolerating case / underscore / space differences"""
    for n in names:
        try:
            if n in entry:
                return entry[n]
        except:
            pass
    want = [n.replace("_", "").replace(" ", "").lower() for n in names]
    try:
        for k in entry.keys():
            if str(k).replace("_", "").replace(" ", "").lower() in want:
                return entry[k]
    except:
        pass
    return None


def readPlcAlarms(tagRoot, qv=None):
    """-> (list of alarm dicts from the CurrentAlarms JSON document, error text)"""
    if qv is None:
        path = "%s/%s" % (str(tagRoot or "").rstrip("/"), ALARM_DOC)
        qv = system.tag.readBlocking([path])[0]
    try:
        good = qv.quality.isGood()
    except:
        good = True
    if not good:
        return [], "%s quality %s" % (ALARM_DOC, qv.quality)
    v = qv.value
    if v is None:
        return [], ""
    if not isinstance(v, (list, tuple, dict)):
        txt = unicode(v).strip()
        if not txt:
            return [], ""
        v = system.util.jsonDecode(txt)
    if isinstance(v, dict):                     # tolerate {"Alarms": [...]}-style wrappers
        for k in v.keys():
            if isinstance(v[k], (list, tuple)):
                v = v[k]
                break
        else:
            v = [v]
    return list(v or []), ""


def equipmentOf(fbs, unit=""):
    f = str(fbs or "")
    if "GPA11" in f:
        return "GPA11"
    first = f.split(".")[0].upper()
    if first in EQUIPMENT:
        return first
    return unit if unit in EQUIPMENT else ""


def poll(provider, lookupTag, equipment=None, maxRows=5):
    """{"rows": [...], "eq": {STATION: {..., level, borderOn, borderOff}}, "error": "", "diag": ""}  (never raises)"""
    try:
        return _poll(provider, lookupTag, equipment, maxRows)
    except:
        import sys
        return emptyResult("Alarm poll failed: %s" % (sys.exc_info()[1],))


IG_STATES = ["ActiveUnacked", "ActiveAcked", "ClearUnacked"]
ASSOC = {"group": ["Alarm Group Id", "Alarm GroupID", "AlarmGroupId", "AlarmGroupID"],
         "code": ["Alarm Code", "AlarmCode"], "severity": ["Severity"],
         "priority": ["Alarm Priority", "Priority"], "fbs": ["FBS Source", "FBSSource"]}


def _prop(ev, names):
    """alarm property / associated data of an Ignition alarm event; '' when missing (never raises)"""
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


def _evMs(data):
    try:
        t = data.getTimestamp()
        return t.getTime() if hasattr(t, "getTime") else long(t)
    except:
        return 0


def plcRecords(tagRoot, qv=None):
    """source 1: PLC JSON document <tagRoot>/AGAdmin/CurrentAlarms -> (records, error)"""
    entries, err = readPlcAlarms(tagRoot, qv)
    out = []
    for n, a in enumerate(entries):
        try:
            grp, code = _num(_get(a, "AlarmGroupID", "AlarmGroupId")), _num(_get(a, "AlarmCode"))
            if grp in ("", "0") and code in ("", "0"):
                continue                                         # empty slot
            active, acked = _bool(_get(a, "Active", "ActiveStatus")), _bool(_get(a, "Acknowledged", "Acked"))
            if not active and acked:
                continue                                         # cleared and acknowledged
            out.append({"src": "PLC", "n": n, "grp": grp, "code": code, "fbs": str(_get(a, "FBSSource", "FBS Source") or "").strip(),
                        "path": "", "active": active, "acked": acked, "sev": _num(_get(a, "Severity")),
                        "prio": str(_get(a, "Priority") or "").strip(), "igPrio": "",
                        "tAct": _ts(_get(a, "TimestampActive")), "tRes": _ts(_get(a, "TimestampReset")),
                        "name": "", "display": "", "id": "%s.%s" % (grp, code), "unit": unitOf(tagRoot)})
        except:
            pass
    return out, err


def ignitionRecords(folders):
    """source 2: alarms configured in Ignition on tags under the nodesets -> (records, error)"""
    events = system.alarm.queryStatus(source=["*%s*" % f for f in folders], state=IG_STATES)
    out = []
    for n, ev in enumerate(events):
        try:
            active, acked = not ev.isCleared(), ev.isAcked()
            grp, code = _num(_prop(ev, ASSOC["group"])), _num(_prop(ev, ASSOC["code"]))
            out.append({"src": "IGN", "n": 10000 + n, "grp": grp, "code": code, "fbs": str(_prop(ev, ASSOC["fbs"]) or "").strip(),
                        "path": str(ev.getSource()), "active": active, "acked": acked, "sev": _num(_prop(ev, ASSOC["severity"])),
                        "prio": str(_prop(ev, ASSOC["priority"]) or "").strip(), "igPrio": str(ev.getPriority()),
                        "tAct": _evMs(ev.getActiveData()), "tRes": _evMs(ev.getClearedData()) if not active else 0,
                        "name": str(ev.getName() or ""), "display": str(ev.getDisplayPath() or ""), "id": str(ev.getId()),
                        "unit": next((unitOf(f) for f in folders if f in str(ev.getSource())), "")})
        except:
            pass
    return out, ""


def _poll(provider, lookupTag, equipment, maxRows):
    result = emptyResult()
    errors, recs, plc, ign = [], [], [], []
    prov = str(provider or "[default]")
    roots = [prov + f for f in NODESETS]
    try:
        qvs = system.tag.readBlocking(["%s/%s" % (r, ALARM_DOC) for r in roots])
    except:
        import sys
        qvs = [None] * len(roots)
        errors.append("Cannot read %s: %s" % (ALARM_DOC, sys.exc_info()[1]))
    for r, qv in zip(roots, qvs):
        if qv is None:
            continue
        try:
            p, e = plcRecords(r, qv)
            plc += p
            if e: errors.append("%s: %s" % (unitOf(r), e))
        except:
            import sys
            errors.append("%s: %s" % (unitOf(r), sys.exc_info()[1]))
    try:
        ign, e = ignitionRecords(NODESETS)
        if e: errors.append(e)
    except:
        import sys
        errors.append("Ignition alarm query failed: %s" % (sys.exc_info()[1],))
    plcIds = set((r["unit"], r["id"]) for r in plc)
    ign = [r for r in ign if (r["unit"], "%s.%s" % (r["grp"], r["code"])) not in plcIds]
    result["error"] = "; ".join(errors[:4])
    result["sources"] = {"plc": len(plc), "ignition": len(ign)}
    result["diag"] = "Active alarms - PLC JSON: %d | Ignition: %d | nodesets: %d" % (len(plc), len(ign), len(roots))
    lk = loadLookupAll(lookupTag)
    for r in plc + ign:
        try:
            alarmId = "%s.%s" % (r["grp"], r["code"])
            unit = r["unit"] or (str(r["fbs"]).split(".")[0].upper() if r["fbs"] else "")
            row = _find(lk, unit, alarmId, r["fbs"])
            sev = r["sev"] if r["sev"] in SEVERITY_TEXT else _num(row.get("Severity"))
            prio = r["prio"] or str(row.get("Priority") or "").strip()
            level = levelOf(sev, prio, r["igPrio"])
            fbs = r["fbs"] or str(row.get("FBSSource") or "")
            eq = equipmentOf(fbs, unit) or equipmentOf(r["path"], unit)
            if eq:
                st = result["eq"][eq]
                st["count"] += 1
                if r["active"]:
                    st["active"] = True
                if not r["acked"]:
                    st["unacked"] = True
                if level > st["level"]:
                    st["level"], st["_topUnacked"] = level, not r["acked"]
                elif level == st["level"] and not r["acked"]:
                    st["_topUnacked"] = True
            if equipment and eq != equipment:
                continue
            r.update({"lk": row, "sev2": sev, "prio2": prio, "level": level, "fbs2": fbs or r["display"] or r["path"], "unit2": unit})
            recs.append(r)
        except:
            pass
    for e, st in result["eq"].items():
        if st["unacked"]:
            st["state"] = "ACTIVE_UNACKED" if st["active"] else "CLEARED_UNACKED"
        elif st["active"]:
            st["state"] = "ACTIVE_ACKED"
        top = st.pop("_topUnacked", False)
        st["borderOn"], st["borderOff"] = border(st["level"], not top)
        st["levelName"] = LEVEL_NAME.get(st["level"], "")
    # newest first; entries without a timestamp keep the source order (after the time-stamped ones)
    recs.sort(key=lambda x: (-x["tAct"], x["n"]))
    missing = "(no entry in alarm list)"
    for r in recs[:int(maxRows)]:
        lk = r["lk"]
        result["rows"].append({
            "eventId": "%s:%s" % (r["unit2"], r["id"]), "level": r["level"], "Unit": r["unit2"], "acked": bool(r["acked"]), "active": bool(r["active"]), "source": r["src"],
            "TimestampActive": _fmt(r["tAct"]),
            "TimestampReset": _fmt(r["tRes"]) if not r["active"] else "",
            "AlarmGroupId": r["grp"], "AlarmCode": r["code"],
            "Severity": SEVERITY_TEXT.get(r["sev2"], r["sev2"]),
            "Priority": r["prio2"] or r["igPrio"],
            "FBSSource": r["fbs2"],
            "Label": str(lk.get("Label") or r["name"] or ""),
            "Description": str(lk.get("AlarmDescription") or r["display"] or ""),
            "OperatorMessage": str(lk.get("OperatorMessage") or (r["display"] or r["name"]) or missing),
            "Troubleshooting": str(lk.get("Troubleshooting") or missing),
            "ActiveStatus": "ACTIVE" if r["active"] else "CLEARED",
            "Acknowledged": "YES" if r["acked"] else "NO"})
    return result


def _g(r, k, d=None):
    try:
        v = r[k]
        return d if v is None else v
    except:
        return d


def styleRows(rows, blinkOn):
    """table rows {field: {"value", "style"}} styled by the severity matrix for the current blink phase (never raises)"""
    out = []
    try:
        for r in (rows or []):
            try:
                if _g(r, "eventId") is None and _g(r, "Label") is None:
                    continue                                   # not an alarm row
                level, acked = int(_g(r, "level", 3)), bool(_g(r, "acked", False))
                style = rowStyle(level, acked, bool(blinkOn))
                row = {"eventId": str(_g(r, "eventId", "")), "level": level, "acked": acked}
                for f in FIELDS:
                    v = _g(r, f, "")
                    if hasattr(v, "keys") or isinstance(v, dict):
                        v = _g(v, "value", "")
                    row[f] = {"value": v, "style": dict(style)}
                out.append(row)
            except:
                pass
    except:
        pass
    return out


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
