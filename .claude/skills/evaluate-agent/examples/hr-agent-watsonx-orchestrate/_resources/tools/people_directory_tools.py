"""
Native python toolkit for the agentevaluator People Directory demo agent.

Three deterministic, in-memory tools modelling a tiny employee directory:
  * lookup_employee_record(alias) -> employee id
  * list_paid_leave_days(employee_id, period_start, period_end) -> list of YYYYMMDD strings
  * list_direct_reports(manager_id) -> list of subordinate aliases

Tool calls are observed by orchestrate's built-in LangFuse integration —
no manual SDK wiring belongs here. Start the orchestrate Developer Edition
with `orchestrate server start --with-langfuse` (or `-l`) so traces are
emitted to the local Langfuse at http://localhost:3010 (creds:
orchestrate@ibm.com / orchestrate). The agentevaluator's
fetch_observability.py reads those traces back via the manifest's
observability.langfuse block.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Final

from ibm_watsonx_orchestrate.agent_builder.tools import (
    ToolPermission,
    tool,
)

_DIRECTORY: Final[dict[str, dict]] = {
    "alex.river": {
        "employee_id": "EMP-1042",
        "leave_days": ["20260118"],
        "direct_reports": [],
    },
    "jordan.kim": {
        "employee_id": "EMP-1043",
        "leave_days": ["20260218", "20260301"],
        "direct_reports": [],
    },
    "sam.cole": {
        "employee_id": "EMP-1099",
        "leave_days": ["20260205"],
        "direct_reports": ["alex.river", "jordan.kim"],
    },
}

_BY_ID: Final[dict[str, dict]] = {
    record["employee_id"]: record
    for record in _DIRECTORY.values()
}

_DATE_FORMAT_INPUT: Final[str] = "%Y-%m-%d"
_DATE_FORMAT_LEAVE: Final[str] = "%Y%m%d"


def _validate_period_date(date_text: str) -> bool:
    try:
        datetime.strptime(date_text, _DATE_FORMAT_INPUT)
        return True
    except ValueError:
        return False


@tool(
    name="lookup_employee_record",
    description=(
        "Resolve an employee alias (e.g. 'alex.river') to the "
        "internal employee id used by every other tool in this "
        "directory."
    ),
    permission=ToolPermission.ADMIN,
)
def lookup_employee_record(employee_alias: str) -> str:
    """
    Return the employee_id for the given alias.

    :param employee_alias: lowercase 'first.last' alias of the employee.
    """
    record = _DIRECTORY.get(employee_alias)
    if record is None:
        return (
            f"Error: alias {employee_alias!r} is not "
            f"registered in the directory."
        )
    return record["employee_id"]


@tool(
    name="list_paid_leave_days",
    description=(
        "Return the paid-leave days an employee took inside an "
        "inclusive date range. Dates are returned in YYYYMMDD."
    ),
    permission=ToolPermission.ADMIN,
)
def list_paid_leave_days(
    employee_id: str,
    period_start: str,
    period_end: str,
) -> str:
    """
    List YYYYMMDD strings for paid leave inside the period.

    :param employee_id: id returned by lookup_employee_record.
    :param period_start: inclusive lower bound, YYYY-MM-DD.
    :param period_end: inclusive upper bound, YYYY-MM-DD.
    """
    if not _validate_period_date(period_start):
        return (
            f"Error: period_start {period_start!r} is "
            f"not in YYYY-MM-DD format."
        )
    if not _validate_period_date(period_end):
        return (
            f"Error: period_end {period_end!r} is not "
            f"in YYYY-MM-DD format."
        )
    record = _BY_ID.get(employee_id)
    if record is None:
        return (
            f"Error: employee_id {employee_id!r} not "
            f"found. Resolve the alias via "
            f"lookup_employee_record first."
        )
    start = datetime.strptime(
        period_start, _DATE_FORMAT_INPUT
    )
    end = datetime.strptime(period_end, _DATE_FORMAT_INPUT)
    inside_period = [
        day
        for day in record["leave_days"]
        if start
        <= datetime.strptime(day, _DATE_FORMAT_LEAVE)
        <= end
    ]
    return json.dumps(inside_period)


@tool(
    name="list_direct_reports",
    description=(
        "Return the aliases of every employee who reports "
        "directly to the given manager id. Aliases can be fed "
        "back into lookup_employee_record."
    ),
    permission=ToolPermission.ADMIN,
)
def list_direct_reports(manager_id: str) -> str:
    """
    List aliases of an employee's direct reports.

    :param manager_id: employee_id of the manager.
    """
    record = _BY_ID.get(manager_id)
    if record is None:
        return (
            f"Error: manager_id {manager_id!r} not "
            f"found. Resolve the alias via "
            f"lookup_employee_record first."
        )
    return json.dumps(record["direct_reports"])
