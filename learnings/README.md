# Procurement RAG learning workspace

Start with [Lesson 0001: Find the failing layer](lessons/0001-find-the-failing-layer.html), or [Lesson 0002: React and FastAPI components](lessons/0002-react-fastapi-components.html) to inspect the application. Keep the [component map](reference/application-components.html) and [general + Azure reference](reference/rag-evaluation.html) open while inspecting the implementation. Both support light/dark themes, printing and offline use with the adjacent assets folder.

- `MISSION.md`: learning purpose and observable goals.
- `RESOURCES.md`: annotated sources and knowledge gaps.
- `NOTES.md`: teaching preferences and where to continue.
- `rag-evaluation-plan.md`: canonical engineering evaluation contract, moved from `docs/`; proposed gates remain proposed.
- `lessons/`: short practice lessons with immediate browser feedback.
- `reference/`: printable explanations, terminology and Azure mappings.
- `assets/`: shared styles, quiz and theme components.
- `learning-records/`: created only after demonstrated understanding. Reading a lesson does not create a record.

Machine-readable seed cases stay in [`../evals/cases.jsonl`](../evals/cases.jsonl). These teaching exercises do not call a model, execute the agent, measure RAG quality or change ticket status. No real evaluation runner is implemented by this material.

For the existing prototype server, run `python3 tools/build-learnings.py` from the project root, then visit `http://127.0.0.1:5173/learnings/index.html`. The script publishes a generated copy of this folder to the prototype's public directory; edit sources here and rerun after changes. Project-document links in that copy are supplied as reference downloads.

Suggested next session: attempt the three lesson questions and explain your reasoning to the agent. Revisit them from memory tomorrow and again next week. Then label the first real retrieval case together.
