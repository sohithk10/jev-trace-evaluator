# Security boundaries

This tool audits recorded traces. It does not prevent an agent from performing an
unsafe action. Enforce permissions, egress restrictions, sandboxing, authentication,
and human approvals in the running agent independently.

## Untrusted trace content

- JSON only. Never replay or execute trace tools.
- All traces are validated before live evaluation begins.
- Trusted policy comes from the local policy file, not from trace instructions.
- Known secret, email, and injection indicators stop external evaluation of that trace.
- The model prompt marks trace content untrusted, but this is not a proven defense
  against prompt injection. A model can still return a confidently wrong answer.
- Hard failures cannot be overridden by semantic judgments.
- API errors and incomplete verdicts require human review.

## Data handling

Offline mode sends nothing over the network. Live mode sends the normalized trace
to TypeSafe only with explicit network consent. Detection patterns are narrow and
can be evaded through encoding, obfuscation, unsupported secret types, or ordinary
personal data that does not look like an email address. Sanitize real traces before
using live mode. Do not send regulated or confidential data without appropriate
provider agreements and organizational authorization.

Reports omit raw trace text and provider exception strings. Trace SHA-256 values
are reproducibility identifiers, not anonymization; low-entropy inputs may be
guessable. Restrict report permissions. Debuggers, third-party instrumentation,
and platform logs are outside this tool's protection. Keep API keys in a secret
manager/environment, never in arguments, example files, reports, or version control.

## Coverage limits

Credential patterns and injection phrases have false positives and false negatives.
Allowed tools can still receive malicious arguments. Tool names are not verified
identities. Missing or forged actions in a trace cannot be recovered. Exports must
be complete and trustworthy. Model confidence is not calibrated correctness.
Output key checking only checks key presence. Local checks are policy heuristics,
not a compliance certification or security test suite for the underlying agent.

Review dependency updates and re-run tests before changing the pinned beta SDK.
The CLI uses a fixed HTTPS endpoint and disables implicit LangSmith judge tracing.
Host-level proxies and environment instrumentation remain the operator's responsibility.
