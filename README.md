# AI Company OS

**Track:** Best Apps and Agents  
**Developer:** Solo  
**Hackathon:** NVIDIA × Nebius

## Project Purpose

AI Company OS is an autonomous business operations agent that helps solo
developers and small teams make data-driven business decisions. The agent
connects to NVIDIA Nemotron models via the Nebius Token Factory platform,
analyzes company financial data, and produces evidence-backed business insights
and recommendations.

## Technology Stack

- **Python** - Core language
- **FastAPI** - API server and single-service host for the dashboard
- **React + Vite** - Interactive web dashboard (in `frontend/`)
- **Pandas** - Data analysis and manipulation
- **SQLite** - Local persistence for history, approvals, actions and datasets
- **Nebius Token Factory** - Authentication and API access for NVIDIA Nemotron
- **NVIDIA Nemotron** - Core LLM for reasoning, tool calling and insight generation
- **OpenAI-compatible Python SDK** - Client for the Nebius API
- **python-dotenv** - Environment variable configuration
- **pytest** - Test suite

## Project Structure

```
package/
├── app/                    # Main application package
│   ├── core/               # Orchestration, workspace, analysis, config
│   ├── llm/                # Nebius LLM client
│   ├── tools/              # Deterministic financial/business analysis tools
│   ├── database/           # SQLite persistence
│   └── ui/                 # Legacy Streamlit dashboard (optional)
├── app/data/company_workspace/  # Uploaded/seed datasets
├── frontend/               # React + Vite dashboard
├── scripts/seed_demo.py    # Idempotent demo workspace seeder
├── tests/                  # Test suite
├── .env.example            # Environment variable placeholders
├── pytest.ini              # Portable pytest configuration
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add your Nebius API key:
   `NEBIUS_API_KEY=...`
   The real `.env` is git-ignored and must never be committed.

## Running the app

### Single service (recommended / production-style)

Build the dashboard once, then run the API which also serves it:

```powershell
cd frontend
npm install
npm run build
cd ..
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open <http://localhost:8000>. The production build reads
`frontend/.env.production` (`VITE_API_URL=`) so all API calls are same-origin.

### Development (two services)

```powershell
# Terminal 1 - API
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 - dashboard with hot reload
cd frontend
npm run dev
```

In development the dashboard defaults to `http://127.0.0.1:8000` for API calls.
Set `VITE_API_URL` to override.

## Demo data

Seed a ready-to-demo company profile and the bundled `video_games_sales.csv`
dataset:

```powershell
python scripts/seed_demo.py
```

The seeder is idempotent and only runs when the Company Workspace is completely
empty, so it never overwrites real user data. Run it again on a populated
workspace and it safely reports `skipped`.

## Testing

Run the full Python test suite:

```powershell
python -m pytest
```

The suite is self-contained and never requires network access or a real API
key. The two Olist relational-join tests skip automatically when the Olist
tables are not bundled with the checkout.

Real Nebius integration testing is **opt-in** and skipped by default:

```powershell
$env:NEBIUS_LIVE_TESTS=1; python -m pytest tests/test_live_nebius.py
```

Frontend validation:

```powershell
cd frontend
npm run lint
npm run build
```

## Security

- `.env` is git-ignored. Never commit real API keys.
- Use `.env.example` as the template for local configuration.
- If a key is ever exposed (e.g. pasted into a transcript or committed), rotate
  it immediately in the Nebius Token Factory console.

## Development Notes

- **core/config.py** - Loads configuration from environment variables
- **llm/nebius_client.py** - OpenAI-compatible Nebius API client
- **tools/financial.py** - Deterministic financial calculations
- **tools/business_analytics.py** - Business trend and ratio analysis
- **database/db.py** - SQLite persistence with parameterized queries
- **core/agent.py** / **core/commander.py** - Agent orchestration
- **core/company_workspace.py** - Company profile and dataset persistence
- **core/company_context.py** - Shared active-company context and caching
- **ui/dashboard.py** - Legacy Streamlit interface (optional)
