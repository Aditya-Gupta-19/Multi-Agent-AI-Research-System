# Multi-Agent AI Research System — Build Log & Interview Prep

Internal companion to the public learning guide (published as a Claude Artifact, linked from chat each module). This file is the one that stays with the repo: a plain-words explanation of every decision, a running log of what was actually built and why, and an interview question bank that grows as the project grows. Read `## How this file works` once, then jump to whatever section matches where the project currently is.

Status: **Module 1 complete. Module 2 (Architecture) queued next.**

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

## Module 02 — Architecture (HLD & LLD)

*Queued. Will cover: Supervisor/Researcher/Analyst/Writer responsibilities, the end-to-end sequence for one query, the LangGraph state schema, error handling, and where Ollama sits in the stack.*

## Module 03 — Interview Prep (full grind)

*Queued. Will cover: problem framing, tech-stack justification (LangChain/LangGraph vs. CrewAI vs. AutoGen vs. a hand-rolled loop), cost/latency/quality trade-offs, scaling and production concerns, evaluation of agent output quality, hallucination handling, security, and system-design-style questions.*

---

## Module 04 — Implementation Log

*No steps yet — this section fills in once we start writing code. Each entry below will follow this shape:*

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
