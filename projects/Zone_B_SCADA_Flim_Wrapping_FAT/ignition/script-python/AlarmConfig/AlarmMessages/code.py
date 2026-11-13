# AlarmMessages.py

ALARMS = {

    (9, 140): {
        "severity": 4,
        "priority": "P1",
        "label": "PDM1MCCB11PLANETARYTrip",
        "description": "C1-PDM1: MCCB11 PLANETARY circuit breaker tripped. Check electrical panel for fault condition."
    },

    (9, 141): {
        "severity": 4,
        "priority": "P1",
        "label": "PDM1MCCB12DISPERTrip",
        "description": "C1-PDM1: MCCB12 DISPER circuit breaker tripped. Check electrical panel for fault condition."
    },

    (261, 9): {
        "severity": 3,
        "priority": "P2",
        "label": "InverterFault",
        "description": "Inverter fault active: PLANETARY"
    },

    (261, 10): {
        "severity": 3,
        "priority": "P2",
        "label": "InverterFault",
        "description": "Inverter fault active: DISPER"
    },

    (261, 11): {
        "severity": 2,
        "priority": "P3",
        "label": "InverterWarning",
        "description": "Inverter warning active: PLANETARY"
    },

    (261, 12): {
        "severity": 2,
        "priority": "P3",
        "label": "InverterWarning",
        "description": "Inverter warning active: DISPER"
    }
}


def getAlarm(groupId, alarmCode):
    return ALARMS.get(
        (int(groupId), int(alarmCode)),
        None
    )