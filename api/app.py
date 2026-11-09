import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as api_router
from mcp_server.server import mcp
from mcp_server.constants import current_iso_timestamp

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(
    title="Vigil AI API & MCP Server",
    description="Autonomous Drug Safety & Pharmacovigilance Assistant powered by LangGraph, Groq, and FastMCP.",
    version="2.4.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Service health and readiness check."""
    return JSONResponse({
        "status": "healthy",
        "service": "Vigil AI",
        "version": "2.4.0",
        "mcp_endpoint": "/mcp",
        "timestamp": current_iso_timestamp()
    })

# Include existing API routes
app.include_router(api_router)

# Mount FastMCP SSE application at /mcp
app.mount("/mcp", mcp.sse_app())

# Mount static folder
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir, exist_ok=True)
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/")
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Vigil AI API is operational. Static UI not found at /static/index.html."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=True)
