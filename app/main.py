from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

@app.get("/api/health")
async def root():
    return {"message": "AI Startup Simulator API is running"}

# Serve Frontend Static Files
# Note: 'static' folder is created by the Docker build stage
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

    @app.exception_handler(404)
    async def not_found(request, exc):
        return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
