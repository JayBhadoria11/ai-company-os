# AI Company OS

**Track:** Best Apps & Agents  
**Developers:** Team of two  
**Hackathon:** NVIDIA × Nebius Global AI Hackathon

AI Company OS is an evidence-grounded multi-agent AI operating system for business intelligence and decision-making. It connects company data to deterministic analytics, specialist agents, NVIDIA Nemotron, executive synthesis, human approval, and persistent decision history.

Instead of treating an LLM as a chatbot that directly guesses answers from raw business data, AI Company OS separates **verified computation from AI reasoning**:

```text
Company Data
     ↓
Deterministic Analytics
     ↓
Commander / CEO Agent
     ↓
Specialist Agents
     ↓
Verified Evidence
     ↓
NVIDIA Nemotron via Nebius Token Factory
     ↓
Executive Intelligence
     ↓
Human Approval
     ↓
Decision History
```

## Project Purpose

Businesses often have large amounts of operational data but still struggle to turn that data into reliable decisions.

AI Company OS is designed to act as an AI operating layer for a company. It analyzes business data, identifies important patterns, asks specialist agents to investigate specific questions, and uses NVIDIA Nemotron to synthesize verified evidence into executive-level insights and recommendations.

The system is designed around three principles:

- **Evidence before reasoning** — deterministic analytics calculate the facts before the LLM interprets them.
- **AI for reasoning, not fabricated numbers** — Nemotron receives curated evidence instead of being asked to calculate directly from an uncontrolled raw dataset.
- **Human approval for actions** — recommendations can pass through an approval workflow before execution.

## NVIDIA Nemotron & Nebius

AI Company OS uses **NVIDIA Nemotron-3 Nano 30B A3B** through **Nebius Token Factory** as its core reasoning and executive-synthesis model.

The application follows an evidence-first architecture. Deterministic Python and Pandas analysis calculates business metrics and produces verified evidence before that evidence is passed to Nemotron.

Nemotron then interprets the evidence, identifies important trends, compares findings, and generates executive-level insights and recommendations.

This allows the system to separate:

```text
Deterministic Layer
    ↓
Facts, metrics, trends and evidence
    ↓
NVIDIA Nemotron
    ↓
Reasoning, synthesis and recommendations
```

### Why NVIDIA Nemotron?

Nemotron provides the reasoning layer required to turn structured business evidence into useful executive intelligence. We use it for tasks such as:

- Executive synthesis
- Business trend interpretation
- Comparing analytical findings
- Generating recommendations
- Producing structured investigation results
- Reasoning over evidence supplied by specialist agents

### How Nebius Token Factory accelerated our workflow

Nebius Token Factory gave us API-based access to NVIDIA Nemotron inference without requiring us to provision or manage GPU infrastructure ourselves.

This allowed us to focus our engineering effort on the actual product:

- Multi-agent orchestration
- Deterministic business analytics
- Evidence extraction
- Context management
- Human approval workflows
- Decision history
- Production deployment
- React dashboard development

The Nebius API is integrated into our FastAPI backend using an OpenAI-compatible Python client.

For production deployment, the API key remains server-side and is supplied through environment variables rather than being exposed in the frontend.

### Other Nebius services

The core application uses **Nebius Token Factory** for NVIDIA Nemotron inference. No additional Nebius services are required for the core application.

## Key Features

### 1. Multi-Agent Business Intelligence

A Commander/CEO agent determines which specialist analysis is required for a business question.

Available specialist capabilities include:

- Business analysis
- Marketing analysis
- HR operations

The agents operate on verified company evidence rather than inventing business facts.

### 2. Deterministic Analytics

Business calculations are performed using Python and Pandas before the LLM receives the evidence.

This includes analysis such as:

- Sales trends
- Product performance
- Regional performance
- Channel performance
- Monthly comparisons
- Orders and units
- Business ratios
- Dataset-level metrics

### 3. NVIDIA Nemotron Executive Synthesis

After specialist analysis, the system sends curated evidence to NVIDIA Nemotron through Nebius Token Factory.

Nemotron transforms the analytical evidence into:

- Executive summaries
- Findings
- Recommendations
- Comparisons
- Business implications
- Limitations

### 4. Human Approval Gate

Recommendations are not automatically treated as executed business actions.

The system provides an approval workflow where proposed actions can be:

- Pending
- Approved
- Rejected

