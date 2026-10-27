# System architecture delivery

- diagram_type: architecture
- output: /mnt/c/Users/choos/Desktop/Procurement System/mockups/system-architecture.html
- specification: system-architecture-openrouter.json
- specification_sha256: 93a43597a53796aa5c89675d75481397c15cf56d67a0d8f09dec62c81f70406e
- specification_bytes: 4533
- artifact_sha256: 82e30b9d6f862c1bcf1eb06baee76fc2213e878624049af217ceab473655f2b4
- artifact_bytes: 713588
- validation: 9/9 showcase, 0 errors, 0 warnings
- browser_evidence: passed
- visual_review: passed
- correction_rounds: 0 for the OpenRouter revision

The earlier tall layout passed deterministic checks but failed desktop browser containment. The final compact specification above supersedes that layout. Its artifact-bound browser receipt is `system-architecture.visual-check.json`: 1440×900, 1600×1000, 1920×1080 and 2048×1320 all pass containment. Light/dark captures at the endpoint sizes were inspected for labels, routes, node fit, component separation and overall balance. Search, export and every viewer interaction have not been exhaustively tested.

This is a proposed system design, not deployed infrastructure or a verified provider integration. Agent Framework is an in-process backend module. The queue box represents PostgreSQL jobs first and an external Azure queue later; Redis remains optional. The more detailed Mermaid dependency map in `docs/architecture-direction.md` records retrieval, embeddings and telemetry paths that are summarized in this overview.

The OpenRouter-first revision replaces the Foundry component with the local evaluation runner. Foundry is deferred. This revision preserves the accepted compact geometry and re-ran all deterministic and browser checks.
