Grade whether the competitive-research skill was invoked.

The prompt deliberately avoids the words "competitive", "competitor", and "analysis". The skill description is tuned to trigger on roadmap-shaped questions like this one. If it does not fire here, the plugin feels broken to a user who asked the most natural possible version of the question.

## Pass

- The competitive-research skill is invoked, and the response follows its workflow (starting with Phase 0 codebase discovery) rather than answering from general knowledge.

## Fail

- A generic product-strategy answer written without reading the codebase.
- Asking the user which competitors to look at before doing any discovery. The skill's promise is zero-config; the codebase is the source of truth.
- Invoking a different skill.

Partial credit if the skill is mentioned or offered but not actually run.
