# Research Paper Agent

An autonomous multi-agent pipeline that generates structured, evaluated academic research papers using AWS Bedrock and LangGraph. Given a research topic, the agent plans, writes, evaluates, and assembles a complete paper in under 2 minutes.

---

## Overview

The agent uses a **dynamic planner-worker architecture** built on LangGraph. A central planner decides which worker to invoke next based on what has been completed, evaluates the quality of each output, and retries or replans if quality is insufficient. Each section of the paper is written by a dedicated worker, summarised, and evaluated before the planner moves forward.

**Key numbers from production runs:**
- Runtime: ~1.8 minutes end-to-end
- Output: 3,500–4,700 words
- Quality score: 0.83–0.92 (evaluated by a separate LLM judge)
- Workers: 11 content workers + planner + summarizer + evaluator
- Fallback: automatic model switch if primary fails or returns None

---

## Architecture

```
START → Planner → [Worker] → Summarizer ─┐
                            → Evaluator  ─┴→ Post-Eval → Planner (loop)
                                                ↓ (on accept)
                                        Research Evaluation
                                                ↓
                                        Output Generator → END
```

### Layers

```
research_agent_fixed/
│
├── main.py                        # CLI entry point
├── ui.py                          # Streamlit UI
│
├── app.py                         # AWS AgentCore entrypoint
├── deploy.py                      # AgentCore configure + deploy
├── launch.py                      # Local AgentCore runtime
├── invoke.py                      # Client — local or AWS invocation
├── requirements.txt               # Top-level deps (AgentCore build)
│
├── agentcore/                     # AgentCore runtime layer
│   ├── runtime_config.py          # Region, agent name, deploy flags
│   └── memory.py                  # MemorySaver session memory
│
└── research_agent/                # Core pipeline
    ├── config/
    │   └── settings.py            # LLMConfig, SafetyConfig, EvaluationConfig
    │
    ├── llm/
    │   └── provider.py            # get_llm_with_structure + get_fallback_llm
    │
    ├── graph/
    │   └── builder.py             # LangGraph StateGraph construction
    │
    ├── state/
    │   ├── schema.py              # GraphState TypedDict + all Pydantic output models
    │   └── initializer.py         # Safe state initialisation
    │
    ├── planner/
    │   ├── planner.py             # Research planner node
    │   ├── replanning.py          # Retry/replan logic
    │   └── fallback.py            # Safety limit fallback handler
    │
    ├── workers/
    │   ├── base.py                # run_worker() — shared execution pattern
    │   ├── content_workers.py     # All 11 section workers
    │   └── references_worker.py   # Citation extraction + reference generation
    │
    ├── evaluators/
    │   ├── worker_evaluator.py    # Per-worker quality evaluation
    │   └── research_evaluator.py  # Final paper quality evaluation
    │
    ├── summarizer/
    │   └── summarizer.py          # Compresses worker output for planner context
    │
    ├── output_generator/
    │   └── output_generator.py    # Assembles final paper markdown
    │
    ├── prompts/
    │   ├── worker_prompts.py      # System prompts for each content worker
    │   └── evaluator_prompts.py   # Summarizer + evaluator prompts
    │
    └── utils/
        ├── logger.py              # Structured console + file logging
        ├── helpers.py             # Safety checks, metrics, state utilities
        └── token_tracker.py       # Token usage tracking
```

---

## Workers

The pipeline runs these workers in sequence, each producing one section:

| Worker | Output | State Key |
|---|---|---|
| `topic_clarifier` | Refined topic + research scope | `clarified_topic` |
| `outline_designer` | Section structure | `outline` |
| `introduction_writer` | Introduction + contributions | `introduction` |
| `background_writer` | Background + key concepts | `background` |
| `literature_review_writer` | Literature synthesis | `literature_review` |
| `research_gap_identifier` | Research gaps + justifications | `research_gaps` |
| `methodology_designer` | Research design + methods | `methodology` |
| `results_writer` | Results + tables | `results` |
| `discussion_writer` | Discussion + limitations + future work | `discussion` |
| `conclusion_writer` | Conclusion + key takeaways | `conclusion` |
| `references_writer` | Formatted reference list | `references` |
| `research_evaluation` | Final quality score + accept/replan | `evaluation_result` |

After each content worker, **summarizer** and **evaluator** run in parallel:
- **Summarizer** — compresses output to ~2 sentences for planner context
- **Evaluator** — scores quality (0–1), decides accept or retry

---

## LLM Configuration

**Provider:** AWS Bedrock via `ChatBedrockConverse`

**Primary model:** `openai.gpt-oss-120b-1:0`
**Fallback model:** `anthropic.claude-3-5-haiku-20241022-v1:0`

Fallback activates automatically if the primary:
- Returns `None` (output token limit hit)
- Raises any exception (throttle, timeout, validation error)

Configured in `research_agent/config/settings.py`:

