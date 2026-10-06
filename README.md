# AI Company OS

**Track:** Best Apps and Agents  
**Developer:** Solo  
**Hackathon:** NVIDIA × Nebius Global AI Hackathon

AI Company OS is an evidence-grounded multi-agent AI operating system for business decision-making.

It combines deterministic data analysis with **NVIDIA Nemotron through Nebius Token Factory** to turn company datasets into verified insights, executive-level reasoning, and actionable recommendations.

The system is designed around a simple principle:

> **AI should reason from evidence, not invent business facts.**

---

## 🚀 Try AI Company OS

### Live Demo

**https://ai-company-os-bff7.onrender.com/**

### GitHub

**https://github.com/JayBhadoria11/ai-company-os**

The live application is deployed as a single production service. No local installation is required to try the demo.

---

## 💡 What It Does

AI Company OS acts as an AI decision-support layer for a company.

Instead of simply sending an entire spreadsheet to an LLM, the system:

1. Ingests company data.
2. Performs deterministic analysis.
3. Uses a Commander/CEO agent to determine what needs investigation.
4. Delegates questions to specialized agents.
5. Collects evidence from the underlying dataset.
6. Uses NVIDIA Nemotron to synthesize the evidence into an executive response.
7. Identifies limitations and unavailable metrics.
8. Generates potential actions.
9. Requires human approval before consequential actions are executed.

This creates a separation between:

**Data → Deterministic Evidence → AI Reasoning → Human Decision**

---

## 🧠 Why AI Company OS?

Traditional dashboards show users what happened.

Generic chatbots can answer questions about data, but may produce unsupported conclusions when the underlying dataset does not contain the required information.

AI Company OS combines both approaches.

The application calculates business evidence deterministically and then gives that evidence to NVIDIA Nemotron for reasoning and synthesis.

If the dataset does not contain enough information to calculate a metric, the system explicitly reports that the metric cannot be verified.

For example:

- No cost data → profit cannot be verified.
- No marketing spend → ROI cannot be verified.
- No customer acquisition data → CAC cannot be verified.

The system is designed to prefer **"not verified" over hallucination**.

---

# 🏗️ Architecture

```text
                    Company Dataset
                           │
                           ▼
                 Deterministic Analysis
                           │
                           ▼
                    Commander / CEO
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           Analyst      Marketing       HR
            Agent         Agent        Agent
              │            │            │
              └────────────┼────────────┘
                           ▼
                    Evidence Context
                           │
                           ▼
              NVIDIA Nemotron via Nebius
                           │
                           ▼
                  Executive Synthesis
                           │
                           ▼
                 Insights + Limitations
                           │
                           ▼
                   Proposed Actions
                           │
                           ▼
                 Human Approval Gate
```

The deterministic analysis remains available inside the application while the LLM receives a controlled, compact evidence context.

---

# 🤖 NVIDIA + Nebius

NVIDIA Nemotron is the intelligence layer of AI Company OS.

The production application uses:

- **Model:** NVIDIA Nemotron 3 Nano 30B A3B
- **Platform:** Nebius Token Factory
- **API:** OpenAI-compatible interface

Nemotron is used for:

- Commander-level planning
- Business reasoning
- Evidence-grounded synthesis
- Executive recommendations
- Tool/agent orchestration

The model is not used as a standalone chatbot. It is integrated into the multi-agent decision pipeline.

---

# 📊 Real Production Test

The deployed application was tested with a **421,570-row Walmart-style sales dataset**.

AI Company OS identified:

| Metric | Result |
|---|---:|
| Total verified sales | $6,737,218,987.11 |
| Strongest month | December 2010 |
| December 2010 sales | $288,760,532.72 |
| December 2011 sales | $288,078,102.48 |
| Difference | ≈ $682,430 |

The system also correctly identified that profit, costs, CAC, ROI, and margin could not be verified from the available dataset.

This demonstrates the intended behavior:

**Calculate what can be proven. Explicitly identify what cannot.**

---

# 📂 Dataset Requirements

AI Company OS analyzes **CSV datasets**.

## Required format

