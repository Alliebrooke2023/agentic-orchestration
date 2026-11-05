# Per-User Agent Preference Memory

* **Author:** (fill in)
* **Date:** 2026-11-01

## Overview

Agents forget user preferences between chats. This feature gives each user a
private list of preferences for each agent, stored in Supabase. When a
playground chat starts, the chat route loads that list and gives it to the
model as context. A preference is saved when the user says "remember this".
Later, the agent may also propose preferences it notices on its own. The user
can view, edit and delete every entry.

Scope: user preferences only. Per user, per agent. Playground first. Supabase
only, no new paid services.

## Analysis

Review status: the six EGM lenses plus six extra lenses were run by one
reviewer in sequence, not as six independent subagents. Treat the findings as
one author's critique. Two of the claims were re-checked against the code and
hold (see Blockers).

### Blockers found in the code

1. **The playground does not use Supabase today.** The chat route
   (`src/app/api/playground/chat/route.ts`) reads agents from an in-memory
   `store` (`src/lib/store.ts`). Agent ids are strings like `research-agent`,
   not UUIDs, so a foreign key to `public.agents` will not work. The Supabase
   agent code (`src/lib/db/agents.ts`) is not used by the routes. Runs are also
   in memory.
2. **No path from the logged-in user to a Supabase user.** Login is NextAuth
   (GitHub). The session reads `supabaseAccessToken` but nothing sets it, and
   the server client uses the anon key. Row-level security based on
   `auth.uid()` cannot identify the user. Existing policies are per workspace,
   so copying them would let any workspace member read another member's
   preferences.
3. **No playground UI exists in the repo.** The view/delete screen has nowhere
   to attach yet.

### Risks

* **Prompt injection through memory.** A saved entry is re-sent on every future
  chat. One poisoned entry persists. Tool output (web search, files) must never
  trigger a save. Entries go in a labelled block marked as untrusted user data,
  not appended to the system prompt.
* **Wrong auto-captured entries.** The model may save a joke, a one-off
  constraint or a stale statement. The user may not notice until the agent
  behaves oddly.
* **Token growth.** Loading the whole list on every turn costs tokens linearly.
  Rough estimate: 20-40 tokens per entry (not measured).
* **Privacy.** Preferences can contain personal data. Log ids and counts, never
  the text.
* **Debuggability.** Nothing records which preferences were in context for a
  given answer.
* **Rate limit.** The existing limiter is per IP and optional, not per user.

### The three working assumptions

1. **Load the whole list every chat.** Acceptable only with hard caps (entry
   count, entry length, total budget) and a stable ordering so prompt caching
   works. Add retrieval only when users hit the cap.
2. **Success = a preference set in one chat applies in a fresh chat.** Too weak.
   Also test: deleted entries stop applying, user B never sees user A's
   entries, a newer entry overrides a contradicting older one, an "ignore
   previous instructions" entry has no effect, and a database failure does not
   break the chat.
3. **Auto-captured entries are visibly marked.** Not enough. Store the source in
   the data, show "used N saved preferences" in the chat itself, and have the
   agent state what it saved. Strongest fix: auto entries stay pending until
   the user accepts them.

## Goals vs. Non-Goals

* **In-Scope Goals:**
  * A user can tell an agent to remember a preference. It applies in later
    chats with that agent without a reminder.
  * Memory is private to the user. No other user can read, change or delete it.
  * The user can see, edit and delete every entry, with its source. Deletion
    takes effect on the next chat.
  * Each chat shows which saved preferences were used.
  * Chat works normally if memory is off, empty, over its cap or the database
    is down.
  * Cost is bounded by an entry cap and a fixed injection budget.
* **Out-of-Scope Non-Goals:**
  * Workflows, cross-user or cross-agent sharing, external vector services.
  * Retrieval, ranking, summarisation, embeddings.
  * Auto-capture in the first release.
  * Saving from tool output, files or any non-user message.
  * Moving the whole agent store to Supabase (only the minimum needed for a
    stable agent id).
  * Guaranteeing the model obeys a preference. The guarantee is that it is in
    context.

## Alternatives Weighed

* **A. Full proposal at once (explicit + auto, whole list).** Rejected as a
  first step. Highest risk and depends on both blockers.
* **B. Explicit "remember this" only, capped whole list.** Recommended first
  release. Removes wrong guesses and tool-output poisoning.
* **C. A per-agent notes text field the user edits.** Least code, no
  model-driven writes. Kept as the fallback if the identity work slips.
* **D. Auto-capture with pending confirmation.** Second release, after B is
  stable.
* **E. pgvector retrieval in Supabase.** Deferred until lists hit the cap.
* **F. Derive memory from run history (`runs.messages`).** Rejected. Runs are
  in memory today, summaries drift and are hard to correct.
* **G. Per-workspace shared memory.** Rejected. Leaks between members and
  breaks the "private" requirement.

## Key Decisions & Staging for Next Steps

Open (need the owner's call):

1. **Identity.** Either set a Supabase token in the NextAuth `jwt` callback and
   use RLS on `auth.uid()`, or use a server-only admin client with a mandatory
   `user_id` filter in one module, with tests.
2. **Canonical agent id.** Either move the chat route onto `src/lib/db/agents.ts`
   (UUID ids), or key memory by the existing string id with no foreign key and
   a cleanup plan. Check on every request that the agent belongs to the caller.
3. **Conflict rule.** Newer entry replaces an older one on the same topic, or
   both are kept and shown.
4. **Limits.** Entry count, length and total budget. Choose numbers from real
   usage. On hitting a limit: reject the new entry, never silently drop.
5. **Mock mode.** With no Supabase env vars, memory is off with a clear message.

Proposed:

* Release 1 = option B. Release 2 = option D.
* Entries injected as a labelled untrusted-data block in deterministic order.
* Minimum table: `id`, `user_id`, `agent_id`, `content`, `source`
  (`user_command` | `auto`), `status` (`active` | `pending`), `created_at`,
  `updated_at`, `source_message_id`. Added as a new numbered script after
  `005`, additive only, flag-guarded.
* Per-chat log: agent, user id, injected count, approximate size, item ids. Per
  write log: source and message id. No memory text in logs.
* A memory load or save failure never fails the chat.
* A per-chat toggle to start with memory off, for testing.
* Tests first: cross-user isolation, injection resistance, delete then fresh
  chat, caps, database-down path.
