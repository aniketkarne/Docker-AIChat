# AI-Powered Docker Image Optimizer

A full-stack application demonstrating AI-driven Dockerfile analysis and optimization.  
Project showcasing FastAPI + Python backend, Next.js + TypeScript + Tailwind CSS frontend, OpenAI integration (GPT-6 Luna by default), and Docker Compose orchestration.

---

## Features

- **Upload or Paste Dockerfile**: Simple UI to drop a file or paste Dockerfile text.
- **Static Linting** *(placeholder)*: Endpoint and UI panel exist, but lint rules are not implemented yet — currently returns no findings.
- **Layer Profiling** *(placeholder)*: Endpoint and UI panel exist, but BuildKit-based profiling is not implemented yet — currently returns no data.
- **AI Optimization**: Submits the Dockerfile to OpenAI (default model `gpt-6-luna`, override with `OPENAI_MODEL`) for size and best-practice improvements.
- **Optimized Diff & Download**: View optimized Dockerfile in Monaco Editor and download the result.
- **In-Browser Chat**: Ephemeral session-based Q&A against your Dockerfile (no external database).
- **Docker Compose**: One-command orchestration of backend and frontend services.

---

## Architecture
![image](https://github.com/user-attachments/assets/c46e978c-aaa3-4765-b821-c544be03b00f)

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
   git clone https://github.com/aniketkarne/Docker-AIChat.git
   cd Docker-AIChat
   ```

2. Set your OpenAI API key  
   ```bash
   cp .env.example .env
   # then edit .env and replace the placeholder
   ```
   Only the AI-backed endpoints (`/optimize`, `/suggestions`, `/chat`) need the key.
   Optionally set `OPENAI_MODEL` to use a different OpenAI model (default: `gpt-6-luna`).

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
   pip install -r requirements.txt
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
├── CHANGELOG.md
├── LICENSE
├── .env.example
├── .gitignore
├── docker-compose.yml
├── .github/workflows/tests.yml
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   ├── .dockerignore
│   └── tests/
│       ├── conftest.py
│       └── test_api.py
└── frontend/
    ├── lib/
    │   └── api.ts
    ├── pages/
    │   ├── _app.tsx
    │   └── index.tsx
    ├── styles/
    │   └── globals.css
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── tsconfig.json
    ├── package.json
    ├── Dockerfile
    └── .dockerignore
```

---

## Tests

Backend tests (no API key or network needed):

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest
```

CI runs the backend suite on Python 3.11/3.12 and a frontend production build on every push.

---

## License

This project is licensed under the [MIT License](LICENSE).
