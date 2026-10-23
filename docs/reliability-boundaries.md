# Reliability begins at the boundaries

An AI evaluation is useful only if it tests the intended cases, compares the
intended runs, preserves its evidence, and produces a usable report. A model's
output is only one part of that chain.

All examples below are synthetic failure scenarios. The regression tests are
offline checks of tool behavior, not evidence of model accuracy or product demand.

## Failure modes covered

| Boundary | Failure before the fix | Behavior and regression evidence |
| --- | --- | --- |
| Expectation bounds | Negative lengths or an impossible min/max range are accepted; invalid similarity thresholds can produce misleading checks | Configuration rejects invalid ranges, including non-finite similarity thresholds; see tests/test_models.py |
| Case identity | Directly constructed suites can have duplicate IDs, causing parallel results to overwrite one another | Every Suite construction requires unique, nonblank IDs; valid IDs retain their order |
| Regex configuration | A malformed expectation regex raises while scoring, after a model request | Compile patterns during configuration validation; valid patterns remain unchanged |
| Case selection | An empty failed-case intersection is interpreted as no filter, running the entire suite | Empty selections fail before client initialization; an absent filter still selects all cases |
| History paths | A run ID containing path separators can address files outside the run directory | Saving and loading require letters, digits, underscores, or hyphens; generated UUIDs remain supported |
| Run prefixes | Several runs matching a short prefix yield an arbitrary choice | Ambiguous prefixes produce an actionable error; an exact ID still wins |
| History writes | A direct write can truncate a previous result if persistence fails | Write a temporary file in the same directory, close it, and atomically replace the destination; failure preserves the old result and cleans the temporary file |
| History listing | JSON arrays, nulls, or malformed run objects can crash or pollute the history list | Validate stored run records; skip invalid files and retain valid results and suite filtering |
| Comparison scope | Unrelated suites with matching case IDs can appear to regress or improve | Reject cross-suite comparisons without writing a comparison report |
| Baseline preflight | A missing strict baseline is discovered after model execution and result saving | Resolve strict requirements before model work; a missing ordinary baseline still permits a bootstrap run |
| JSON output | Python's decoder accepts non-standard NaN and Infinity tokens as JSON values | Reject those numeric constants, including nested values; ordinary numbers, nulls, and quoted strings remain valid |
| JUnit XML | Control characters can make reports unparseable; a second serializer can lose attribute whitespace | Preserve illegal XML characters as visible Unicode escapes and serialize once; valid Unicode and XML metacharacters round-trip |

## Compatibility decisions

- Expectation configuration now rejects impossible values instead of accepting
  them. Suite case IDs must be unique and nonblank.
- Run IDs are filenames, not paths. A legacy manually assigned ID with spaces or
  punctuation outside the documented alphabet is rejected. Existing generated
  UUIDs and ordinary alphanumeric prefixes remain valid.
- Corrupt or incomplete run files are omitted from history listing. An explicit
  lookup still reports a readable validation error rather than inventing results.
- Intentional subset comparisons remain supported. Coverage enforcement remains
  opt-in with --fail-on-removed.
- Atomic replacement avoids exposing partially written JSON to readers. It does
  not provide multi-writer version conflict detection or a power-loss durability
  guarantee; there is no fsync or transaction log in this implementation.
- Matching suite and case IDs do not establish unchanged prompts, inputs,
  assertions, or scoring rules.

## Verify from a fresh checkout

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

The completed sprint has 110 offline tests. CI exercises Python 3.11 and 3.12 on
both Linux and Windows. The optional existing live evaluation remains restricted
to the Linux/Python 3.12 job and still requires its configured API key.

Windows sandbox restrictions can deny file replacement in temporary test
directories. Local atomic-write checks passed with normal Windows file
permissions. Such a permission failure must be reported, not treated as a pass
or bypassed by disabling the relevant assertions.

## A 60-90 minute first-principles exercise

Choose one boundary today: the empty selection bug.

1. Spend 10 minutes deriving the difference between an absent filter and an
   explicit empty set. In set terms, no selection restriction is different from
   the intersection of two disjoint sets.
2. Spend 15 minutes predicting which cases should run when a previous run failed
   case A and the user asks to rerun only case B.
3. Spend 20-30 minutes reading filter_cases, run_suite, and
   test_from_failed_empty_intersection_does_not_run_entire_suite.
4. Run the focused verification:

   ```bash
   python -m pytest -q tests/test_runner.py tests/test_cli_compare.py -k "selection or intersection or baseline"
   ```

5. Spend 10 minutes explaining why validation should happen before creating a
   model client, and why this protects cost and the meaning of the result.
6. Use the remaining time to predict another case and add a test. Do not call a
   live API to demonstrate a selection bug.

Implementation is not evidence that you have learned this material. Explain the
failure and the tradeoff in your own words after running the exercise.

## Remaining work

Transport timeout and retry behavior, complete case-definition snapshots,
statistical evaluation quality, and external pilot value are outside this sprint.
This is a local tool reliability improvement, not a production-readiness claim.
