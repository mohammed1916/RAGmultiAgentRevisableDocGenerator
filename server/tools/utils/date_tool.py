"""Date grounding tool for LLM prompts.

The LLM has no reliable notion of "today", so any planning that reasons about
a deadline needs the current date supplied to it. This tool computes date facts
in Python and formats them as a prompt block the agents can embed directly.

It replaces ad-hoc date handling in agents: instead of the model guessing the
date, the caller injects :func:`date_context` into the prompt, optionally with a
parsed deadline so the model can pace the plan against real days remaining.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional


# Formats accepted for a user-supplied deadline, tried in order.
_DEADLINE_FORMATS = (
    "%Y-%m-%d",       # 2026-03-15
    "%d-%m-%Y",       # 15-03-2026
    "%d/%m/%Y",       # 15/03/2026
    "%B %d, %Y",      # March 15, 2026
    "%B %d %Y",       # March 15 2026
    "%d %B %Y",       # 15 March 2026
    "%B %Y",          # March 2026 (assumes the 1st)
)


def today() -> date:
    """Return the current local date (single source of truth for 'now')."""
    return date.today()


def parse_deadline(value: Optional[str]) -> Optional[date]:
    """Parse a free-text deadline into a date, or None if unparseable/empty.

    Accepts common formats (ISO, day-first, and month-name variants). Returns
    None rather than raising so callers can degrade to a deadline-less plan.
    """
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    for fmt in _DEADLINE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def days_until(target: date, reference: Optional[date] = None) -> int:
    """Whole days from ``reference`` (default today) until ``target``.

    Negative if the target is already in the past.
    """
    return (target - (reference or today())).days


def date_context(deadline: Optional[str] = None) -> str:
    """Build a prompt block stating today's date and, if given, the deadline.

    Embed the returned string in an agent prompt so the model reasons from the
    real current date instead of guessing. When a deadline is supplied and
    parseable, the remaining-days figure is included so the model can pace work.
    """
    now = today()
    lines = [f"Current date: {now.isoformat()} ({now.strftime('%A, %B %d, %Y')})."]

    parsed = parse_deadline(deadline)
    if parsed is not None:
        remaining = days_until(parsed, now)
        if remaining < 0:
            lines.append(
                f"Deadline: {parsed.isoformat()} — this date has already passed "
                f"({abs(remaining)} days ago); flag this to the learner."
            )
        else:
            lines.append(
                f"Deadline: {parsed.isoformat()} ({remaining} days remaining). "
                "Pace the plan to fit within the days remaining."
            )
    elif deadline:
        # A deadline was provided but couldn't be parsed — say so rather than
        # silently dropping it.
        lines.append(
            f'Deadline (as given, unparsed): "{deadline}". Interpret it against '
            "the current date above."
        )

    return "\n".join(lines)