```python
class LLMConfig:
    MODEL:               str   = "openai.gpt-oss-120b-1:0"
    FALLBACK_MODEL:      str   = "anthropic.claude-3-5-haiku-20241022-v1:0"
    AWS_REGION:          str   = "us-east-1"
    DEFAULT_TEMPERATURE: float = 0.7
```

---

## Safety & Quality Controls

| Control | Setting | Purpose |
|---|---|---|
| Max total steps | 80 | Hard cap on graph execution |
| Max planner calls | 60 | Prevents infinite replanning |
| Max worker retries | 4 | Per-worker retry limit |
| Circuit breaker | 3 consecutive failures | Trips and terminates |
| Quality threshold | 0.65 | Minimum score to accept worker output |
| Max eval retries | 3 | Per-worker evaluation retries |

---

## Setup

### Prerequisites

- Python 3.11+
- AWS account with Bedrock access
- AWS credentials configured (`aws configure` or environment variables)
- Bedrock model access enabled for your chosen models

### Installation

```bash
git clone <repo>
cd research_agent_fixed
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
# AWS — required
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-east-1

# LangSmith tracing — optional
LANGSMITH_API_KEY=ls__your_key
LANGCHAIN_PROJECT=research-paper-agent

# AgentCore — required for deployment
AGENTCORE_ARN=arn:aws:bedrock:...   # populated after deploy.py
```

---

## Usage

### CLI

```bash
python main.py
```

Edit the topic at the bottom of `main.py`:

```python
run_pipeline(
    topic="Design a research paper on the future of the IT industry with AI",
    citation_style="APA",  # APA | IEEE | MLA
)
```

Output files saved to `output/`:
- `final_paper.md` — full paper in markdown
- `final_paper.json` — structured sections + metadata
- `token_report.json` — token usage per LLM call

### Streamlit UI

```bash
streamlit run ui.py
```

- Enter research topic
- Select citation style (APA / IEEE / MLA)
- Click **Generate Paper**
- Spinner updates with current worker name
- Download paper as markdown when complete
- Partial paper available for download if pipeline fails mid-run

### AgentCore (AWS Deployment)

**Test locally:**
```bash
python launch.py           # starts local runtime on :8080
python invoke.py --local --prompt "Design a paper on AI in healthcare"
```

**Deploy to AWS:**
```bash
python deploy.py
# prints ARN after deploy
```

**Invoke on AWS:**
```bash
python invoke.py \
  --prompt "Design a paper on AI in healthcare" \
  --arn arn:aws:bedrock:us-east-1:...
```

**Payload format:**
```json
{
  "prompt": "Design a research paper on...",
  "citation_style": "APA",
  "session_id": "optional-for-memory-continuity"
}
```

**Response format:**
```json
{
  "session_id": "abc-123",
  "status": "success",
  "title": "...",
  "word_count": 4200,
  "score": 0.88,
  "paper_md": "# Title\n\n..."
}
```

---

## Observability

**LangSmith** — full execution traces available at [smith.langchain.com](https://smith.langchain.com)
- Every node, every LLM call, token counts, latency
- Automatic retry on payload size errors (>25MB truncated, traces still visible)

**Structured logging** — `logs/agent.log`
```
21:13:00  WORKER    ⚙  [background_writer]  Starting
21:13:05  WORKER    ✅  [background_writer]  Completed successfully
21:13:07  EVAL      [background_writer]  score=0.86  → PASS
```

**Token report** — `output/token_report.json`
- Input/output tokens per worker
- Total cost estimate
- Latency per call

---

## Performance

Measured on production runs with `openai.gpt-oss-120b-1:0` on Bedrock:

| Component | Time |
|---|---|
| 11 content workers | ~57s total |
| Summarizer + Evaluator (parallel) | ~25s total |
| Planner calls (12 total) | ~21s total |
| Research evaluation | ~3s |
| **Total** | **~1.8 minutes** |

Parallel summarizer + evaluator saves ~15s per run vs sequential execution.
Fallback model activation adds ~4-5s on affected workers but prevents retries that would cost 15-20s.

---

## Known Limitations

- References worker can hit output token limits with 30+ citations — fallback model handles this but batching is not yet implemented
- Background and research gaps sections tend to be shorter (~200-250 words) — prompt word count targets not yet added
- AgentCore memory uses in-process MemorySaver — sessions reset on container restart (DynamoDB persistence not yet implemented)
- Input validation not yet implemented — pipeline will attempt to run on any input including non-research topics

---

## Tech Stack

| Component | Technology |
|---|---|
| Agent framework | LangGraph |
| LLM provider | AWS Bedrock (ChatBedrockConverse) |
| Primary model | openai.gpt-oss-120b-1:0 |
| Fallback model | anthropic.claude-3-5-haiku |
| Output validation | Pydantic v2 |
| Observability | LangSmith |
| UI | Streamlit |
| Deployment | AWS Bedrock AgentCore Runtime |
| Session memory | LangGraph MemorySaver |
| Language | Python 3.11+ |