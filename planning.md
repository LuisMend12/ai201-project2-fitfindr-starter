# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset (`data/listings.json` via `load_listings()`) for items matching free-text keywords, an optional size, and an optional price ceiling, returning matches ranked by relevance.

**Input parameters:**
- `description` (str): Free-text keywords describing what the user wants (e.g. `"vintage graphic tee"`). Tokens are compared against each listing's `title`, `description`, and `style_tags` to compute a relevance score.
- `size` (str | None): Size string to filter by, case-insensitive substring match against the listing's `size` field (e.g. `"M"` matches `"S/M"`). `None` skips size filtering.
- `max_price` (float | None): Maximum price, inclusive. `None` skips price filtering.

**What it returns:**
A `list[dict]` of matching listings, sorted by relevance score (highest first). Each dict is a full listing record: `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand` (str or `None`), `platform`. Listings with zero keyword overlap with `description`, or that fail the `size`/`max_price` filters, are dropped entirely — not included at the bottom with a score of 0.

**What happens if it fails or returns nothing:**
Returns `[]` — never raises an exception. The planning loop checks for an empty list after calling this tool, sets `session["error"]` to a specific message (what was searched, and a concrete suggestion like loosening the price/size filter or using broader keywords), and returns the session immediately without calling `suggest_outfit` or `create_fit_card`.

---

### Tool 2: suggest_outfit

**What it does:**
Given a candidate item (the item the user is considering) and the user's wardrobe, asks the LLM (Groq `llama-3.3-70b-versatile`) to suggest 1–2 complete outfits pairing the new item with the user's existing pieces — or, if the wardrobe is empty, general styling advice for the item on its own.

**Input parameters:**
- `new_item` (dict): A listing dict in the same shape returned by `search_listings` — the item under consideration.
- `wardrobe` (dict): A wardrobe dict with key `"items"` containing a list of wardrobe item dicts (`id`, `name`, `category`, `colors`, `style_tags`, `notes`). `wardrobe["items"]` may be `[]`.

**What it returns:**
A non-empty `str` with the LLM's suggestion. When the wardrobe has items, the suggestion names specific wardrobe pieces by name (e.g. "your wide-leg jeans and platform Docs"). When the wardrobe is empty, the suggestion describes general styling direction (what kinds of pieces, colors, or vibes would pair well) instead.

**What happens if it fails or returns nothing:**
If `wardrobe["items"]` is empty, the tool does not error or return an empty string — it builds a different prompt (general styling advice instead of specific pairings) and still returns a non-empty string from the LLM. This is a normal branch, not a failure the planning loop needs to catch.

---

### Tool 3: create_fit_card

**What it does:**
Given an outfit suggestion string and the new item, asks the LLM to write a short, casual, shareable social-media caption (2–4 sentences) announcing the thrifted find and how it's styled.

**Input parameters:**
- `outfit` (str): The outfit suggestion string returned by `suggest_outfit()`.
- `new_item` (dict): The listing dict for the thrifted item being captioned.

**What it returns:**
A 2–4 sentence `str` written like a real OOTD caption — mentions the item name, price, and platform once each, and captures the outfit's vibe in specific terms. Uses a higher LLM temperature so repeated calls on the same input produce different wording each time.

**What happens if it fails or returns nothing:**
If `outfit` is empty, `None`, or whitespace-only, the tool does not call the LLM — it returns a descriptive fallback string (e.g. `"Can't create a fit card — no outfit suggestion was provided."`) instead of raising an exception. In the normal planning loop this branch should never trigger, since `suggest_outfit` always returns a non-empty string before `create_fit_card` is called — this guard exists for when `create_fit_card` is tested in isolation with a missing/blank `outfit`.

---

### Additional Tools (if any)

None — three tools are sufficient for the required interaction (search → suggest → caption).

---

## Planning Loop

**How does your agent decide which tool to call next?**

The loop is a fixed sequence with one conditional branch point, not a free-form decision — each step's output determines whether the next tool runs at all:

1. Initialize the session with `_new_session(query, wardrobe)`.
2. Parse `query` into `description`, `size`, `max_price` and store in `session["parsed"]`.
3. Call `search_listings(**session["parsed"])`. Store the return value in `session["search_results"]`.
   - **If `session["search_results"] == []`:** set `session["error"]` to a specific message and `return session` immediately. `suggest_outfit` and `create_fit_card` are never called.
   - **If `session["search_results"]` is non-empty:** set `session["selected_item"] = session["search_results"][0]` and continue.
