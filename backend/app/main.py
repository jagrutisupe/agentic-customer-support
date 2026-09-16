from fastapi import FastAPI

app = FastAPI(
    title="Agentic Customer Support Associate",
    description="AI-powered customer support system with ReAct, RAG and controlled tools.",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "message": "Agentic Customer Support Associate API",
        "status": "running",
        "version": "0.1.0"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }