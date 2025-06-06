from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

import os
import uuid
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

# In-memory session store
sessions = {}

app = FastAPI(title="AI-Powered Docker Image Optimizer")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_dockerfile(file: UploadFile = File(...)):
    """
    Receive Dockerfile upload.
    Returns sessionID, filename, and raw contents.
    """
    content = await file.read()
    dockerfile_str = content.decode("utf-8")
    session_id = str(uuid.uuid4())
    sessions[session_id] = {"raw": dockerfile_str}
    return {"sessionID": session_id, "filename": file.filename, "dockerfile": dockerfile_str}

@app.get("/lint")
async def lint(sessionID: str):
    """
    Return lint results for the specified session's Dockerfile.
    """
    raw = sessions.get(sessionID, {}).get("raw", "")
    results = lint_service(raw)
    return {"lintResults": results}

@app.get("/layers")
async def layers(sessionID: str):
    """
    Return per-layer size breakdown for the specified session's Dockerfile.
    """
    raw = sessions.get(sessionID, {}).get("raw", "")
    report = layer_profiler(raw)
    return {"layerReport": report}

@app.get("/suggestions")
async def suggestions(sessionID: str):
    """
    Return AI-driven optimization suggestions for the specified session's Dockerfile.
    """
    raw = sessions.get(sessionID, {}).get("raw", "")
    optimized = sessions.get(sessionID, {}).get("optimized", ai_optimize(raw))
    suggestion_text = ai_optimize(raw)
    suggestions = suggestion_text.splitlines()
    return {"suggestions": suggestions}

# Service implementations
def lint_service(dockerfile: str):
    # TODO: implement lint rules
    return []

def layer_profiler(dockerfile: str):
    # TODO: implement BuildKit-based layer profiling
    return []

def ai_optimize(dockerfile: str):
    # AI optimization via OpenAI GPT-4
    prompt = (
        "Optimize the following Dockerfile for minimal image size and best practices.\n\n"
        f"{dockerfile}"
    )
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a Dockerfile optimization assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    return response.choices[0].message.content

def build_chat_prompt(raw: str, optimized: str, history: list, question: str) -> str:
    history_str = "\n".join(f"{h['role']}: {h['content']}" for h in history)
    return (
        "You are a Dockerfile optimization assistant.\n"
        "Raw Dockerfile:\n" + raw + "\n\n"
        "Optimized Dockerfile:\n" + optimized + "\n\n"
        "Conversation history:\n" + history_str + "\n\n"
        "User question:\n" + question
    )

async def ai_chat(prompt: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant for Dockerfile optimization."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

@app.post("/optimize")
async def optimize(payload: dict):
    """
    Optimize Dockerfile via lint, profiling, and AI.
    """
    session_id = payload.get("sessionID") or str(uuid.uuid4())
    dockerfile_str = payload.get("dockerfile")
    sessions[session_id] = {"raw": dockerfile_str}
    lint_results = lint_service(dockerfile_str)
    layer_report = layer_profiler(dockerfile_str)
    optimized = ai_optimize(dockerfile_str)
    sessions[session_id]["optimized"] = optimized
    return {
        "sessionID": session_id,
        "optimizedDockerfile": optimized,
        "lintResults": lint_results,
        "layerReport": layer_report,
    }

@app.post("/chat")
async def chat(payload: dict):
    """
    Handle chat questions against uploaded Dockerfile.
    """
    session_id = payload.get("sessionID")
    history = payload.get("history", [])
    question = payload.get("question")
    session_data = sessions.get(session_id)
    if not session_data:
        return {"error": "Invalid sessionID"}
    prompt = build_chat_prompt(
        session_data["raw"], session_data.get("optimized", session_data["raw"]), history, question
    )
    response = await ai_chat(prompt)
    history.append({"role": "assistant", "content": response})
    return {"response": response, "history": history}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