4. Call `suggest_outfit(new_item=session["selected_item"], wardrobe=session["wardrobe"])`. Store the result in `session["outfit_suggestion"]`. (No branch needed here — this tool is specced to always return a non-empty string, even for an empty wardrobe.)
5. Call `create_fit_card(outfit=session["outfit_suggestion"], new_item=session["selected_item"])`. Store the result in `session["fit_card"]`.
6. Return `session`. The loop is done once `fit_card` is set (3 tool calls succeeded) or once it returned early after step 3 (1 tool call, `error` set).

There's no looping/retrying — each tool is called at most once per `run_agent()` call.

---

## State Management

**How does information from one tool get passed to the next?**

A single dict (created by `_new_session()`) is the only state container for one interaction — there's no class, no global variables, and no state that outlives one call to `run_agent()`. Its fields:

- `query` — the original user string, set once at init and never modified.
- `parsed` — `{description, size, max_price}` extracted from `query`; read by `search_listings`.
- `search_results` — the list returned by `search_listings`; read to check for the empty case and to pick `selected_item`.
- `selected_item` — `search_results[0]`; passed as `new_item` into both `suggest_outfit` and `create_fit_card`.
- `wardrobe` — passed in by the caller of `run_agent`, read by `suggest_outfit`.
- `outfit_suggestion` — the string returned by `suggest_outfit`; passed as `outfit` into `create_fit_card`.
- `fit_card` — the string returned by `create_fit_card`; the final user-facing output.
- `error` — `None` unless the loop terminated early; checked first by any caller of `run_agent`.

Each tool only ever reads fields already written by an earlier step and writes back exactly one new field — the dict is threaded through `run_agent()` step by step, never passed into the tools themselves (the tools take plain arguments, not the session dict).

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | `search_listings` returns `[]`. The planning loop sets `session["error"]` to a message naming what was searched and what to try, e.g. `"No listings matched 'vintage graphic tee' under $30. Try raising your budget, dropping the size filter, or using a broader term like 'tee' instead of a specific style."`, then returns the session immediately — `suggest_outfit` and `create_fit_card` are never called. |
| suggest_outfit | Wardrobe is empty | `suggest_outfit` checks `wardrobe["items"]` before building its prompt. If empty, it asks the LLM for general styling advice for `new_item` alone (vibe, what kinds of pieces would pair well) instead of advice referencing specific wardrobe items, and still returns that non-empty string. The planning loop treats this exactly like the normal case — it is not an error, so `session["error"]` stays `None` and the loop proceeds to `create_fit_card`. |
| create_fit_card | Outfit input is missing or incomplete | `create_fit_card` checks whether `outfit` is `None`, `""`, or whitespace-only before calling the LLM. If so, it returns a descriptive string, e.g. `"Can't create a fit card — no outfit suggestion was provided."`, instead of raising or calling the LLM. In the wired-up `run_agent()` flow this should never actually trigger (step 4 always populates `outfit_suggestion` first), so it matters mainly when `create_fit_card` is tested directly with a blank `outfit` in isolation. |

---

## Architecture

```
User query
    │
    ▼
Parse query → session.parsed = {description, size, max_price}
    │
    ▼
Planning Loop ──────────────────────────────────────────────────────────────┐
    │                                                                       │
    ├─► search_listings(description, size, max_price)                      │
    │       │                                                              │
    │       │ results = []                                                 │
    │       ├──► [ERROR] session.error = "No listings matched '<query>'    │
    │       │            under $<max_price>. Try a higher budget,          │
    │       │            dropping the size filter, or broader keywords."   │
    │       │            ───────────────────────────────────► RETURN session
    │       │                                                              │
    │       │ results = [item, ...]                                       │
    │       ▼                                                              │
    │   session.search_results = results                                   │
    │   session.selected_item  = results[0]                                │
    │       │                                                              │
    ├─► suggest_outfit(selected_item, wardrobe)                            │
    │       │                                                              │
    │       │ wardrobe["items"] == []                                      │
    │       │   → LLM prompt: general styling advice for selected_item     │
    │       │ wardrobe["items"] != []                                      │
    │       │   → LLM prompt: pair selected_item with named wardrobe items │
    │       ▼                                                              │
    │   session.outfit_suggestion = "<LLM outfit text>"                    │
    │       │                                                              │
    ├─► create_fit_card(outfit_suggestion, selected_item)                  │
    │       │                                                              │
    │       │ outfit_suggestion empty/whitespace → fallback string,        │
    │       │   no LLM call                                                │
    │       │ outfit_suggestion present → LLM prompt: write caption        │
    │       ▼                                                              │
    │   session.fit_card = "<LLM caption text>"                            │
    │       │                                                              │
    └───────┴──────────────────────────────────────────────────► RETURN session
                                                                  (error=None)

Session State (single dict threaded through every step above):
  query, parsed, search_results, selected_item, wardrobe,
  outfit_suggestion, fit_card, error
```

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

