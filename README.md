# JEV Trace Evaluator

A CLI-first evaluator for recorded agent runs. It combines local security and
output guardrail checks with optional JEV judgments through LangChain.

**[Try the interactive mock on GitHub Pages](https://sohithk10.github.io/jev-trace-evaluator/)**
— synthetic examples only; no backend, uploads, or live model calls.

![JEV Trace Observatory: local evaluation dashboard with trace input, policy failures, and human-review findings](docs/ui-screenshot.png)

## Local web UI

After installation, run `jev-eval ui` and open **http://127.0.0.1:8765**.
Use `jev-eval ui --port 8766` to select another port.

Load the synthetic demo or upload JSON/JSONL traces, set a comma-separated tool
allowlist, and click **Run evaluation**. Inspect individual findings and download
the JSON report. The screenshot above shows the synthetic demo, not production data.

The UI runs offline checks only and uses the other default policy settings. It
does not call JEV, request API keys, or upload traces externally. Use the CLI for
custom policies and opt-in live judging. The server binds only to IPv4 loopback,
checks Host/Origin and a per-session token, and stores no uploaded files. Do not
expose it through a public proxy. The README image appears on the GitHub repository
front page. The real evaluator runs locally; GitHub Pages hosts a separate synthetic-only mock.

### Rebuild the hosted mock

Run `python scripts/build_demo.py` after changing the local UI. This generates the
static demo in `docs/`, with read-only fixtures and an explicitly labeled mock report.
GitHub Pages publishes `main` → `/docs`. No API keys or server are deployed.

Inspired by [JEV-as-a-Judge: Accept When Confident, Escalate When Unsure](https://arxiv.org/abs/2609.26550).
This is an independent implementation, not the paper's benchmark reproduction.
It uses confidence gating, but escalates uncertain cases to **human review**, not
an automatic second LLM. It makes no claim to the paper's accuracy or cost results.

## Quick start: no API key, no network calls

Requires Python 3.11 or newer. Run from this repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
jev-eval evaluate examples/traces.jsonl --policy examples/policy.json
```

The synthetic demo returns one `fail` and two `review` results, with exit code 1.
That is expected: it includes an unauthorized tool and a prompt-injection indicator.
Offline mode never awards an overall pass, because semantic checks were not run.
It has no runtime dependencies and makes no network requests.

Save a report without recording the input text:

```bash
mkdir -p reports
jev-eval evaluate examples/traces.jsonl --policy examples/policy.json > reports/audit.json
```

Reports contain fingerprints, fixed finding codes, probabilities, decisions, policy
hash, and evaluator/rubric versions. They do not contain raw prompts, outputs,
tool arguments, trace IDs, or provider exception messages. Reports are still sensitive
operational data: keep them private.

## Live JEV evaluation

```bash
python -m pip install -e '.[jev]'
# Set TYPESAFE_API_KEY securely in your environment, not in a trace or committed file.
jev-eval evaluate examples/langsmith-run.json \
  --policy examples/policy.json --judge jev --allow-network
```

`--allow-network` explicitly permits transmission of unflagged trace content to
`https://api.typesafe.ai`. It can incur charges. Review and sanitize your trace
export first: the built-in patterns are **not comprehensive PII or secret detection**.
There is no automatic redaction that silently changes the evidence. Flagged traces
are kept local and skip JEV entirely. Implicit LangSmith tracing of judge requests
is disabled. `TYPESAFE_BASE_URL` is not used; the provider endpoint is fixed.

The default model is `jev-latest`. For repeatable experiments use
`--model <provider-supported-versioned-model-id>` and record the SDK environment.
The alias may change; the report records the requested identifier, not a guarantee
of the resolved server version. Requests have a 30-second network timeout and
no application-level retries. By default at most 10 traces may be submitted per
invocation; change this deliberately with `--max-live-traces N`.

The TypeSafe LangChain integration is beta and pinned to `0.0.1a3`. Tests exercise
the real SDK with a mocked HTTP transport. They do not establish live service
availability, correctness, or security effectiveness.

## Decision rules

1. Validate the whole batch and policy before any provider call.
2. Run local checks. Hard violations fail; indicators and missing execution data
   require review. Any local finding prevents that trace from leaving the machine.
3. If enabled, ask JEV four independent yes/no questions: task completion,
   groundedness, safe behavior, and instruction-boundary compliance.
4. For each returned probability `p` of passing, compute `q = max(p, 1-p)`.
   Accept its pass/fail judgment only when `q >= threshold`; otherwise require review.
5. Any failure makes the overall result fail. Otherwise any unknown makes it review.
   Only all confident semantic passes with no local findings produce pass.

A high confidence of failure is a **failure**, not a pass. Missing criteria,
malformed probabilities, timeouts, and API errors cannot produce passes. A model
cannot override a hard local violation. Review results contain
`"escalation": "human_review"`; no review ticket or notification is sent automatically.

The default threshold `0.95` is an **uncalibrated starting setting**, not a promised
95% accuracy. Before using a pass as a release gate, have humans label representative
traces, pick the threshold on a calibration split for an acceptable false-pass rate,
freeze it, and assess coverage and false passes on a separate held-out split. Repeat
after changing the model, rubric, policy, or workload. Include confidently wrong,
style-adversarial, prompt-injection, and missing-evidence cases.

## Input formats

Use `.json` for one object or an array; `.jsonl` for one object per line.
All traces must fit the documented schema. Maximum input is 5 MB, 1,000 traces,
and 32 JSON nesting levels. Duplicate keys, non-finite numbers, unknown canonical
fields, and invalid types are rejected. Inputs are data: nothing is executed.

### Canonical trace

```json
{
  "id": "optional-local-label",
  "input": "What is the return window?",
  "output": "30 days.",
  "tools": [
    {"name": "search_docs", "input": {"query": "returns"}, "output": "Returns accepted within 30 days."}
  ],
  "evidence": ["Returns accepted within 30 days."],
  "error": false,
  "incomplete": false
}
```

Only `input` and `output` are required. Input, output, evidence, and tool payloads
are JSON values. `tools` is an array of records with a nonempty `name` and optional
`input`/`output`. Error and incomplete flags must be booleans. `id` is discarded.
The record is not an attestation: falsified or omitted actions cannot be detected.

### LangChain / LangSmith export

```bash
jev-eval evaluate examples/langsmith-run.json --policy examples/policy.json
```

Supports a **nested run tree** with `run_type`, `inputs`, `outputs`, `end_time`, and
`child_runs`. Tool runs use `run_type: "tool"` and `name`. All nested run inputs,
outputs, and errors remain available to the evaluator. Metadata, tags, timestamps,
and IDs are not sent to JEV. Missing end times require review. Child IDs without
nested child objects are rejected to avoid evaluating an incomplete export.

This CLI does not download from LangSmith or upload scores. Flat span lists, OpenTelemetry
exports, arbitrary callback event logs, and unresolved child-run references must
be converted first. Inspect the synthetic fixture for the supported shape.

## Policy and checks

Start with `examples/policy.json`. Tool names are exact, case-sensitive matches.
The default empty allowlist rejects every recorded tool call.

| Policy/check | Behavior |
| --- | --- |
| `allowed_tools` | Hard failure for an unlisted tool |
| `max_tool_calls` | Hard failure above the call count |
| `max_output_chars` | Hard failure above output length; objects use JSON serialization length |
| `required_output_keys` | Require a JSON object with these top-level keys; no full JSON Schema validation |
| `forbidden_output_terms` | Case-insensitive literal substring match, hard failure |
| `threshold` | Semantic confidence gate, greater than 0.5 and at most 1 |
| Credential patterns | Hard failure; selected token prefixes, private key headers, named credential assignments |
| Email pattern | Possible personal data: review |
| Injection patterns | Selected instruction-override phrases: review, not proof of attack success |
| Error/incomplete/empty output | Review |

There is no URL fetching, tool execution, shell evaluation, or trace deserialization
into executable objects. There is no network-egress analysis, malware scanner, full
DLP engine, or live-agent guardrail enforcement. See [SECURITY.md](SECURITY.md).

## CI exit codes

| Code | Meaning |
| --- | --- |
| 0 | All traces passed all enabled semantic and local checks |
| 1 | At least one trace failed (takes priority over review) |
| 2 | Review required or judge setup unavailable; argparse also uses 2 for bad CLI syntax |
| 3 | Invalid/unreadable trace or policy, or missing network consent |

Do not use `|| true` for a release gate. Offline audit succeeds at finding violations,
but deliberately exits nonzero even for clean traces because semantics remain unchecked.

## Development

```bash
python -m pip install -e '.[test,jev]'
python -m pytest -q
```

The tests cover gating, invalid probabilities, secret-safe errors, provider failures,
no-upload behavior, input validation, nested run normalization, guardrail violations,
CLI exit codes, and the pinned SDK's HTTP contract. No credentials or live API calls
are needed. Without the `jev` extra, the SDK contract test is skipped.

## References

- [Research paper](https://arxiv.org/abs/2609.26550): the confidence-routing idea.
- [Official LangChain TypeSafe integration](https://github.com/langchain-ai/langchain/tree/master/libs/partners/typesafe): typed Noul probabilities and the runnable API.
- [Pinned SDK release](https://pypi.org/project/langchain-typesafe/0.0.1a3/).

No source code, datasets, or figures from the paper are bundled.
