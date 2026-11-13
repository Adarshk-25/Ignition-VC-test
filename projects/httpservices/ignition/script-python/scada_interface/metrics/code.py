###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : metrics.py
# Module         : Interface Metrics
#
# Description:
# Provides a common metrics hook for interface measurements and currently routes
# metric records through the structured framework logger.
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

from scada_interface import logger


# -----------------------------------------------------------------------------
# Function    : record
# Description : Handles record logic for this module.
# -----------------------------------------------------------------------------
def record(ctx, metric_name, value, labels=None):
    # Skeleton: route metrics to SQL, Prometheus bridge, or structured logs.
    # Until a metrics backend exists, structured logs keep the signal searchable.
    logger.info(ctx, "METRIC", "RECORDED", metric_name, {"value": value, "labels": labels or {}})