I'll use Claude (Claude Code), one tool at a time, in this order: `search_listings`, `suggest_outfit`, `create_fit_card`. For each one, I'll give it only that tool's spec block from the **Tools** section above (what it does, exact input parameters, return shape, failure mode) plus the existing docstring/TODO already in `tools.py`, and ask it to implement just that function — using `load_listings()` from `utils/data_loader.py` for `search_listings`, and the existing `_get_groq_client()` helper for the LLM-backed tools. Before trusting any generated function, I'll check: does the signature match the spec exactly (parameter names, types, defaults)? Does it handle the documented failure mode without raising? For `search_listings`, I'll manually trace 3 queries against `data/listings.json` to sanity-check the returned items and ordering. For `suggest_outfit` and `create_fit_card`, I'll run each twice with identical input and confirm the wording differs, and that the empty-wardrobe / empty-outfit branches behave exactly as specced. Only after a tool's `pytest` tests pass do I move to the next one.

**Milestone 4 — Planning loop and state management:**

I'll give Claude the **Planning Loop**, **State Management**, and **Architecture** sections above and ask it to implement `run_agent()` in `agent.py` following the 6 numbered steps exactly — parse, search, branch on empty results, select the top item, call `suggest_outfit`, call `create_fit_card`, return the session. I'll verify the result by running the two CLI scenarios already stubbed at the bottom of `agent.py` (happy path and no-results path) and confirming `session["error"]` is `None` vs. set correctly in each case, and that `suggest_outfit`/`create_fit_card` are never invoked when `search_results` is empty.

---

## A Complete Interaction (Step by Step)

FitFindr takes a user from a thrifting query to a shareable outfit post in three chained tool calls: it searches the mock listings for an item matching the user's description, size, and budget, then asks an LLM to suggest how to style that item against the user's existing wardrobe (or with general advice if the wardrobe is empty), and finally turns that suggestion into a casual, shareable caption. `search_listings` fires on the user's initial query; `suggest_outfit` fires only once a listing has actually been found; `create_fit_card` fires only once an outfit suggestion exists. If `search_listings` comes back empty, the agent stops immediately, tells the user what to adjust (loosen the size or price filter, try different keywords), and never calls `suggest_outfit` or `create_fit_card` with empty input.

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent parses the query into `description="vintage graphic tee"`, `size=None` (no size was mentioned), `max_price=30.0`, then calls `search_listings("vintage graphic tee", size=None, max_price=30.0)`. Against `data/listings.json`, the top match is `lst_006`, "Graphic Tee — 2003 Tour Bootleg Style" — $24, Depop, good condition (its title and tags overlap most heavily with "vintage," "graphic," and "tee"). The agent stores the full result list in `search_results` and selects this top hit as `selected_item`.

**Step 2:**
The agent calls `suggest_outfit(new_item=<lst_006>, wardrobe=<user's wardrobe>)`. The user's wardrobe (the example wardrobe) already contains `w_001` "Baggy straight-leg jeans, dark wash" and `w_007` "Chunky white sneakers" — a direct match for what the user said they wear. The LLM returns a suggestion pairing the bootleg tee with those two pieces, e.g. tucking the tee loosely into the baggy jeans and finishing with the chunky sneakers for a 90s streetwear look. This string is stored in `outfit_suggestion`.

**Step 3:**
The agent calls `create_fit_card(outfit=<suggestion from Step 2>, new_item=<lst_006>)`. The LLM generates a short, casual caption that mentions the item name, the $24 price, and Depop once each, and captures the streetwear vibe of the outfit. This string is stored in `fit_card`.

**Final output to user:**
The user sees the outfit suggestion plus the ready-to-post fit card caption, with `session["error"]` left as `None`. Nothing about a failed search or an empty wardrobe surfaces here, since this query succeeds at every step.