This creates a human-in-the-loop control layer between AI recommendations and business actions.

### 5. Company Workspace

Each company has a workspace containing:

- Company profile
- Industry
- Business objectives
- Primary KPI
- Revenue target
- Growth target
- Uploaded datasets
- Analytical context

### 6. Decision History

Investigations and decisions are persisted using SQLite so that the company can review previous AI-generated intelligence and approvals.

### 7. Large Dataset Handling

The system is designed to avoid blindly sending entire datasets to the LLM.

For large datasets, deterministic analysis first extracts decision-relevant evidence. The synthesis layer then uses bounded, curated context.

This keeps the LLM context focused while preserving the complete deterministic analysis internally.

### 8. Missing-Metric Awareness

The system does not invent unavailable business metrics.

For example, if a dataset contains sales but does not contain:

- Profit
- Cost
- Customer acquisition cost
- ROI
- Margin

the system explicitly identifies those limitations rather than fabricating values.

## Technology Stack

- **Python** — Core application language
- **FastAPI** — API server and single-service production host
- **React** — Interactive web dashboard
- **Vite** — Frontend build tooling
- **Pandas** — Business data analysis and manipulation
- **SQLite** — Local persistence for history, approvals, actions and datasets
- **NVIDIA Nemotron-3 Nano 30B A3B** — Core reasoning and synthesis model
- **Nebius Token Factory** — Nemotron inference and API access
- **OpenAI-compatible Python SDK** — Nebius API client
- **python-dotenv** — Environment configuration
- **pytest** — Automated testing
- **Docker** — Production packaging and deployment
- **Git / GitHub** — Version control and source distribution

## Project Structure

```text
package/
├── app/
│   ├── core/
│   │   ├── commander.py
│   │   ├── agent.py
│   │   ├── company_workspace.py
│   │   ├── company_context.py
│   │   └── config.py
│   │
│   ├── llm/
│   │   └── nebius_client.py
│   │
│   ├── tools/
│   │   ├── financial.py
│   │   └── business_analytics.py
│   │
│   ├── database/
│   │   └── db.py
│   │
│   └── main.py
│
├── app/data/company_workspace/
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.*
│
├── scripts/
│   └── seed_demo.py
│
├── tests/
│
├── .env.example
├── .gitignore
├── Dockerfile
├── LICENSE
├── pytest.ini
├── requirements.txt
└── README.md
```

## Setup

### Requirements

Recommended environment:

- Python 3.10+
- Node.js 18+
- npm
- Git

### 1. Clone the repository

```powershell
git clone https://github.com/JayBhadoria11/ai-company-os.git
cd ai-company-os
```

### 2. Create a Python virtual environment

```powershell
python -m venv .venv
```

Activate it in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Nebius

Copy the environment template:

```powershell
Copy-Item .env.example .env
```

Open `.env` and add your own Nebius Token Factory API key:

```env
NEBIUS_API_KEY=your_api_key_here
NEBIUS_BASE_URL=https://api.studio.nebius.ai/v1
MODEL_NAME=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B
```

**Never commit `.env` or expose a real API key.**

## Running the App

### Single Service — Recommended

Build the React dashboard once:

```powershell
cd frontend
npm install
npm run build
cd ..
```

Then start FastAPI:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000
```

The FastAPI application serves both the API and the production React dashboard.

The production frontend uses the same origin for API requests by default.

### Development Mode

For frontend development with hot reload, use two terminals.

Terminal 1 — API:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Terminal 2 — frontend:

```powershell
cd frontend
npm install
npm run dev
```

The development frontend defaults to:

```text
http://127.0.0.1:8000
```

for API requests.

Set `VITE_API_URL` if a different API endpoint is required.

## Demo Data

The repository includes a bundled demo dataset and a ready-to-use demo workspace.

Seed the demo workspace with:

```powershell
python scripts/seed_demo.py
```

The seeder is idempotent.

It only initializes the demo workspace when the Company Workspace is completely empty, so it does not overwrite existing company data.

Running it again on a populated workspace safely reports that seeding was skipped.

## Example Workflow

A typical investigation follows this flow:

```text
1. User asks a business question
             ↓
2. Commander identifies the required specialist
             ↓
3. Specialist agent analyzes the company data
             ↓
4. Deterministic tools calculate verified metrics
             ↓
5. Evidence is collected and bounded
             ↓
