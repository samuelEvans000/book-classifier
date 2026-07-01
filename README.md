# Book Classification Pipeline

Classifies 1.9M non-fiction books using free LLM APIs (SambaNova, DeepSeek, Gemini, Cerebras, OpenRouter, HuggingFace).
Outputs a headerless CSV: `md5,category,"sub1,sub2,sub3,sub4","tag1,...,tag8",audience`

---

## Setup

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in at least one API key.

Place your input file at `data/books.csv` (columns: `title,author,md5`).

---

## Run

```bash
python run.py
```

The pipeline is fully resumable — if it stops, just run again. Completed books are tracked in `checkpoints/checkpoint.json` and cross-checked against `output/classified.csv`.

---

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `PRIMARY_PROVIDER` | `sambanova` | First provider in rotation |
| `CHUNK_SIZE` | `500` | Books loaded per chunk from disk |
| `MAX_WORKERS` | `20` | Concurrent async workers |
| `MAX_BOOKS_PER_BATCH` | `40` | Books per single API call |
| `RETRY_BATCH_SIZE` | `10` | Failed books retried in mini-batches |
| `ENABLE_GROQ` | `false` | Groq free tier is Llama-only (disabled by default) |
| `REQUEST_TIMEOUT` | `60` | Seconds per request |
| `MAX_RETRIES` | `5` | Retries per batch before giving up |

---

## Free API Tiers (non-Llama models)

| Provider | Model | RPM | Daily limit |
|---|---|---|---|
| SambaNova | Qwen3-32B | 10 | 20M tokens/day |
| DeepSeek | deepseek-chat | 60 | credits-based |
| Gemini | gemini-2.5-flash-lite | 15 | 1,000 RPD |
| Cerebras | gpt-oss-120b | 5 | 1M tokens/day |
| OpenRouter | gemma-3-12b-it:free | 20 | 200 RPD |
| HuggingFace | Mistral-7B-Instruct | 10 | varies |

Load balancer uses **round-robin** across all active providers. When one hits quota (429), it is skipped for the rest of the session.

---

## Scaling to 1.9M books

Run multiple terminal sessions with sharded input files and different `PRIMARY_PROVIDER` values:

```bash
PRIMARY_PROVIDER=sambanova INPUT_FILE=data/shard1.csv python run.py
PRIMARY_PROVIDER=deepseek INPUT_FILE=data/shard2.csv python run.py
PRIMARY_PROVIDER=gemini INPUT_FILE=data/shard3.csv python run.py
```

Use multiple API accounts per provider for maximum throughput.

---

## Architecture

```
run.py
└── app/main.py          (orchestrator)
    ├── parser/           (CSV I/O)
    ├── checkpoint/       (resume support)
    ├── router/           (round-robin load balancer + fallback)
    │   └── providers/    (SambaNova, DeepSeek, Gemini, Cerebras, OpenRouter, HF)
    ├── workers/          (async queue + workers)
    ├── validator/        (response parsing + output QA)
    └── prompt/           (compact system prompt + batch prompt builder)
```

---

## Output Format

```
md5hash,Category,"Sub1,Sub2,Sub3,Sub4","Tag1,Tag2,Tag3,Tag4,Tag5,Tag6,Tag7",Audience
```

No header row. Example:
```
048ea0496db0444f,Finance,"Personal Finance,Financial Literacy,Investing,Wealth Management","Assets,Liabilities,Cash Flow,Passive Income,Financial Freedom,Wealth Building,Real Estate",General
```
