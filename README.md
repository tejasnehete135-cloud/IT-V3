# Smart Student Helpdesk Chatbot

A responsive Campus-branded helpdesk. All institution details are fictional
sample data. The backend retrieves relevant entries from editable JSON files
and sends only that context to a local LM Studio model. If the model is
unavailable, the best keyword-matched Campus answer is returned with an
offline notice.

## Requirements

- Python 3.9 or newer
- [LM Studio](https://lmstudio.ai/) with a downloaded chat/instruct model
- Windows, macOS, or Linux

## Setup and run

1. Install and open LM Studio. In **Discover**, download an instruction model,
   then load it. The default configured model is `qwen/qwen3-4b`.
2. In LM Studio, start the **Local Server** on port `1234`. The
   OpenAI-compatible endpoint is
   `http://localhost:1234/v1/chat/completions`; no API key is needed.
3. Copy `.env.example` to `.env` in the project root:

   ```powershell
   Copy-Item .env.example .env
   ```

   On macOS/Linux, use `cp .env.example .env`. If LM Studio reports a
   different model ID or server URL, update `LM_STUDIO_MODEL` or
   `LM_STUDIO_BASE_URL` in `.env`.
4. From the project root, install dependencies and start Flask:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   py -m pip install -r backend\requirements.txt
   py -m pip install pytest
   py -m pytest backend\tests -q
   py backend\app.py
   ```

   On macOS/Linux, activate with `source .venv/bin/activate` and use `python`
   instead of `py`:

   ```sh
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -r backend/requirements.txt
   python -m pytest backend/tests -q
   python backend/app.py
   ```

5. Open **http://127.0.0.1:5000**. Flask serves the frontend and API together;
   do not open `frontend/index.html` directly.

On Windows, `boot.bat` starts LM Studio, starts the local server, loads the
configured model, starts the app, and opens the browser. Ensure LM Studio and
its `lms` CLI are installed; set `LM_STUDIO_EXE` in `.env` if LM Studio is
installed somewhere other than the default path. `shutdown.bat` stops the
helpdesk and LM Studio. The scripts use `HELPDESK_PORT` from `.env` (default
`5000`).

## Project structure

```text
backend/
  app.py
  config.py
  llm_client.py
  retriever.py
  requirements.txt
  tests/test_app.py
data/
  admissions.json
  fees.json
  exams.json
  timetable.json
  events.json
  contacts.json
frontend/
  index.html
  style.css
  script.js
.env.example
logs/                       # Created when the first valid question is asked
README.md
```

Each data file is a JSON array with at least eight records. A record uses
`id`, `category`, `keywords`, `question`, and `answer`. To update Campus
knowledge, edit the relevant JSON records and restart the backend; no source
code changes are needed. Categories are `admissions`, `fees`, `exams`,
`timetable`, `events`, and `general`.

## Configuration

The backend reads `.env` from the project root. Process environment values
override `.env`.

| Variable | Default | Description |
|---|---|---|
| `LM_STUDIO_BASE_URL` | `http://localhost:1234/v1` | Local OpenAI-compatible API base |
| `LM_STUDIO_MODEL` | `qwen/qwen3-4b` | Loaded local model ID |
| `LM_STUDIO_TIMEOUT_SECONDS` | `45` | Model request timeout |
| `HELPDESK_TEMPERATURE` | `0.2` | Generation temperature |
| `HELPDESK_MAX_TOKENS` | `400` | Maximum answer tokens |
| `HELPDESK_RETRIEVAL_TOP_K` | `4` | Retrieved data records (3-5) |
| `HELPDESK_PORT` | `5000` | Flask port |
| `HELPDESK_DATA_DIR` | `data` | Directory containing category JSON files |
| `HELPDESK_LOG_FILE` | `logs/queries.csv` | CSV question log |

## API

- `POST /api/chat` accepts
  `{"message":"...", "history":[{"role":"user","content":"..."}]}` and returns
  `{"reply":"...", "category":"fees", "source":"llm"}`. `source` is `fallback`
  when the local model cannot be used. The last five messages are sent to the
  model.
- `GET /api/health` reports server status, LM Studio connectivity, and indexed
  record count.
- `GET /api/quick-questions` supplies the six chat quick-reply chips.

Valid questions are logged with a UTC timestamp and detected category.
Conversation history is held in browser memory only. CORS is enabled for API
routes; keep the server on localhost unless you add access control.

## Tests

```powershell
py -m pip install pytest
py -m pytest backend\tests -q
```

## Ten sample questions and expected answers

1. **What is the annual B.Sc. tuition fee?** B.Sc. tuition is Rs 45,000 per year.
2. **What is the annual B.Tech tuition fee?** B.Tech tuition is Rs 85,000 per year.
3. **When is the application window?** The application window is June 1 through July 15.
4. **Which documents are required to apply?** Submit 10th and 12th marksheets,
   a transfer certificate, entrance scorecard (if applicable), government
   photo ID, two passport photos, and category certificate when applicable.
5. **How do I contact the admissions office?** Email
   admissions@campus.example or call +1-555-0101 during office hours.
6. **When are the semester examinations?** Autumn semester examinations are
   scheduled for December 1-15. Spring semester examinations are scheduled for
   May 1-15. The final timetable is posted on the student portal.
7. **What are the passing criteria?** A student must earn at least 40% overall
   in each course and at least 35% in its final examination to pass.
8. **What are the weekly class hours?** Regular classes run Monday through
   Saturday, 9:00 AM-4:00 PM. Lunch break is 1:00-2:00 PM.
9. **When is the annual Campus festival?** Open Horizons is scheduled for
   February 12-14.
10. **How can I contact the Campus Helpdesk?** Contact
    helpdesk@campus.example or +1-555-0100. Office hours are
    Monday-Saturday, 9:00 AM-5:00 PM.
