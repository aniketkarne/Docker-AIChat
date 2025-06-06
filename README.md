# AI-Powered Docker Image Optimizer

A full-stack application demonstrating AI-driven Dockerfile analysis and optimization.  
Project showcasing FastAPI + Python backend, Next.js + TypeScript + Tailwind CSS frontend, OpenAI GPT-4 integration, and Docker Compose orchestration.

---

## Features

- **Upload or Paste Dockerfile**: Simple UI to drop a file or paste Dockerfile text.
- **Static Linting**: Identifies anti-patterns and best-practice violations.
- **Layer Profiling**: Emulates BuildKit to report per-layer size breakdown.
- **AI Optimization**: Submits the Dockerfile to OpenAI GPT-4 for size and best-practice improvements.
- **Optimized Diff & Download**: View optimized Dockerfile in Monaco Editor and download the result.
- **In-Browser Chat**: Ephemeral session-based Q&A against your Dockerfile (no external database).
- **Docker Compose**: One-command orchestration of backend and frontend services.

---

## Architecture

```mermaid
flowchart LR
  subgraph Frontend
    U[User Upload/Paste Dockerfile] -->|POST /upload| A[Upload Page]
    A -->|display| E[Editor View (Monaco)]
    E -->|"Optimize"| O[Optimize Button]
    O -->|POST /optimize| B[FastAPI Backend]
    B -->|optimized Dockerfile| E
    E -->|"Download"| D[Download File]
    E -->|"Chat"| C[Chat Panel]
    C -->|send message| B
    B -->|stream response| C
  end

  subgraph Backend
    B[FastAPI] --> AI[OpenAI GPT-4]
    B --> L[Lint Service]
    B --> P[Layer Profiler]
  end
```

---

## Tech Stack

- **Backend**:  
  - Python 3.11, FastAPI, Poetry  
  - OpenAI Python SDK  
- **Frontend**:  
  - Next.js, React, TypeScript  
  - Tailwind CSS, Monaco Editor, Chart.js  
- **Containerization**:  
  - Dockerfiles for backend & frontend  
  - Docker Compose orchestration  

---

## Getting Started

1. Clone the repository  
   ```bash
   git clone https://github.com/your-username/ai-docker-image-optimizer.git
   cd ai-docker-image-optimizer
   ```

2. Set OpenAI API key  
   ```bash
   export OPENAI_API_KEY="your_api_key_here"
   ```

3. Development with Docker Compose  
   ```bash
   docker-compose up --build
   ```
   - Backend at http://localhost:8000  
   - Frontend at http://localhost:3000  

4. Or run services manually  

   **Backend**  
   ```bash
   cd backend
   poetry install
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   **Frontend**  
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. Open http://localhost:3000 in your browser, upload or paste a Dockerfile, click **Optimize**, review and download the optimized Dockerfile, then click **Chat** to interact.

---

## Repository Structure

```
.
├── README.md
├── docker-compose.yml
├── backend/
│   ├── main.py
│   ├── pyproject.toml
│   └── Dockerfile
└── frontend/
    ├── pages/
    │   ├── _app.tsx
    │   └── index.tsx
    ├── styles/
    │   └── globals.css
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── tsconfig.json
    ├── package.json
    └── Dockerfile
```

---

## License

MIT License  
© 2025 AniketKarne