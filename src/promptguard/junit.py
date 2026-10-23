from __future__ import annotations

import xml.etree.ElementTree as ET
import re
from pathlib import Path

from .models import RunResult


_INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


def _xml_text(value: str) -> str:
    # Preserve invalid XML 1.0 characters as visible escapes instead of losing
    # model-output evidence or failing the whole report.
    return _INVALID_XML.sub(lambda match: f"\\u{ord(match.group(0)):04x}", value)


def to_junit_xml(result: RunResult) -> str:
    """Serialize a run as JUnit XML (CI-friendly)."""
    suite = ET.Element(
        "testsuite",
        {
            "name": _xml_text(result.suite_name),
            "tests": str(result.total),
            "failures": str(result.failed),
            "errors": "0",
            "skipped": "0",
        },
    )
    if result.started_at:
        suite.set("timestamp", result.started_at.isoformat())

    for cr in result.case_results:
        case = ET.SubElement(
            suite,
            "testcase",
            {
                "classname": _xml_text(result.suite_name),
                "name": _xml_text(cr.case_id),
            },
        )
        if cr.latency_ms is not None:
            case.set("time", f"{cr.latency_ms / 1000:.3f}")

        if not cr.passed:
            messages = []
            for f in cr.failures:
                if isinstance(f, str):
                    messages.append(f)
                else:
                    messages.append(f"[{f.check}] {f.message}")
            fail = ET.SubElement(
                case,
                "failure",
                {
                    "message": _xml_text(messages[0] if messages else "failed"),
                    "type": "assertion",
                },
            )
            body = "\n".join(messages)
            if cr.output:
                body += f"\n\noutput:\n{cr.output[:1500]}"
            fail.text = _xml_text(body)

    ET.indent(suite, space="  ")
    return ET.tostring(suite, encoding="unicode", xml_declaration=True) + "\n"


def write_junit(result: RunResult, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_junit_xml(result), encoding="utf-8")
    return path
