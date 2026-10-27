# Learning material validation

Checked 23 October 2026 against the existing Vite prototype server using headless Chrome through Playwright.

- Navigation from learning home to lesson works.
- Explicit light/dark theme survives navigation; toggling works.
- All three quiz questions show correct immediate feedback; incorrect choices also show feedback.
- Retrieval lab calculates two relevant results out of three as recall 100% and precision 67%; removing the irrelevant result raises precision to 100%.
- Three-result selection limit works.
- Print media hides navigation and controls.
- Home, lesson and reference have no page overflow at a 390px viewport.
- No browser page errors observed.
- Local HTML links and shared assets resolve in both canonical and generated folders.
- Desktop dark lesson and light reference screenshots, plus a mobile reference capture, saved under `../mockups/learnings-*.png`; desktop dark lesson visually inspected.

These checks verify the teaching pages, not the procurement application or real RAG quality. No paid provider calls or production evaluation runs were performed. Passing quiz checks does not record the user's learning.

## Lesson 02 and application component reference

Checked 23 October 2026 in headless Chrome. All six walkthrough steps switch correctly; all four questions provide correct feedback and tailored hints. Print mode exposes all walkthrough steps. Theme choice persists between lesson and reference. Both new pages fit a 390px viewport without page overflow. All local links/assets resolve in canonical and published folders, and every new answer option contains one word. Existing lesson 01 feedback still works. No browser page errors observed; the desktop dark lesson was visually inspected. These are teaching-page checks, not new application or learner-mastery results.

## Lesson 03

Checked all three two-word-option quizzes, print controls and mobile page overflow in Chrome. Local HTML links resolve after publishing; the component map was updated for shared types and PurchaseOrderForm. No browser errors observed. These checks do not establish learner mastery.

## Lesson 04 · 24 October 2026

Chrome verified all three state walkthrough buttons, all three quiz feedback paths for correct answers, theme toggle, print visibility (all walkthrough stages shown, navigation hidden), 390px page width and no page errors. The local-link scan covers canonical and published files. Every quiz option in lesson 04 uses two words, with correct positions varied. These checks establish teaching-page behavior, not learner mastery or RAG quality.

## Lesson 05 · 26 October 2026

Verified in Chrome: all walkthrough states, three correct quiz feedback paths, varied answer positions with two-word options, light/dark toggle, print navigation hidden and all stages visible, 390px width without overflow, and no page errors. Canonical/published local links validated. These are material checks, not learner mastery or RAG quality evidence.

## Lesson 06 · 26 October 2026

Chrome verified all three walkthrough stages and correct quiz feedback paths, light/dark toggle, print navigation hidden and all stages exposed, 390px width without page overflow, and no page errors. Answer options use two words with varied correct positions. Canonical/published links validated. No learner mastery is inferred.

## Agent workflow report · 27 October 2026

Verified three role cards, all four walkthrough stages, implementer/verifier clipboard prompts, handoff template download, theme switching, print visibility of all stages, 390px layout and no page errors. All 22 canonical/published HTML pages passed local-link checks. These are report controls only; no Kilo task, verifier session or automatic handoff was executed.
