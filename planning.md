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
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): ...
- `size` (str): ...
- `max_price` (float): ...

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): ...
- `wardrobe` (dict): ...

**What it returns:**
<!-- Describe the return value -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): ...
- `new_item` (dict): ...

**What it returns:**
<!-- Describe the return value -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | |
| suggest_outfit | Wardrobe is empty | |
| create_fit_card | Outfit input is missing or incomplete | |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     Use ASCII art or a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html).
     Do NOT embed an image — graders need to read your diagram directly in the file;
     an embedded image or screenshot cannot be evaluated.
     You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

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

**Milestone 4 — Planning loop and state management:**

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