6. NVIDIA Nemotron receives curated evidence
             ↓
7. Nemotron produces executive synthesis
             ↓
8. Recommendation is presented
             ↓
9. Human reviews and approves/rejects
             ↓
10. Decision is stored in history
```

## Large Dataset Context Management

One of the major engineering challenges was handling large business datasets without overwhelming the reasoning model.

Sending every analytical table and raw breakdown directly into the synthesis prompt created unnecessary duplication and could cause the model to reach its context/output limits.

We solved this by introducing bounded evidence extraction and context budgeting.

The system:

1. Performs deterministic analysis first.
2. Identifies decision-relevant findings.
3. Removes redundant analytical payloads from the synthesis prompt.
4. Applies explicit character budgets.
5. Sends a compact evidence package to Nemotron.
6. Retains the full deterministic analysis internally.

This allows the application to work with substantially larger datasets while keeping the LLM prompt focused.

## Testing

Run the complete Python test suite:

```powershell
python -m pytest
```

The test suite is designed to run without network access or a real API key.

Olist relational-join tests automatically skip when the optional Olist tables are not bundled with the repository.

### Live Nebius Integration Test

Live Nemotron testing is opt-in.

Set:

```powershell
$env:NEBIUS_LIVE_TESTS=1
```

Then run:

```powershell
python -m pytest tests/test_live_nebius.py
```

A valid `NEBIUS_API_KEY` must be configured.

## Frontend Validation

From the frontend directory:

```powershell
cd frontend
npm run lint
npm run build
```

## Docker

AI Company OS includes a production Dockerfile.

Build the image:

```powershell
docker build -t ai-company-os .
```

Run it:

```powershell
docker run --rm -p 8000:8000 --env-file .env ai-company-os
```

Then open:

```text
http://localhost:8000
```

The Docker image builds the React frontend and packages it with the FastAPI backend so the application can run as a single service.

## Production Demo

Live demo:

https://ai-company-os-bff7.onrender.com/

Health check:

https://ai-company-os-bff7.onrender.com/health

Source code:

https://github.com/JayBhadoria11/ai-company-os

## Security

- `.env` is included in `.gitignore`.
- Never commit real API keys.
- Use `.env.example` as the configuration template.
- API keys are used server-side.
- The React frontend does not contain the Nebius API key.
- If a key is ever exposed in a transcript, repository, log, or other public location, rotate it immediately in the Nebius Token Factory console.

## Development Notes

Important application modules include:

### `app/core/config.py`

Loads application configuration and environment variables.

### `app/llm/nebius_client.py`

Provides the OpenAI-compatible client used to communicate with NVIDIA Nemotron through Nebius Token Factory.

### `app/core/commander.py`

Implements the Commander/CEO orchestration layer and determines which specialist agents are required.

### `app/core/agent.py`

Coordinates specialist agent execution and investigation workflows.

### `app/tools/financial.py`

Contains deterministic financial calculations.

### `app/tools/business_analytics.py`

Contains business analytics and trend analysis.

### `app/database/db.py`

Handles SQLite persistence.

### `app/core/company_workspace.py`

Manages company profiles and dataset persistence.

### `app/core/company_context.py`

Maintains shared active-company context and caching.

## Limitations

AI Company OS is designed to reason only over the information available in the connected company datasets.

If a dataset does not contain a required metric, the system reports the limitation instead of inventing the value.

For example, a sales dataset may support:

- Revenue
- Orders
- Units
- Product performance
- Regional performance
- Monthly trends

but may not support:

- True profit
- Operating costs
- Customer acquisition cost
- ROI
- Gross margin

These limitations are surfaced to the user as part of the generated intelligence.

## Future Work

Potential future extensions include:

- Additional specialist agents
- Forecasting
- Scenario simulation
- More business-data connectors
- Recurring executive reviews
- Role-based access control
- Long-term company memory
- More structured tool calling
- Approved action execution
- External business system integrations
- Advanced planning and multi-step autonomous workflows

## License

AI Company OS is released under the **MIT License**.

See [`LICENSE`](LICENSE) for the complete license text.

## Hackathon

Built for the **NVIDIA × Nebius Global AI Hackathon** under the **Best Apps & Agents** track.

The project combines deterministic business analytics with NVIDIA Nemotron inference through Nebius Token Factory to create an evidence-grounded AI operating layer for business decision-making.
