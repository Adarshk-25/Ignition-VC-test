import system

def buildEquipmentSchedule():

    start = system.date.now()                      # java.util.Date
    end   = system.date.addHours(start, 12)        # java.util.Date

    return {
        "items": [
            {
                "id": 1,                           # int (required)
                "label": "Mixer-01"
            },
            {
                "id": 2,
                "label": "Coater-02"
            }
        ],

        "dateRange": {
            "startDate": start,
            "endDate": end
        },

        "scheduledEvents": [
            {
                "itemId": 1,                       # int → matches items.id
                "eventId": 101,
                "label": "Production Run",
                "startDate": system.date.addMinutes(start, 30),
                "endDate": system.date.addHours(start, 4),
                "percentDone": 40
            },
            {
                "itemId": 2,
                "eventId": 102,
                "label": "Maintenance",
                "startDate": system.date.addHours(start, 1),
                "endDate": system.date.addHours(start, 3),
                "percentDone": 75
            }
        ],

        "breakEvents": [
            {
                "startDate": system.date.addHours(start, 6),
                "endDate": system.date.addMinutes(
                    system.date.addHours(start, 6), 30
                )
            }
        ],

        "selectedEvent": {
            "itemId": 1,
            "eventId": 101
        },

        "currentTimeIndicator": {
            "color": "#8A8AFF"
        }
    }
	
	
	
	
	

def addnumber (a,b):
	return a+b