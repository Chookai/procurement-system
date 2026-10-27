# Historical workflow research · 23 October 2026

Superseded as the current handoff choice by [the Kilo Desktop workflow](development-agent-workflow.md), accepted 27 October 2026. Package/model/authentication observations below are historical and have not been revalidated for the Kilo setup.

# Development agents: plan → implement → verify

User direction recorded 23 October 2026: GPT Sol handles architecture, implementation planning, specifications and tickets; a separate pi harness with a cheaper OpenRouter model implements and performs initial testing; GPT Sol then performs an independent testing/review pass through the Codex subscription. This changes the development workflow, not the procurement agent's runtime architecture. No application implementation is authorized by this research note.

## Current execution choice

Later on 23 October 2026, the user authorized implementation here and deferred configuring pi or Claude Code with OpenRouter. The original handoff design below remains an optional future workflow, not a restriction on the newly authorized implementation. The first PR application slice is documented in `first-application-slice.md`.

## Responsibilities and billing

| Stage | Harness and model | Result | Billing route |
|---|---|---|---|
| Plan | Codex app or CLI, selected GPT Sol model | Small executable ticket, contracts, acceptance scenarios, test commands and exclusions | ChatGPT/Codex subscription sign-in, subject to its limits |
| Implement | pi, explicitly selected OpenRouter coding model | Focused code change and initial test evidence | OpenRouter API credits |
| Independently verify | Fresh Codex session, GPT Sol | Actual test execution, additional edge cases, spec comparison and findings | ChatGPT/Codex subscription sign-in, subject to its limits |
| Repair and verify again | pi repairs; Codex independently verifies | Fix evidence and resolution of each finding | Each harness keeps its own billing route |

The production application and its live RAG evaluation calls still use separately billed provider APIs. A subscription-backed reviewer can inspect outputs and run the evaluation command, but it does not pay for the application's OpenRouter generation, embeddings or model-judge calls. Manual GPT review is not a versioned automated RAG quality score.

## Checked locally

- Installed Codex CLI: `0.163.0-alpha.11.2`.
- `codex login status` reports `Logged in using ChatGPT`.
- `pi` was not found on the checked WSL PATH; that does not establish whether it is installed elsewhere on Windows.
- This check did not launch pi, start implementation, install a harness, change authentication or run a second GPT model session.

## Start with a manual handoff

1. Have Codex refine one ticket. Keep the approved requirements and negative cases explicit. Existing backlog tickets are not all detailed enough for blind implementation.
2. Give pi the approved spec, selected ticket, applicable agent instructions and domain/architecture documents. Limit work to that ticket. Require a summary of changed files, exact test commands/results, limitations and unresolved questions. Tests or acceptance gates must not be weakened to make the change pass.
3. Stop pi editing before review. Use a fixed Git commit or otherwise a stable file snapshot; establishing Git is recommended before the first implementation handoff. Git was not initialized by this research step.
4. Start a fresh Codex session on that same snapshot. Have it run tests, compare behavior against the ticket, add independent negative scenarios and report reproducible findings. Ask it to report first, without implementing repairs.
5. Send findings to pi for fixes. Verify again in Codex. Only then mark implementation complete; end-of-phase user code inspection is still required.

## Authentication and commands

For Codex, keep ChatGPT sign-in rather than switching to an OpenAI API key:

```bash
codex login status
# If not signed in: codex login, then complete the browser sign-in.
codex -m gpt-6.1-sol
```

The official model guide lists `gpt-6.1-sol`; use the specific Sol version available to the account and client. The status check verifies sign-in, not every model's entitlement. In the desktop app, select the intended Sol model in the picker.

For pi, assuming the Pi project formerly named badlogic/pi-mono, now earendil-works/pi, start it in the project directory and authenticate interactively:

```text
pi
/login openrouter
/model
```

Select the OpenRouter model deliberately. Pi also accepts `OPENROUTER_API_KEY` from its process environment, but the backend's `.env` is not automatically the harness configuration. Prefer pi's login flow or a separately configured harness key with its own spend limit. No particular cheaper coding model has been benchmarked/selected yet.

Current upstream pi also exposes OpenAI ChatGPT subscription authentication in its OpenAI provider source; the old `openai-codex` provider is labelled legacy. If using that alternative, verify the installed version's `/login` and model list. It is not required for this user's proposed split, which keeps GPT planning and verification in Codex.

## Reviewer prompt

> Verify the specified ticket against the approved specification and completion gates. Execute the available tests; report exact commands and outcomes, including skips and missing dependencies. Inspect the implementation for authorization, state-transition, monetary/quantity, concurrency and persistence failures relevant to this ticket. Add independent edge cases rather than relying only on the implementer's tests. Do not modify application code or relax acceptance criteria. For each finding provide severity, file/line, reproduction and expected versus actual behavior. State what was not tested. Write repair recommendations for the pi implementer. Do not mark the milestone complete.

The reviewer may need to create independent tests and reports; that requires workspace writes even though application repairs are excluded. Prefer the interactive Codex app/CLI initially. Its permissions must support the actual local commands and dependencies; this WSL environment reported missing bubblewrap under the default shell sandbox, so sandbox configuration needs attention before unattended CLI testing is assumed to work.

## Later automation

After manual handoffs work, pi can call `codex exec` as a separate reviewer process, or integrate Codex app-server for sessions/events/approvals. The CLI command supports explicit model selection, JSON output and an output file. Continue using the authenticated local Codex workflow, and verify the authentication/usage route; do not assume an OpenAI/OpenRouter API call consumes subscription allowance. No automation or harness extension was installed here.

## Sources

- [Official OpenAI authentication documentation](https://learn.chatgpt.com/docs/auth): ChatGPT subscription sign-in versus separately billed API-key access.
- [Official Codex model guide](https://learn.chatgpt.com/docs/models?surface=app): Sol model IDs and availability qualifications.
- [Official Codex CLI reference](https://learn.chatgpt.com/docs/cli/reference): `exec`, model selection and output controls.
- [Official Codex app-server guide](https://learn.chatgpt.com/docs/app-server): integration surface for a future orchestrator.
- [pi provider documentation](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/providers.md): OpenRouter authentication and model discovery.
- [pi OpenAI provider source](https://github.com/earendil-works/pi/blob/main/packages/ai/src/providers/openai.ts): current ChatGPT subscription login option.
- [pi legacy Codex provider source](https://github.com/earendil-works/pi/blob/main/packages/ai/src/providers/openai-codex.ts): version-sensitive legacy naming.

Sources checked 23 October 2026. Source capabilities are not a claim that pi was installed or tested on this machine.
