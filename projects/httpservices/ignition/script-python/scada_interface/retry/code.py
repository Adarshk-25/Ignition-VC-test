###############################################################################
# Project        : AGRATAS SCADA - MES Integration
# File Name      : retry.py
# Module         : Retry Wrapper
#
# Description:
# Provides a reusable retry loop for technical operations, including retry count
# tracking in the shared transaction context and fixed backoff delay.
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

import sys
import time


# -----------------------------------------------------------------------------
# Function    : execute
# Description : Handles execute logic for this module.
# -----------------------------------------------------------------------------
def execute(
    ctx,
    operation_name,
    operation,
    retry_count,
    retry_backoff_ms,
    is_retryable,
    should_retry_result=None,
    on_retry=None
):
    """Execute an operation with fixed-backoff exception/result retries.

    ``retry_count`` is the number of additional attempts after the initial
    call. Existing callers that retry exceptions only remain compatible;
    callers may optionally supply ``should_retry_result`` to retry a returned
    result and ``on_retry`` to record retry diagnostics.
    """
    attempt = 0
    while True:
        try:
            result = operation()
            retry_result = (
                should_retry_result is not None
                and should_retry_result(result)
            )
            if not retry_result or attempt >= retry_count:
                return result

            attempt += 1
            ctx["retry_count"] = ctx.get("retry_count", 0) + 1
            if on_retry is not None:
                on_retry(
                    operation_name,
                    "RESULT",
                    result,
                    attempt,
                    retry_count - attempt,
                    retry_backoff_ms
                )
            time.sleep(float(retry_backoff_ms) / 1000.0)
        except Exception:
            ex = sys.exc_info()[1]
            # retry_count is the number of extra attempts after the first failure.
            if attempt >= retry_count or not is_retryable(ex):
                raise

            attempt += 1
            # Store retry count in context so audit and logs report final retry usage.
            ctx["retry_count"] = ctx.get("retry_count", 0) + 1
            if on_retry is not None:
                on_retry(
                    operation_name,
                    "EXCEPTION",
                    ex,
                    attempt,
                    retry_count - attempt,
                    retry_backoff_ms
                )
            time.sleep(float(retry_backoff_ms) / 1000.0)