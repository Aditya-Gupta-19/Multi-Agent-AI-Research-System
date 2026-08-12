# Multi-Agent AI Research System — Build Log & Interview Prep

Internal companion to the public learning guide (published as a Claude Artifact, linked from chat each module). This file is the one that stays with the repo: a plain-words explanation of every decision, a running log of what was actually built and why, and an interview question bank that grows as the project grows. Read `## How this file works` once, then jump to whatever section matches where the project currently is.

Status: **Modules 1–3 complete. Module 4 roadmap locked. Writing Step 1 (scaffolding + state.py) next.**

---

## How this file works

- **Modules 1–3** (Concepts, Architecture, Interview Prep) get a plain-words recap here plus an interview Q&A block — the full depth lives in the published artifact, this is the durable, versioned reference.
- **Module 4** (Implementation) is logged step by step as we build: what was added, which files, which tools/features, why that choice over the alternatives, how to run it, how to demo/test it, and the interview questions that specific step answers. New entries append under `## Module 04 — Implementation Log`; nothing here gets rewritten after the fact except to fix errors.
- Every commit that lands a build step should reference its entry here (e.g. `feat: add supervisor node — see .docs/BUILD_LOG.md#step-1`).

---

## Module 01 — Concepts & Foundations (recap)

**What we're building:** a research assistant made of several small AI agents instead of one big one — a Supervisor that routes work, a Researcher that searches, an Analyst that judges/synthesizes findings, and a Writer that produces the final report. Running entirely on a local model via **Ollama** (no API cost, no data leaving the machine).

**In plain words:**

