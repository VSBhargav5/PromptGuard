import xml.etree.ElementTree as ET

import pytest

from promptguard.junit import to_junit_xml
from promptguard.models import CaseResult, Failure, RunResult


def _run(text):
    return RunResult(
        suite_name="suite-" + text,
        model="offline",
        temperature=0,
        total=1,
        passed=0,
        failed=1,
        case_results=[CaseResult(
            case_id="case-" + text,
            passed=False,
            output="output " + text,
            latency_ms=125,
            failures=[Failure(check="exact", message="mismatch " + text)],
        )],
    )


@pytest.mark.parametrize("character", ["\x00", "\x01", "\x08", "\x0b", "\x1f", "\ud800", "\ufffe"])
def test_invalid_xml_characters_are_preserved_as_visible_escapes(character):
    xml = to_junit_xml(_run(character))
    root = ET.fromstring(xml)
    escaped = f"\\u{ord(character):04x}"
    assert escaped in root.attrib["name"]
    case = root.find("testcase")
    assert escaped in case.attrib["name"]
    failure = case.find("failure")
    assert escaped in failure.attrib["message"]
    assert escaped in failure.text
    assert character not in xml


def test_junit_preserves_normal_unicode_and_xml_metacharacters():
    text = "<refund> & approved 🚀\tline\nnext"
    root = ET.fromstring(to_junit_xml(_run(text)))
    assert root.attrib["name"] == "suite-" + text
    case = root.find("testcase")
    assert case.attrib["time"] == "0.125"
    assert "output " + text in case.find("failure").text
