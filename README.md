<h1 align="center">🏠 LocalMind</h1>

<p align="center">
  <b>A private AI assistant that runs entirely on your machine.</b><br>
  Plug-in skills (notes, reminders, file search, calc), SQLite memory, and an offline mock model — or point it at Ollama / LM Studio.
</p>

<p align="center">
  <a href="https://github.com/Hayatelin/localmind/actions/workflows/ci.yml"><img src="https://github.com/Hayatelin/localmind/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/Hayatelin/localmind/releases"><img src="https://img.shields.io/github/v/release/Hayatelin/localmind?color=4f46e5" alt="release"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="python">
  <img src="https://img.shields.io/badge/privacy-local--first-0fb9a4" alt="privacy">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="license">
  <a href="https://github.com/Hayatelin/localmind/stargazers"><img src="https://img.shields.io/github/stars/Hayatelin/localmind?style=social" alt="stars"></a>
</p>

<p align="center"><img src="docs/demo.gif" alt="LocalMind demo" width="820"></p>

---

LocalMind is a small, dependency-light Python assistant that routes what you type
to drop-in **skills** (notes, reminders, file search, calculator, ...) and only
falls back to a language model when no skill matches. The default language-model
provider is a fully **offline, rule-based "mock" provider**, so LocalMind runs
end-to-end with **no API key and no internet**. When you want smarter free-form
answers, point it at a **local** OpenAI-compatible server such as
[Ollama](https://ollama.com) or [LM Studio](https://lmstudio.ai) — still on your
own machine.

> Not affiliated with any cloud AI service. By default, **nothing ever leaves
> your computer.**

---

## 繁體中文摘要 (Traditional Chinese Summary)

**LocalMind 是一個注重隱私、完全在本機執行的 AI 助理閘道。所有資料都留在你的電腦上。**

- **零設定、可離線執行**：預設使用內建、以規則為基礎的「mock」語言模型，不需要 API 金鑰、不需要網路。
- **技能外掛架構**：把 Python 檔放進 `skills/` 資料夾即可新增功能。LocalMind 會自動把輸入路由到最適合的技能，找不到時才交給語言模型。
- **內建 4 個離線技能**：筆記 (notes)、提醒 (reminders)、檔案搜尋 (file_search)、計算機 (calc)，全部實際可用。
- **本機儲存**：使用 SQLite，將筆記、提醒與對話記憶存在單一 `localmind.db` 檔。
- **可選本機模型**：可指向 Ollama (`http://localhost:11434/v1`) 或 LM Studio (`http://localhost:1234/v1`)，資料一樣不外流。
- **預設絕不連雲端**：隱私是第一原則。

技能是由關鍵字規則打分選出，不是由模型決定要呼叫哪個工具，每則訊息只處理一次；實際運作方式與它和 agent 迴圈的差別，見 [How it works — and is it an agent?](#how-it-works--and-is-it-an-agent)。

快速開始：

```bash
pip install -e .
python -m localmind --once "add note buy milk"
python -m localmind --once "list notes"
python -m localmind            # 進入互動式對話
```

---

## Why LocalMind?

| Concern | LocalMind's answer |
| --- | --- |
| Privacy | Data is stored only in a local SQLite file. No telemetry, no cloud calls by default. |
| Works offline | The default `mock` provider is rule-based and needs no network. |
| Extensible | Add a `.py` file to `skills/` — no core changes required. |
| Lightweight | Standard library + PyYAML. `requests` is optional and lazily imported. |
| Your hardware, your model | Optional local LLM via Ollama / LM Studio. |

---

## Install

Requires **Python 3.9+**.

```bash
git clone https://github.com/VictorLin/localmind.git
cd localmind

# Recommended: a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install LocalMind (editable) + its single runtime dependency (PyYAML)
pip install -e .

# Optional extras:
pip install -e ".[local]"        # adds requests, for the Ollama/LM Studio provider
pip install -e ".[dev]"          # adds pytest for running the test suite
```

You can also just install the dependency directly: `pip install PyYAML`.

---

## Quickstart (copy-paste)

```bash
# Single-shot mode (great for scripts and trying things out):
python -m localmind --once "add note buy milk"
python -m localmind --once "list notes"
python -m localmind --once "remind me to call mom at 5pm"
python -m localmind --once "list reminders"
python -m localmind --once "calc (5 + 3) ** 2"
python -m localmind --once "find report.txt"
python -m localmind --once "hello"        # no skill matches -> offline LLM reply

# Inspect what's loaded and how it's configured:
python -m localmind skills
python -m localmind config

# Interactive chat REPL (Ctrl-D or /quit to leave):
python -m localmind
```

Inside the REPL you can also type `/skills`, `/config` and `/quit`.

Because everything persists to a local SQLite database, a note you add in one
invocation is there the next time you ask to list notes.

---

## Configuration

LocalMind reads config from (highest precedence first): environment variables,
then a YAML file, then built-in defaults. Run `python -m localmind config` to see
the active values and the config file path.

Example `localmind.yaml`:

```yaml
provider: mock                              # "mock" (offline default) or "local"
local_endpoint: http://localhost:11434/v1   # Ollama default; LM Studio uses :1234/v1
local_model: llama3
file_search_dir: /home/you/Documents        # directory the file_search skill scans
# db_path: /custom/path/localmind.db        # optional override
```

Environment variables (override the file):

| Variable | Purpose |
| --- | --- |
| `LOCALMIND_CONFIG` | Path to the YAML config file. |
| `LOCALMIND_HOME` | Base directory for data (db + default config). |
| `LOCALMIND_PROVIDER` | `mock` or `local`. |
| `LOCALMIND_LOCAL_ENDPOINT` | OpenAI-compatible base URL. |
| `LOCALMIND_LOCAL_MODEL` | Model name to request. |
| `LOCALMIND_DB` | Path to the SQLite database. |
| `LOCALMIND_FILE_SEARCH_DIR` | Directory for the file_search skill. |
| `LOCALMIND_SKILLS_DIR` | Extra directory of custom skill modules. |

---

## Pointing LocalMind at Ollama / LM Studio

LocalMind talks to any **local** OpenAI-compatible `/v1/chat/completions` server.

**Ollama:**

```bash
# 1. Install Ollama and pull a model
ollama pull llama3
# Ollama serves an OpenAI-compatible API at http://localhost:11434/v1

# 2. Tell LocalMind to use it
pip install -e ".[local]"        # ensure 'requests' is available
export LOCALMIND_PROVIDER=local
export LOCALMIND_LOCAL_ENDPOINT=http://localhost:11434/v1
export LOCALMIND_LOCAL_MODEL=llama3

python -m localmind --once "what is the capital of France"
```

**LM Studio:** start its local server (default `http://localhost:1234/v1`), then
set `LOCALMIND_LOCAL_ENDPOINT=http://localhost:1234/v1` and
`LOCALMIND_LOCAL_MODEL` to the model you loaded.

Skills always run locally regardless of provider; the provider is only the
fallback for free-form questions. Even with `provider: local`, the server is on
your machine — still no cloud.

---

## How to add a custom skill

A skill is a Python module exposing a module-level `SKILL` object with a `name`,
a list of trigger `keywords`, and a `run(query, context)` function returning a
string.

Create `skills/weather.py` inside the package (or in any folder pointed to by
`LOCALMIND_SKILLS_DIR`):

```python
from localmind.skills import Skill, SkillContext

def run(query: str, context: SkillContext) -> str:
    # context.storage  -> the SQLite Storage object
    # context.config   -> the resolved Config
    return "It's always sunny inside your own machine."

SKILL = Skill(
    name="weather",
    keywords=["weather", "forecast"],
    run=run,
    description="A toy weather skill.",
)
```

Then:

```bash
python -m localmind skills            # confirm it loaded
python -m localmind --once "weather"  # route to it
```

Routing picks the skill with the highest keyword score; a keyword at the start of
your message counts a little extra. If nothing scores high enough, the provider
answers.

---

## Architecture

```mermaid
flowchart TD
    U[User input] --> CLI[CLI / REPL]
    CLI --> A[Assistant router]
    A -->|score skills| R{Best skill\nabove threshold?}
    R -->|yes| S[Skill.run query, context]
    R -->|no| P[Provider fallback]
    P -->|default| M[MockProvider\noffline, rule-based]
    P -->|opt-in| L[LocalEndpointProvider\nOllama / LM Studio]
    S --> DB[(SQLite localmind.db)]
    A --> DB
    subgraph Skills[skills/ plugins]
        N[notes]
        RM[reminders]
        FS[file_search]
        C[calc]
    end
    S --- Skills
    DB -. notes / reminders / history .- Skills
```

- **`cli.py`** — argparse CLI: REPL, `--once`, `skills`, `config`.
- **`assistant.py`** — scores skills, routes, records history.
- **`skills/`** — auto-discovered plugins (each exports `SKILL`).
- **`providers.py`** — `MockProvider` (default) and `LocalEndpointProvider`.
- **`storage.py`** — SQLite for notes, reminders and chat history.
- **`config.py`** — layered config (env > YAML > defaults).

---

## How it works — and is it an agent?

LocalMind is a rule-based router with a language-model fallback. Which skill runs is
decided by keyword scoring in Python, not by the model, and each message is handled
in a single pass.

### One message, step by step

1. `cli.main` loads the config and builds an `Assistant`, which loads skills with
   `skills.load_skills()` (built-in modules, then `LOCALMIND_SKILLS_DIR`) and the
   provider with `providers.build_provider`.
2. `--once TEXT`, or each REPL line, calls `Assistant.handle(text)`, which reads the
   10 most recent rows of the SQLite `history` table, then saves the user message.
3. `best_skill` asks every skill for `score(query)`: +1.0 per keyword found as a
   whole word, +0.5 more if the message starts with it. The top score wins if it is
   at least `MATCH_THRESHOLD` (1.0); on a tie, the skill loaded first wins.
4. If a skill wins, `skill.run(query, context)` returns the reply. Skills parse the
   text with regular expressions and use SQLite or the filesystem; no model is involved.
5. Otherwise `provider.generate(query, history)` returns the reply.
6. The reply is saved to `history` (with the skill name, if any) and printed.

A message triggers one skill call or one provider call, never both. A skill's result
goes straight to the user; it is never passed back to a model.

### Where the model is called and what it sees

- Only in step 5, the fallback path.
- `MockProvider` (the default) is not a model: it matches a short list of regexes,
  returns canned text and ignores `history`.
- `LocalEndpointProvider` POSTs `{"model", "messages", "stream": false}` to
  `<endpoint>/chat/completions` and returns `choices[0].message.content`. There is no
  system prompt, no `tools` field and no `max_tokens`.
- `messages` is the 10 most recent `history` rows from before this message, then
  the current message once. The rows include skill replies and turns from earlier
  runs, since the table persists and is not filtered by session.
- Context length is handled only by that fixed 10-row window. Tokens are not counted,
  messages are not truncated (a `file_search` reply can list 20 results), and the
  `history` table is never pruned.
- Endpoint errors are caught and returned as a `[local provider error] ...` reply.

### Is this an agent?

No. In an agent loop the model receives tool schemas, decides which tool to call,
sees the result in its context and decides again, until it gives a final answer or
hits a step limit.

| | Agent loop | LocalMind |
| --- | --- | --- |
| Who picks the tool | the model, from tool schemas | `Skill.score` keyword rules |
| Model calls per message | repeated until done | zero or one |
| Tool result | added to context; the model continues | returned to the user directly |
| Stop condition | final answer or step limit | after one skill or one provider call |

The skills are real tools (SQLite notes and reminders, filesystem search, an
AST-based calculator), so they are a reasonable base for an agent loop.

### What it would take to become an agent loop (roadmap idea, not implemented)

1. Give each `Skill` a JSON schema for its arguments (for example `add_note(text)`,
   `calc(expression)`) instead of parsing free text with regexes.
2. Send the schemas in the `tools` field of the `LocalEndpointProvider` payload; this
   needs a local model and server that support tool calling.
3. Parse `message.tool_calls` and validate the arguments.
4. Run the skill, append a `role: "tool"` message with its result, call the model again.
5. Stop when the model answers without a tool call; cap steps per message; return
   unknown tools or bad arguments to the model as tool errors.
6. Replace the 10-row window with a token budget, add a system prompt, truncate long
   tool output and summarise older history.
7. Keep keyword routing for `MockProvider`, which cannot call tools.

---

## Running the tests

```bash
pip install -e ".[dev]"
pytest -q
```

The suite covers skill routing, each skill's core function, and a SQLite
storage roundtrip (including persistence across separate connections).

---

## Privacy stance

- **No cloud by default.** The default provider is fully offline.
- **No telemetry.** LocalMind never phones home.
- **Local storage only.** Everything lives in one SQLite file you control.
- **Opt-in networking.** The only outbound traffic possible is to a *local*
  endpoint you explicitly configure, and `requests` is only imported when used.

---

## License

[MIT](LICENSE) © 2026 VictorLin
