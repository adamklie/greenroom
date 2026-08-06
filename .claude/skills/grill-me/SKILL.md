---
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when the user wants to stress-test a plan, get grilled on a design, or says "grill me". Usage: /grill-me [topic]
---

# /grill-me

Interview the user relentlessly about every aspect of the plan or design under
discussion until you reach a shared understanding. Walk down each branch of the
design tree, resolving dependencies between decisions one-by-one. For each
question, provide your recommended answer.

Ask the questions **one at a time**.

If a question can be answered by exploring the codebase, explore the codebase
instead of asking.

## How to run it here

1. **Anchor on the topic.** If the user passed a topic (e.g. `/grill-me chromia
   animation`), grill on that. Otherwise grill on the plan/design that is the
   active subject of the conversation.
2. **Build the decision tree first.** Privately enumerate the open decisions and
   their dependencies (what must be decided before what). Grill in dependency
   order — don't ask about leaf details before the trunk is settled.
3. **One question per turn.** Use the `AskUserQuestion` tool with 2–4 concrete
   options. Put your **recommended** option first and mark it `(Recommended)`.
   Keep going until every branch is resolved.
4. **Investigate before asking.** If the answer is discoverable (a file, a
   convention, an existing pattern, a schema), read it and state what you found
   instead of asking. Only ask the user what genuinely requires their judgment.
5. **Track and close.** After each answer, restate the decision in one line, note
   any new branches it opened, and move to the next. When the tree is fully
   resolved, summarize the locked decisions so the user can confirm.

Stop when there are no unresolved branches the user cares about, or when the user
says to stop.
