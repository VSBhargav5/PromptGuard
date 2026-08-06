from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from .models import RunResult


def to_junit_xml(result: RunResult) -> str:
    """Serialize a run as JUnit XML (CI-friendly)."""
    suite = ET.Element(
        "testsuite",
        {
            "name": result.suite_name,
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
                "classname": result.suite_name,
                "name": cr.case_id,
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
                    "message": messages[0] if messages else "failed",
                    "type": "assertion",
                },
            )
            body = "\n".join(messages)
            if cr.output:
                body += f"\n\noutput:\n{cr.output[:1500]}"
            fail.text = body

    rough = ET.tostring(suite, encoding="unicode")
    return minidom.parseString(rough).toprettyxml(indent="  ")


def write_junit(result: RunResult, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_junit_xml(result), encoding="utf-8")
    return path
