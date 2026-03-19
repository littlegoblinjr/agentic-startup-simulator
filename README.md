# 🚀 AI Startup Simulator: Swarm-Powered Venture Validation

**AI Startup Simulator** is an advanced multi-agent orchestrator designed to stress-test, validate, and build comprehensive strategies for new startup ideas in real-time. By deploying a swarm of 8 specialized AI researchers, the simulator provides deep market analysis, technical architecture, and financial feasibility reports in minutes.

---

## 🧠 The Agent Swarm
Our simulation is powered by a coordinated swarm of 8 specialized agents, each with a dedicated role in the venture building process:

1.  **📊 Market Agent**: Conducts deep-dive research into target audiences, market size, and competitors.
2.  **💻 Tech Agent**: Designs cloud-native architectures, selects the optimal tech stack, and outlines product roadmaps.
3.  **💰 Finance Agent**: Models revenue streams, calculates burn rates, and estimates funding requirements.
4.  **🎤 Pitch Agent**: Generates brand identity, taglines, and "elevator pitches" for the venture.
5.  **🧩 Synthesis Agent**: Consolidates research from all agents into a unified, strategic venture briefing.
6.  **⚖️ Evaluation Agent**: Acts as a harsh VC critic, scoring the venture on a 1-100 scale across multiple metrics.
7.  **📅 Planner Agent**: Dynamically builds a Task DAG (Directed Acyclic Graph) for the simulation flow.
8.  **🛡️ Guardrail Agent**: Screens every incoming prompt for semantic validity and security.

---

## ✨ Key Features
- **Real-Time Telemetry & Monitoring**: Watch the agent swarm work live with real-time log streaming and execution status.
- **Neon DB Persistence**: Every simulation run is saved to a Neon PostgreSQL database for reliable history and cloud access.
- **Granular Cost Tracking**: 100% transparency on OpenAI API spend, tracked per-token and per-agent action.
- **Neural Intel Briefings**: High-level executive summaries and "Neural Briefings" for every completed research task.
- **Safety First**: Integrated LLM-powered guardrails to prevent prompt abuse and waste of resources.

---

## 🛠️ Tech Stack
- **Backend**: Python, FastAPI, Asyncio
- **Frontend**: React, Tailwind CSS, Framer Motion, Lucide React
- **Intelligence**: OpenAI (`gpt-4o-mini`), Sentence Transformers
- **Database**: Neon (PostgreSQL), `asyncpg`
- **Searching**: Tavily AI, Trafilatura

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/littlegoblinjr/agentic-startup-simulator.git
cd agentic-startup-simulator
```

### 2. Set up the Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Configure Environment
# Create a .env file with your keys
OPENAI_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
DATABASE_URL=your_neon_db_url_here

# Run the API
uvicorn app.main:app --port 1234 --reload
```

### 3. Set up the Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.