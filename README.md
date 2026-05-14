# StratOS AI: Distributed Multi-Agent Business Simulation Platform

StratOS AI is a high-fidelity, event-driven business simulation platform that utilizes a swarm of specialized AI agents to architect, analyze, and project the lifecycle of a business venture. From technical architecture to SaaS economics and risk assessment, StratOS AI provides venture-grade insights through a resilient, distributed pipeline.

StratOS AI Dashboard

## 📸 Gallery

<p align="center">
  <img src="assets/dashboard_main.png" width="45%" alt="Dashboard Overview" />
</p>

## 🎬 Product Demo


https://github.com/user-attachments/assets/6cb240c2-8f76-49d1-81d3-de56228e2dd8


<p align="center">
  <video width="100%" controls>
    <source src="assets/demo_video.webm" type="video/webm">
    Your browser does not support the video tag.
  </video>
</p>

## 🚀 Key Features

- **Distributed Orchestration**: Scalable multi-agent workflow powered by **Kafka** and **Redis**.
- **Specialized Agent Swarm**:
    - **Architect**: Designs the multi-layer execution plan.
    - **Market Specialist**: Conducts competitive analysis and TAM/SAM/SOM modeling.
    - **Technical Architect**: Designs the stack and infrastructure.
    - **Financial Engine**: Projects SaaS economics, burn rate, and ROI.
    - **Risk Evaluator**: Identifies operational and market dependencies.
- **Real-time Streaming**: Live agent activity stream and progress tracking via Streamlit.
- **Enterprise Hardening**: Secure authentication, personal API key management, and robust error recovery.

---

StratOS AI is built on a modern microservices architecture designed for high throughput and fault tolerance.
### 🛰️ System Flow (Mermaid)
<p align="center">
  <img src="assets/architecture_diagram.png" width="100%" alt="StratOS AI Architecture Diagram" />
</p>

---

## 🛠️ Tech Stack

- **Frontend**: Streamlit, Custom CSS
- **Backend**: FastAPI (Python 3.10+)
- **Message Broker**: Apache Kafka
- **Database**: PostgreSQL
- **Caching**: Redis
- **LLM Orchestration**: OpenRouter API
- **Containerization**: Docker & Docker Compose

---

## 📥 Setup Instructions

### Prerequisites
- Docker & Docker Compose
- [OpenRouter API Key](https://openrouter.ai/keys)

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/StratOS-AI.git
cd StratOS-AI
```

### 2. Configure Environment
Create a `.env` file in the root directory based on `.env.example`:
```bash
cp .env.example .env
```
Edit `.env` and add your `OPENROUTER_API_KEY` and other credentials.

### 3. Launch with Docker
```bash
docker-compose up --build
```

The platform will be available at:
- **Frontend**: `http://localhost:8501`
- **API Gateway**: `http://localhost:8000`

---

## 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*Built for the future of automated business intelligence.*