- The file uploaded to the application should be a **`.csv` file**.
- The CSV should contain a header row with column names.
- Data should be organized into rows and columns.
- Numeric, categorical, and date columns can be used depending on the analysis.
- Larger datasets are supported.

## Using Kaggle datasets

Kaggle provides datasets in different formats.

For AI Company OS, use the **actual dataset CSV**, not a Jupyter Notebook.

### ✅ Supported workflow

```text
Kaggle dataset
      │
      ▼
Download dataset
      │
      ├── CSV ───────────────► Upload CSV
      │
      └── ZIP ──► Extract ───► Find CSV ───► Upload CSV
```

### ✅ Use

- `.csv`
- `.zip` downloaded from Kaggle **when it contains the required CSV dataset**

### ❌ Do not upload

- `.ipynb` Jupyter notebooks
- Python notebooks instead of the dataset
- Screenshots
- PDF reports
- HTML notebook exports
- ZIP files containing only notebooks

**Important:** A Kaggle ZIP is a download package, not the upload format. Extract it first and upload the relevant `.csv` file.

---

# 🧪 Recommended Demo Datasets

Different datasets demonstrate different capabilities of AI Company OS.

### 🥇 Sales & Operations

A structured sales dataset containing fields such as:

- Date
- Store
- Product
- Category
- Region
- Units Sold
- Price
- Discount
- Promotion
- Inventory

This is the recommended type of dataset for the broadest business demonstration.

### 📣 Marketing Analytics

Marketing datasets can be used for questions involving:

- Impressions
- Clicks
- Spend
- Conversions
- Campaign performance

### 👥 HR Analytics

HR datasets can be used for:

- Attrition
- Departments
- Employee characteristics
- Overtime
- Job satisfaction
- Workforce patterns

AI Company OS adapts its analysis to the information actually present in the dataset.

---

# 💬 Example Questions

After uploading a suitable CSV, try questions such as:

### Sales

> Which month had the strongest sales performance, and how did it compare with the other months?

### Products

> Which products or categories generated the most sales?

### Regional Performance

> Which regions or stores performed best, and what patterns should management investigate?

### Marketing

> Which campaigns appear to have the strongest conversion performance?

### HR

> What patterns are associated with employee attrition?

### Data Limitations

> Which important business metrics cannot be verified from this dataset?

The final question is particularly important because AI Company OS is designed to identify missing evidence instead of inventing values.

---

# 🧩 Human-in-the-Loop

AI Company OS does not blindly execute AI recommendations.

When the system identifies a potential consequential action, it creates an approval candidate.

The human can then:

- Review the evidence.
- Review the AI reasoning.
- Approve the action.
- Reject the action.

This keeps the system useful while maintaining human control over consequential decisions.

---

# ⚙️ Technology Stack

- **NVIDIA Nemotron** — AI reasoning and synthesis
- **Nebius Token Factory** — NVIDIA model access
- **Python** — Core application language
- **FastAPI** — API server and production host
- **React + Vite** — Interactive dashboard
- **Pandas** — Data analysis and manipulation
- **SQLite** — Local persistence
- **Docker** — Production packaging
- **OpenAI-compatible Python SDK** — Nebius API client
- **python-dotenv** — Environment configuration
- **pytest** — Automated testing

---

# 📁 Project Structure

```text
package/
├── app/
│   ├── core/
│   │   ├── orchestration
│   │   ├── workspace
│   │   ├── analysis
│   │   └── configuration
│   ├── llm/
│   │   └── nebius_client.py
│   ├── tools/
│   │   ├── financial.py
│   │   └── business_analytics.py
│   ├── database/
│   │   └── db.py
│   └── ui/
│       └── dashboard.py
│
├── frontend/
│   └── React + Vite dashboard
│
├── scripts/
│   └── seed_demo.py
│
├── tests/
│
├── .env.example
├── Dockerfile
├── pytest.ini
├── requirements.txt
└── README.md
```

---

# 🛠️ Local Setup

## 1. Clone the repository

```bash
git clone https://github.com/JayBhadoria11/ai-company-os.git
cd ai-company-os
```

## 2. Create a virtual environment

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## 3. Install Python dependencies

```powershell
pip install -r requirements.txt
```

## 4. Configure Nebius

Copy the environment template:

