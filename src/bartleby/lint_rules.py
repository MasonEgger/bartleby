# ABOUTME: The leaf types every lint module shares: a Rule row and a Finding.
# ABOUTME: Imports nothing from bartleby, so linting and linting_a11y both build on it.

"""The two shapes `bartleby lint` is made of.

A :class:`Rule` is one row of the rule table (id, severity, description, hint); a
:class:`Finding` is one report of a rule against a file. They live here so
:mod:`bartleby.linting` (the runner and the content rules) and
:mod:`bartleby.linting_a11y` (the accessibility rules) share them without importing
each other.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rule:
    """One lint rule as the docs, the CLI, and the generated skills describe it.

    :ivar id: The stable kebab-case rule id that findings and ``--rules`` use.
    :ivar severity: ``"error"`` (fails the command) or ``"warning"``.
    :ivar description: One sentence saying what the rule reports.
    :ivar hint: The fix every finding of this rule prints.
    """

    id: str
    severity: str
    description: str
    hint: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "severity": self.severity,
            "description": self.description,
            "hint": self.hint,
        }


@dataclass(slots=True)
class Finding:
    """One issue reported by :func:`bartleby.linting.lint_site`.

    :ivar severity: ``"error"``, ``"warning"``, or ``"info"``.
    :ivar rule: Stable machine-readable rule name (e.g. ``"orphaned-page"``).
    :ivar file: Source path of the offending page.
    :ivar message: Human-readable description of the issue.
    :ivar line: Line number when known; ``0`` when not applicable.
    :ivar fixable: Whether ``--fix`` can resolve this issue automatically.
    :ivar hint: The concrete fix, printed as ``(fix: ...)`` after the message.
    """

    severity: str
    rule: str
    file: str
    message: str
    line: int = 0
    fixable: bool = False
    hint: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "rule": self.rule,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "fixable": self.fixable,
            "hint": self.hint,
        }
