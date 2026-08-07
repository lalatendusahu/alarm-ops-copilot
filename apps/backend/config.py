import os


class Settings:
    mcp_servers = {
        "alarm": os.getenv("MCP_ALARM_URL", "http://localhost:9001/mcp"),
        "workorders": os.getenv("MCP_WORKORDERS_URL", "http://localhost:9002/mcp"),
    }
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    max_tool_iterations = int(os.getenv("COPILOT_MAX_TOOL_ITERATIONS", "8"))
    rag_top_k = int(os.getenv("RAG_TOP_K", "4"))
    rag_min_score = float(os.getenv("RAG_MIN_SCORE", "0.30"))


settings = Settings()