```powershell
Copy-Item .env.example .env
```

Then add your own Nebius API key to `.env`:

```text
NEBIUS_API_KEY=your_key_here
```

The real `.env` file is git-ignored and must never be committed.

---

# ▶️ Running the Application

## Recommended: Single-Service Mode

Build the React dashboard:

```powershell
cd frontend
npm install
npm run build
cd ..
```

Start FastAPI:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000
```

The production frontend is served directly by FastAPI.

---

## Development Mode

### Terminal 1 — API

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

### Terminal 2 — React dashboard

```powershell
cd frontend
npm run dev
```

The development dashboard communicates with the FastAPI backend.

---

# 🎮 Demo Data

The repository includes a demo seeding system.

Run:

```powershell
python scripts/seed_demo.py
```

The seeder creates a ready-to-demo company workspace and bundled demo dataset.

The operation is idempotent and only runs when the Company Workspace is completely empty.

It will not overwrite existing user data.

---

# 🧪 Testing

Run the Python test suite:

```powershell
python -m pytest
```

The test suite is designed to run without network access or a real API key.

The optional live Nebius integration test can be enabled with:

```powershell
$env:NEBIUS_LIVE_TESTS=1
python -m pytest tests/test_live_nebius.py
```

Frontend validation:

```powershell
cd frontend
npm run lint
npm run build
```

---

# 🐳 Docker

Build the production image:

```powershell
docker build -t ai-company-os .
```

Run it:

```powershell
docker run --env-file .env -p 8000:8000 ai-company-os
```

Then open:

```text
http://localhost:8000
```

The Docker image builds the React frontend and packages it with the FastAPI application into a single deployable service.

---

# 🔐 Security

- `.env` is git-ignored.
- Never commit real API keys.
- Use `.env.example` as the configuration template.
- API keys should remain server-side.
- If a key is ever exposed, rotate it immediately in the Nebius Token Factory console.

---

# 🧠 Large Dataset Handling

Large datasets introduced an important engineering challenge.

An early version of the synthesis pipeline duplicated large portions of deterministic evidence, producing prompts of roughly **65,000 characters**.

This could cause NVIDIA Nemotron to reach its context/output boundary before producing usable content.

Instead of simply increasing the output-token limit, we redesigned the synthesis context.

The system now:

- Compacts evidence before sending it to the model.
- Removes duplicated cross-tab data.
- Preserves the important computed findings.
- Keeps the complete deterministic analysis inside the application.
- Sends a bounded decision-relevant context to Nemotron.

In our representative test, the synthesis prompt was reduced from approximately **65,000 characters to approximately 12,000 characters**.

This made the production workflow reliable for large datasets.

---

# 📚 Development Notes

Important components include:

- `app/core/config.py` — Environment configuration
- `app/llm/nebius_client.py` — Nebius/NVIDIA API client
- `app/tools/financial.py` — Deterministic financial calculations
- `app/tools/business_analytics.py` — Business trend and ratio analysis
- `app/database/db.py` — SQLite persistence
- `app/core/agent.py` — Specialist agent execution
- `app/core/commander.py` — Commander/CEO orchestration
- `app/core/company_workspace.py` — Company profile and dataset persistence
- `app/core/company_context.py` — Active company context and caching
- `app/ui/dashboard.py` — Legacy Streamlit interface

---

# 🎯 What We Learned

Building an agentic application is not only about selecting a powerful model.

The project taught us that reliable AI systems require:

- **Deterministic evidence**
- **Controlled context**
- **Clear agent responsibilities**
- **Explicit limitations**
- **Human approval**
- **Production testing**
- **Good data boundaries**

One of the biggest lessons was that **context engineering can be just as important as model selection**.

---

# 🚀 Future Direction

AI Company OS can evolve into a broader AI operating layer for small and growing companies.

Future directions include:

- More specialized business agents
- Additional data integrations
- More automated workflows
- Richer company memory
- More advanced approval and action systems
- Deeper financial, marketing, HR, and operational intelligence

The goal is to move from:

**"Ask an AI about your data"**

to:

**"Give your company an AI operating layer that understands its evidence and helps humans make better decisions."**

---

## License

MIT License.
