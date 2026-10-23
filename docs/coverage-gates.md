# A higher pass rate can hide lost coverage

## The problem

A small team changes a support assistant's prompt. The baseline passes eight of
ten golden cases. The new run passes eight of eight. The two missing cases used
to catch invented refunds. The percentage rose from 80% to 100%, but there is no
new evidence that refund handling improved.

These numbers are an illustrative scenario, not a measured product result.

## Derive the comparison from sets

Let B be the baseline case IDs and C the current case IDs.

- Shared cases: B intersect C. Only these have two observed outcomes.
- Removed cases: B minus C. Their current behavior is unknown.
- New cases: C minus B. Their baseline behavior is unknown.
- Regressions: shared cases that passed before and fail now.

Missing is different from failing. Preserve both facts: do not invent a current
failure for an unevaluated case, and do not hide that it was unevaluated.

`--fail-on-removed` is an explicit policy on top of this comparison. Use it when
every baseline case must run. Leave it off for intentional subset comparisons;
the summary still shows what was omitted. A missing baseline cannot establish
coverage, so strict mode fails in that situation too.

## Offline reproduction

From a checkout with the development dependencies installed:

```bash
python -m pytest -q tests/test_compare.py tests/test_summary_html.py tests/test_cli_compare.py
```

`test_compare_removed_coverage_gate` saves real run fixtures in a temporary
directory, invokes the CLI, and checks both the exit code and Markdown artifact.
It covers removal of previously passing and previously failing cases. The run
command tests replace the model execution boundary; no API requests are made and
your personal run history is untouched.

## Your 60-90 minute learning session

1. Spend 10 minutes explaining why 100% on fewer cases is not comparable to 80%
   on the full baseline.
2. Spend 15 minutes predicting the result for shared, new, removed, and disjoint
   sets before reading the implementation.
3. Spend 25-40 minutes tracing `compare_runs`, `to_compare_pr_summary`, and the two
   CLI entry points. Run the tests and inspect the fixture inputs.
4. Spend 10 minutes changing a fixture from passing to failing and predicting
   which checks should fail. Restore the fixture after the experiment.
5. Spend 5-10 minutes explaining why strict mode is optional and what a missing
   baseline means.

## Explain it in an interview

"I found that aggregate pass rates could conceal dropped evaluation cases. I
made added and removed coverage explicit and added an opt-in CI gate. The tests
exercise the CLI with saved runs, so the failure mode is reproducible offline."

Use that statement after you have run the exercise and can explain the code.

## Limits and the next question

Matching IDs do not prove that case inputs, assertions, or scoring rules stayed
the same. The current stored result does not contain a complete case-definition
snapshot. A future change should capture and compare a stable definition digest
with a versioned contract, while handling old run files explicitly. Do not claim
that this gate establishes semantic equivalence or statistical model quality.
