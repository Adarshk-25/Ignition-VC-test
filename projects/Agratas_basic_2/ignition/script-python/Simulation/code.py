import random
import time

STEP_SECONDS = 10
SHIFT_SECONDS = 8 * 3600

def simulatePLC(state):

    now = int(time.time())
    state["lastUpdate"] = now

    # --- Advance simulated shift clock ---
    state["shiftElapsed"] += STEP_SECONDS

    # --- State Machine Logic ---
    # States: 1=RUNNING, 2=STOPPED

    if state["machineState"] == 1:
        # Random stop trigger (once per cycle window)
        if state["stopTimer"] <= 0 and random.random() < state["stopProbability"]:
            state["machineState"] = 2
            state["stopTimer"] = random.randint(60, 300)  # 1–5 min stop
    else:
        state["stopTimer"] -= STEP_SECONDS
        if state["stopTimer"] <= 0:
            state["machineState"] = 1

    # --- Production Logic ---
    if state["machineState"] == 1:
        partsProduced = int(STEP_SECONDS / state["idealCycleTime"])
        state["totalCount"] += partsProduced

        rejects = int(partsProduced * state["rejectRate"])
        state["rejectCount"] += rejects
        state["goodCount"] += (partsProduced - rejects)

        state["runTime"] += STEP_SECONDS
    else:
        state["downTime"] += STEP_SECONDS

    # --- Shift Detection (NO COUNTER RESET) ---
    if state["shiftElapsed"] >= SHIFT_SECONDS:
        state["shiftNumber"] += 1
        state["shiftElapsed"] = 0

    return state


# -------- INITIAL MACHINE STATE --------

machine = {
    "machineState": 1,
    "idealCycleTime": 2.0,       # seconds per part
    "rejectRate": 0.03,          # 3% reject
    "stopProbability": 0.05,     # chance to trigger stop
    "stopTimer": 0,
    "shiftElapsed": 0,
    "shiftNumber": 1,
    "runTime": 0,
    "downTime": 0,
    "totalCount": 0,
    "goodCount": 0,
    "rejectCount": 0,
    "lastUpdate": 0
}


# -------- SIMULATE 1 HOUR --------

for i in range(int(3600 / STEP_SECONDS)):
    machine = simulatePLC(machine)

print machine