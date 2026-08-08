from promptguard.template import render


def test_render_simple():
    assert render("Hello {{name}}", {"name": "Ada"}) == "Hello Ada"


def test_render_missing_left_intact():
    assert render("Hi {{missing}}", {}) == "Hi {{missing}}"


def test_render_spaces_in_braces():
    assert render("{{ shop }}", {"shop": "Acme"}) == "Acme"


def test_render_empty():
    assert render("", {"a": 1}) == ""
    assert render("plain", None) == "plain"
