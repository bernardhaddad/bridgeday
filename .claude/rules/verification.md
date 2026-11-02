# What "done" means here

- A task is done when it is observed working: `make check` passes and, for
  anything with a UI or an endpoint, `make run` was exercised and the result
  was seen (screenshot, curl output, or log line quoted in the commit).
- Write the failing test first when the change is testable; watch it fail.
- Keep each change under ~100 lines where possible; commit after every green
  increment with a message that states the observed result.
- Do not widen scope: adjacent refactors go in `docs/plan.md` as new tasks.
