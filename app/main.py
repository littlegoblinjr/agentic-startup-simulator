from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.routes import router as api_router
from app.memory.db import init_db
from app.tools.registry import register_tool
from app.tools.web_search import WebSearchTool
from app.tools.python_executor import PythonExecutorTool

app = FastAPI(title="AI Startup Simulator API")

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, restrict this.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Initialize database connection pool
    try:
        await init_db()
        print("DATABASE: Initialized successfully.")
    except Exception as e:
        print(f"DATABASE ERROR: {e}")

    # Register tools for agents to use
    register_tool(WebSearchTool())
    register_tool(PythonExecutorTool())
    print("TOOLS: Registered WebSearch and PythonExecutor.")

# Create logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

# Include routes
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "AI Startup Simulator API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=1234, reload=True)
