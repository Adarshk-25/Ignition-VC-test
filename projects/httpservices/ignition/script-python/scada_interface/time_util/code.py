###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : time_util.py
# Module         : Time Utilities
#
# Description:
# Provides shared time helper functions for calculating transaction and step
# durations from the framework context.
#
# Author         : Hari
# Version        : 1.0
# Date           : 07-Jul-2026
#
# Change History
# -----------------------------------------------------------------------------
# Sl No | Version | Date        | Author | Fix/Change
# -----------------------------------------------------------------------------
# 1     | 1.0     | 07-Jul-2026 | Hari   | Initial documented version
# -----------------------------------------------------------------------------
###############################################################################

# -----------------------------------------------------------------------------
# Function    : duration_ms
# Description : Handles duration ms logic for this module.
# -----------------------------------------------------------------------------
def duration_ms(ctx):
    # Duration is derived from the shared transaction start time.
    return system.date.millisBetween(ctx.get("start_time"), system.date.now())