- An **agent** = an LLM in a loop that can call real functions ("tools") and decides for itself when it's done, instead of just answering once.
- **Multi-agent** = splitting one big fuzzy job into several small focused jobs, each with its own short prompt and its own tools, coordinated by a **Supervisor** agent that decides who goes next.
- **LangChain** gives us the small parts: prompts, the model connection, tools, and a way to force the model's reply into a structured object instead of loose text.
- **LangGraph** gives us the wiring: a shared state object, and a graph of steps that — unlike a plain LangChain chain — can loop back and can decide the next step at run time instead of at write time. That's the piece that makes a Supervisor possible at all.
- Four reasoning patterns matter here: **ReAct** (think→act→observe, repeat — used inside the Researcher), **Plan-and-Execute** (plan fully up front, then run it — named for contrast, not used as the top-level control here), **Reflection** (critique your own output, redo if it's weak — optional pass after the Writer), **Supervisor** (a hub agent routing to specialists — the backbone of the whole system).
- **Memory** is three different things: working memory (this run only), short-term/session memory (checkpointed state, survives follow-up questions), long-term memory (a vector store, survives across sessions — this is what makes it RAG).
- Running tool-calling through **Ollama** instead of a hosted API is the single biggest reliability trade-off in this build — local models are more likely to emit a malformed tool call, so retry/repair logic isn't optional here the way it might be with GPT-4o or Claude.

Full version with diagrams: see the published artifact linked in chat (Module 1: Concepts & Foundations).

### Interview Q&A — Module 1 concepts

**Q: What's the actual difference between a "chain" and an "agent"?**
A: A chain runs a fixed sequence decided when you write the code — prompt in, model, parser, done. An agent decides its *own* next step at run time, in a loop, based on what happened last step. A chain can't change its mind mid-run; an agent can.

**Q: Why not just build this as one agent with four tools instead of four agents?**
A: Because the four jobs (search, judge sources, synthesize, write) need different prompts, different context, and fail in different ways. Cramming all four into one system prompt and one context window makes debugging a specific failure ("bad sources" vs "bad writing") much harder, and it's easy for one instruction to quietly override another. The honest cost of splitting them up is more LLM round-trips and a coordinator (the Supervisor) to manage hand-offs — it's a real trade-off, not a free win, and worth saying that plainly in an interview rather than overselling multi-agent as strictly better.

**Q: Why LangGraph instead of plain LangChain?**
A: Plain LangChain's LCEL chains are directed acyclic graphs decided at write time — no loops, no run-time branching. A Supervisor pattern needs both: it has to loop (send work back to a specialist) and branch based on live state (which agent runs next depends on what came back, not on what the code said in advance). LangGraph adds a stateful graph — nodes, edges, and conditional edges — specifically to support that.

**Q: What breaks first when you swap a hosted LLM API for a local Ollama model?**
A: Tool-calling reliability. Hosted frontier models are fine-tuned hard to emit schema-correct function calls; smaller/quantized local models occasionally emit malformed calls. That turns "add a retry/repair step around tool invocation" from a nice-to-have into a required part of the design. The upside is zero per-token cost and everything staying on-machine — a genuine trade-off depending on whether you're optimizing for reliability or for cost/privacy.

**Q: Why use Ollama at all instead of just calling OpenAI or Anthropic's API?**
A: Cost (no per-token billing while iterating on a learning project), privacy (nothing leaves the machine, relevant if the "research" ever touches sensitive documents), and it forces the design to be honest about tool-calling reliability instead of getting a free pass from a very well-tuned hosted model. The trade-off — weaker tool-calling, need for local compute/GPU, smaller effective context in some models — gets its own full treatment in Module 3.

*(This Q&A block grows as later modules land — architecture, system design, and performance/security questions get appended under their own modules below.)*

---

## Module 02 — Architecture (HLD & LLD) — recap

**High-level design:** four agents, each with a narrow job. The Supervisor owns *zero* tools — it only reads state and routes; giving it tools would let it quietly start doing research work no other agent's output review would catch. The Researcher is the only agent running a ReAct loop against a real tool (`web_search`). The Analyst is pure reasoning — it scores and deduplicates findings, no tools. The Writer turns scored findings into the final report, with an optional Reflection hand-back to the Supervisor if the draft is thin.

**Sequence for one query:** User → Supervisor → Researcher (ReAct loop, capped) → Supervisor → Analyst → Supervisor → Writer → Supervisor → User. Nine hand-offs, each one a real LLM call — worth remembering when reasoning about latency/cost, since a single research question costs at minimum ~4 LLM calls (Supervisor routes 4 times) plus however many search iterations the Researcher takes.

**Low-level design — the concrete pieces:**
- **State schema**: a `ResearchState` TypedDict — `question`, `findings` (a list using an `add` reducer so new findings *append* instead of overwriting), `report`, `next_agent`, `iterations`.
- **Nodes** return only the state keys they changed; LangGraph merges the rest via each field's reducer.
- **Routing** is a plain function (`route_after_supervisor`) that inspects state and returns a string naming the next node — the concrete mechanism behind "conditional edges" from Module 1.
- **Search tool**: DuckDuckGo (`ddgs` package) by default — free, no API key, consistent with why Ollama was chosen in the first place. Tavily is the named paid alternative (better structured, pre-ranked results) for when reliability matters more than cost.
- **Guardrails**: an iteration cap on the Supervisor's loop (forces a final answer instead of looping forever), tool-call retry/repair around Ollama's occasional malformed calls, a per-node timeout, and schema validation at the Researcher→Analyst hand-off so bad data fails loud immediately instead of corrupting the report three steps later.
- **Observability**: not wired up by default (local-first build), but LangSmith tracing (`LANGCHAIN_TRACING_V2=true`) is the real answer to "how would you debug a bad run" — inspect the trace, don't grep terminal logs.
- **Ollama's place in the stack**: a local server (`localhost:11434`); `ChatOllama` is just a LangChain client pointed at it. Because every node is written against LangChain's shared `Runnable` interface, swapping to a hosted provider later is a one-line change (`ChatOllama(...)` → `ChatAnthropic(...)`) — nothing downstream of `llm` knows or cares which provider backs it.

Full version with the sequence diagram and code snippets: see the published artifact (Module 2: Architecture — HLD & LLD).

### Interview Q&A — Module 2 architecture

**Q: Walk me through what happens for one user query, end to end.**
A: The question goes to the Supervisor, which routes to the Researcher. The Researcher runs a capped ReAct loop — search, look at results, decide whether to search again — until it's confident or hits its step cap, then reports findings back to the Supervisor. The Supervisor sends those findings to the Analyst, which scores and deduplicates them with no tools of its own, purely reasoning over the data. The Supervisor sends the scored findings to the Writer, which drafts the report. The Writer hands the draft back to the Supervisor, which either returns it to the user or — if a Reflection pass is enabled and the draft is weak — routes back for another research round.

**Q: Why does only one agent (the Researcher) actually call tools?**
A: Because tool-calling is where local models are least reliable (see Module 1's Ollama caveat), and it's the one capability that should be isolated and hardened with retry/repair logic rather than duplicated across every agent. It also keeps the Supervisor and Analyst's failure surface small and easy to reason about — if the report is wrong, it's either a research problem or a reasoning problem, never "which of four tool-callers misfired."

**Q: What's a "reducer" in LangGraph state, and why does the findings field need one?**
A: A reducer tells LangGraph how to combine a node's returned update with existing state instead of blindly overwriting it. `findings` uses `Annotated[list[Finding], add]` so each Researcher turn appends to the list. Without it, a second Researcher turn would replace the first turn's findings outright, since multiple nodes write to that field over the course of one run.

**Q: What stops this system from looping forever?**
A: A hard iteration cap in the Supervisor's routing function — once `iterations >= MAX_ITERATIONS`, the router forces `"writer"` regardless of whether the Researcher feels done. It's a deliberate quality/termination trade-off: better to answer with imperfect evidence than never answer at all.

**Q: Why DuckDuckGo over Tavily for the search tool, given this is meant to be a serious project?**
A: Consistency, not cost-cutting for its own sake — Ollama was chosen specifically to remove per-call cost and external dependency from the stack; picking a paid search API right after would undercut that same reasoning. Tavily is explicitly named as the better production option (cleaner, pre-ranked, structured results) — the honest framing is "I optimized for zero marginal cost end-to-end, and this is the one place that trade-off costs some result quality," which is a defensible engineering trade-off, not an oversight.

**Q: How would you debug a bad output in production if you can't just re-run it and watch the terminal?**
A: LangSmith tracing — every node call, tool call, and state transition for a specific run becomes inspectable after the fact via `LANGCHAIN_TRACING_V2`. That's the real answer; local development for this project skips it by default but the design is compatible with turning it on.

*(Grows further once Module 3 does the full system-design and trade-off grind.)*

## Module 03 — Interview Prep (full grind) — recap

**The four-beat narrative** (for "tell me about a project you're proud of"): Problem — a single prompt/agent doing search, judgment, synthesis, and writing at once fails in ways that are hard to localize. Approach — split into four specialists behind a Supervisor, orchestrated with LangGraph for run-time routing, on Ollama for a free, self-contained stack. Outcome — a working system where every decision traces to a stated trade-off. What I'd change at scale — swap the search tool and LLM (both one-line changes by design) and turn on observability.

**Tech stack vs. alternatives:** LangGraph was chosen over CrewAI/AutoGen/a hand-rolled loop specifically because the core challenge here — a Supervisor making run-time routing decisions over shared, typed state — is exactly the problem `StateGraph` exists to solve. CrewAI's higher-level "crew" abstraction is faster to prototype but weaker at expressing conditional, cyclical routing. AutoGen's conversational agent-to-agent chat loop suits open-ended dialogue better than a fixed pipeline of typed hand-offs. Hand-rolling avoids dependency risk but means re-implementing state merging and routing — effort better spent on the agents themselves.

**Local vs. hosted LLM, quantified honestly:** Ollama wins on cost (free after hardware) and privacy (nothing leaves the machine); hosted APIs win on tool-calling reliability, latency consistency, and context/reasoning depth. The decision framework: local when optimizing for cost/privacy and retry logic can absorb weaker tool-calling (this project); hosted the moment reliability or reasoning quality becomes the bottleneck. The one-line swap (Module 2, §2.8) means this isn't a permanent bet.

**Multi-agent, quantified:** this design costs roughly 4 extra LLM calls per query just for Supervisor routing, on top of the Researcher's ReAct turns — the real, sayable price of separation of concerns. Justified when roles genuinely need different context/tools (true here); overengineering when "specialist" agents end up needing the same context and tools anyway.

**Scaling to production** would require: concurrency handling in front of a single Ollama instance (queue or replicas), leaning on LangGraph's already-externalized checkpointed state to resume runs on different workers, a semantic cache over repeated questions, rate limiting on the search tool and model server, and observability (LangSmith) moving from optional to mandatory.

**Evaluation & hallucination handling:** a golden question set with known-good reference findings re-run on every prompt/model change; groundedness checks (every report claim should trace to a `Finding.source` — an unsupported claim is a checkable hallucination signal); the Analyst's `confidence` field surfacing uncertainty instead of smoothing it over; periodic human spot-checks for what automated checks miss.

**Failure modes → mitigations** (all designed alongside the failure, not bolted on after): infinite Researcher loop → iteration cap; malformed Ollama tool call → retry/repair; bad Researcher output → schema validation at the hand-off; unsupported report claims → groundedness check; hung node → per-node timeout; lost findings → the `add` reducer (append, never overwrite).

**Security:** prompt injection via untrusted search-result content (mitigated by treating tool output as evidence to evaluate, never as instructions to follow); secrets in a gitignored `.env`, never hardcoded; local-first privacy since nothing leaves the machine by default; and a deliberately narrow tool surface — `web_search` is read-only, no tool in this design writes files, runs code, or takes actions on the user's behalf, which caps the blast radius of any bad tool call to "wrong results," not damage.

Full version with the rapid-fire Q&A grid: see the published artifact (Module 3: Interview Prep).

### Interview Q&A — Module 3 (additional, beyond Modules 1–2)

**Q: What's the single biggest risk in this design?**
A: Tool-calling reliability from the local model — named explicitly in Module 1 and mitigated with retry/repair logic in Module 2, rather than discovered as a surprise in production.

**Q: What would you change if this had to run for 1,000 users tomorrow?**
A: Swap to a hosted LLM and Tavily (both one-line changes by design), add a request queue and observability, and turn on the vector-memory cache — the full breakdown is in §3.5 of the artifact.

**Q: What's the benefit over just asking ChatGPT directly?**
A: Structure and auditability — every claim in the output traces to a specific, scored source, and the process is inspectable step by step instead of being one opaque generation.

**Q: Isn't four agents overkill for "search and summarize"?**
A: Only if the roles don't actually diverge in context and tools needed — here they do (search vs. judgment vs. writing), and the real cost (~4 extra LLM calls per query for routing) is worth naming rather than hiding.

**Q: What was the hardest design decision?**
A: Keeping the Supervisor tool-less. It's tempting to let it "help" directly with research, and resisting that is what keeps the failure-isolation benefit from Module 1 real instead of aspirational.

*(Module 4 will append implementation-specific Q&A — "why this library version," "how did you test this," etc. — as real code lands.)*

---

## Module 04 — Implementation

### Roadmap (locked before any code)

Repo layout:
```
.
├── .env.example
├── requirements.txt
├── src/
│   ├── state.py           # ResearchState, Finding
│   ├── llm.py              # ChatOllama client
│   ├── tools.py             # web_search (ddgs)
│   ├── agents/
│   │   ├── supervisor.py    # routing
│   │   ├── researcher.py    # ReAct loop
│   │   ├── analyst.py       # scoring
│   │   └── writer.py        # report draft
│   ├── graph.py             # StateGraph wiring
│   └── main.py              # CLI entrypoint
└── tests/
```

Dependencies: `langgraph`, `langchain-core`, `langchain-ollama`, `ddgs`, `pydantic`, `python-dotenv`, `pytest`. Requires Python 3.11+ and Ollama installed locally with a tool-calling-capable model pulled.

Build order (bottom-up — data shapes → the one tool → each agent alone → the graph that wires them together → the entrypoint):
1. Scaffolding + `state.py`
2. `llm.py` + `tools.py`
3. Researcher agent
4. Analyst agent
5. Writer agent
6. Supervisor + `graph.py`
7. `main.py` (first true end-to-end run)
8. Automated tests

Each numbered step is logged below as it lands — what was built, which APIs/functions, why, how to run it, how to test/demo it, and the interview questions it answers.

### Implementation Log

*Each entry follows this shape:*

```
### Step N — <what was built>
- Date:
- Files added/changed:
- What it does (plain words):
- Tools/features used, and why (vs. the alternatives considered):
- How to run it:
- How to test / demo it:
- Interview questions this step answers:
```

---

## Appendix — Repo conventions

- This file lives at `.docs/BUILD_LOG.md` — a dotfile path, so it's tucked out of the way in normal file browsers, but it **is** fully visible to anyone with access to the GitHub repo (dotfiles aren't private). If the repo is ever made public, treat everything in here as public.
- `.claude/settings.local.json` is local session config and is gitignored — it's not part of the project.
