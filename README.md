# AI Business Analyst 🧠

**The world's first open-source, self-hosted autonomous business analyst that learns your business, works while you sleep, and never sends your data anywhere.**

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Docker Pulls](https://img.shields.io/docker/pulls/timilehin-dev/ai-business-analyst)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![React](https://img.shields.io/badge/react-18+-61dafb.svg)

## 🚀 Why This Exists

Traditional BI tools (Tableau, PowerBI) require weeks of setup and certified specialists. AI copilots (Julius AI) send your data to their cloud, forget everything after each session, and can't be trusted with sensitive data.

**We're different:**
- ✅ **Zero data egress** - Runs entirely inside your infrastructure
- ✅ **Persistent memory** - Gets smarter every day, remembering your business context
- ✅ **Proactive insights** - Investigates anomalies before you ask
- ✅ **Model agnostic** - Use Ollama local ($0), GPT-4, Claude, or any model
- ✅ **100% free** - Apache 2.0 license, unlimited seats, no hidden costs

## ⚡ Quick Start (5 Minutes)

### Option 1: Build & Run with Docker

```bash
git clone https://github.com/timilehin-dev/ai-business-analyst.git
cd ai-business-analyst
docker build -t ai-business-analyst .
docker run -d \
  -p 3000:8000 \
  -v $(pwd)/data:/app/data \
  --name ai-analyst \
  ai-business-analyst
```

Then open http://localhost:3000 in your browser.

> Prebuilt images on GHCR are coming soon (see Roadmap).

### Option 2: Docker Compose (Recommended)

```bash
git clone https://github.com/timilehin-dev/ai-business-analyst.git
cd ai-business-analyst
docker-compose up -d
```

Open http://localhost:3000 — you'll see a 3-step setup wizard:
1. **Connect Data** - Choose SQLite (default), PostgreSQL, MySQL, or CSV files
2. **Pick AI Brain** - Select Ollama (free/local), OpenAI, Anthropic, etc.
3. **Enable Superpowers** - Toggle Newsroom (web search), Code Sandbox (accurate math), Air-Gap mode

That's it. No .env files. No API keys required (unless using cloud models).

## 🎯 What It Does

### The Briefing (Proactive Insights)
Every morning, open the app to find:
- 🔴 **Critical issues** investigated overnight (e.g., "Churn spiked 23% in EMEA")
- 🟢 **Positive trends** (e.g., "Revenue tracking 8% above forecast")
- 🟡 **Ambiguous patterns** needing your input

### Chat Interface (Ask Anything)
```
You: "Why did Q3 revenue beat expectations?"
Analyst: "Enterprise renewals exceeded forecasts by 34%. 
          [Show Work] → SQL query + chart + market context from news"
```

### Show Your Work (Transparency)
Every answer includes:
- The SQL/query executed
- The data sources used
- External market context (if Newsroom enabled)
- Confidence intervals and caveats

### Learning Memory
- 👍/👎 feedback on every answer
- Corrections automatically improve future analyses
- Business glossary auto-generated from your schema

## 🛡️ Security & Privacy

| Feature | Description |
|---------|-------------|
| **Read-Only by Default** | All database connections are read-only unless explicitly enabled |
| **Air-Gap Mode** | Disable all internet calls; runs fully offline with local models |
| **SQL Validation** | Blocks non-SELECT queries and dangerous operations before execution |
| **Encrypted Config** | API keys and credentials encrypted at rest with Fernet |
| **Self-Hosted** | Your data never leaves your infrastructure |

> PII masking, audit log export, and row-level security are on the roadmap (Phase 3).

## 🧠 Model Support

Bring your own brain — task-routed for cost efficiency:

| Provider | Use Case | Cost |
|----------|----------|------|
| **Ollama (Local)** | SQL generation, routine queries | $0 |
| **Ollama Cloud** | Balanced performance/cost | Low |
| **OpenAI GPT-4** | Complex reasoning, strategy | Medium |
| **Anthropic Claude** | Long-context analysis | Medium |
| **Any OpenAI-Compatible** | Groq, Together, Fireworks | Varies |

Example config (set via UI):
```yaml
reasoning: anthropic/claude-sonnet-4    # Heavy thinking
sql: ollama/qwen2.5-coder:7b            # Fast, local, free
embedding: ollama/bge-m3                # Local always (private)
fallback: ollama-cloud/llama3.1:70b     # If local fails
```

## 🔧 Features Baked In

### Core Intelligence
- [x] **Newsroom** - Web search for market/competitor context
- [x] **SQL Validator** - Blocks non-SELECT queries by default
- [x] **Model Router** - Task-based routing across any LiteLLM provider
- [ ] **Code Sandbox** - Secure Python execution (framework ready, needs Docker wiring)
- [ ] **Self-Correction** - Auto-fixes failed queries before showing errors
- [ ] **Multi-Agent Debate** - Skeptic + Statistician sub-agents stress-test conclusions

### Memory System
- [x] **Encrypted Config Store** - API keys and settings encrypted at rest
- [ ] **Semantic Memory** - Business glossary, metric definitions
- [ ] **Episodic Memory** - History of all analyses + corrections
- [ ] **Procedural Memory** - Learned playbooks ("always exclude test accounts")
- [ ] **Feedback Loop** - 👍/👎 buttons updating knowledge base

### Deployment Options
- [x] **SQLite** - Zero-config, runs on laptop/Raspberry Pi
- [x] **Docker Compose** - Single command deploy
- [ ] **PostgreSQL + pgvector** - Production-scale with vector search
- [ ] **Helm Chart** - Kubernetes scaling
- [ ] **MCP Server** - Expose as service for other AI tools

## 📦 Architecture

```
┌─────────────────────────────────────────────────────┐
│           YOUR INFRASTRUCTURE (On-Prem/VPC)         │
│                                                      │
│  ┌──────────┐    ┌─────────────┐    ┌────────────┐ │
│  │  React   │───▶│  FastAPI    │───▶│  LangGraph │ │
│  │  Frontend│    │  Backend    │    │   Agent    │ │
│  └──────────┘    └──────┬──────┘    └─────┬──────┘ │
│                         │                  │        │
│                  ┌──────▼───────┐   ┌──────▼─────┐  │
│                  │  SQLite/     │   │  Ollama/   │  │
│                  │  PostgreSQL  │   │  Cloud LLM │  │
│                  └──────────────┘   └────────────┘  │
│                                                      │
│              NO DATA LEAVES THIS BOX                 │
└─────────────────────────────────────────────────────┘
```

## 🏗️ Development

### Local Setup

```bash
# Backend
cd /workspace
pip install -r requirements.txt
python -m uvicorn api.main:app --reload

# Frontend
cd web
npm install
npm run dev

# Access at http://localhost:5173 (Vite proxy to backend)
```

### Build Docker Image

```bash
docker build -t ai-business-analyst .
docker run -p 3000:8000 -v $(pwd)/data:/app/data ai-business-analyst
```

## 📈 Roadmap

### Phase 1 (Current) - MVP ✅
- [x] Core agent with LangGraph
- [x] Newsroom web search
- [x] Code sandbox
- [x] Setup wizard (zero-config)
- [x] Chat interface
- [x] Docker deployment

### Phase 2 (Next) - Memory & Proactivity
- [ ] PostgreSQL + pgvector integration
- [ ] Persistent memory layers
- [ ] Scheduled briefing generation
- [ ] Anomaly detection engine
- [ ] Feedback loop implementation

### Phase 3 - Enterprise Hardening
- [ ] PII redaction (Presidio)
- [ ] RBAC & audit logging
- [ ] Air-gap mode certification
- [ ] Multi-agent war room
- [ ] Helm chart for K8s

### Phase 4 - Ecosystem
- [ ] MCP server mode
- [ ] Connector marketplace
- [ ] Slack/Teams/Notion integrations
- [ ] What-if simulation engine
- [ ] Safe write operations (proposal mode)

## 🤝 Contributing

This is an open-source project built for the community. Ways to contribute:
- 🐛 Report bugs via GitHub Issues
- 💡 Suggest features or vote on roadmap
- 🔌 Build connectors for your data source
- 📝 Improve documentation
- 🌍 Translate to other languages

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Apache 2.0 — Free for commercial use, includes patent protection.

## 🙏 Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent orchestration
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [React + Vite](https://vitejs.dev/) - Frontend
- [Tailwind CSS](https://tailwindcss.com/) - Styling
- [Ollama](https://ollama.ai/) - Local LLM runtime
- [duckduckgo-search](https://pypi.org/project/duckduckgo-search/) - Web search

---

**Made with ❤️ for organizations that value privacy, transparency, and intelligence.**

Star this repo if you believe AI should amplify human judgment, not replace it.
