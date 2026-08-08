from promptguard.models import Expect
from promptguard.scorer import score, token_jaccard


def test_contains_pass():
    assert score("Hello world", Expect(contains=["hello"])) == []


def test_contains_fail():
    fails = score("Hello", Expect(contains=["goodbye"]))
    assert len(fails) == 1
    assert fails[0].check == "contains"


def test_not_contains():
    fails = score("I don't know", Expect(not_contains=["don't know"]))
    assert len(fails) == 1


def test_regex():
    assert score("order #42", Expect(regex=[r"#\d+"])) == []
    assert score("no number", Expect(regex=[r"#\d+"]))


def test_exact_normalized():
    assert score("  a   b  ", Expect(exact="a b")) == []


def test_json_keys():
    out = '{"status": "ok", "eta": "tomorrow"}'
    assert score(out, Expect(json_valid=True, json_keys=["status", "eta"])) == []
    fails = score('{"status": "ok"}', Expect(json_valid=True, json_keys=["eta"]))
    assert any(f.check == "json_key" for f in fails)


def test_json_fenced():
    out = '```json\n{"a": 1}\n```'
    assert score(out, Expect(json_valid=True, json_keys=["a"])) == []


def test_similar_to():
    assert token_jaccard("refund in 30 days", "30 day refund") > 0.3
    fails = score("hello", Expect(similar_to="completely different text", min_similarity=0.9))
    assert fails and fails[0].check == "similar_to"


def test_min_max_chars():
    fails = score("hi", Expect(min_chars=10))
    assert fails[0].check == "min_chars"
    fails = score("x" * 50, Expect(max_chars=10))
    assert fails[0].check == "max_chars"
