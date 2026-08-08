FROM python:3.12-slim AS base
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY connectors/ ./connectors/
COPY rag/ ./rag/
COPY apps/ ./apps/
COPY mcp-servers/ ./mcp-servers/
COPY alarm-simulator/ ./alarm-simulator/
COPY work-order-service/ ./work-order-service/
COPY scripts/ ./scripts/
COPY chainlit.md ./chainlit.md

# --- Alarm Management API simulator ---
FROM base AS alarm-simulator
WORKDIR /app/alarm-simulator
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# --- Work order mock service ---
FROM base AS work-order-service
WORKDIR /app/work-order-service
EXPOSE 8010
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s CMD curl -f http://localhost:8010/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]

# --- Alarm Management MCP server ---
FROM base AS mcp-alarm
WORKDIR /app
EXPOSE 9001
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s \
    CMD python -c "import socket; socket.create_connection(('localhost', 9001), 2)" || exit 1
CMD ["python", "mcp-servers/alarm_management/server.py"]

# --- Work order MCP server ---
FROM base AS mcp-workorders
WORKDIR /app
EXPOSE 9002
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s \
    CMD python -c "import socket; socket.create_connection(('localhost', 9002), 2)" || exit 1
CMD ["python", "mcp-servers/work_orders/server.py"]

# --- Copilot GUI (Chainlit), orchestrator + RAG run in-process ---
FROM base AS copilot
WORKDIR /app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s CMD curl -f http://localhost:8000/ || exit 1
CMD ["sh", "-c", "python rag/ingestion/ingest.py && python apps/frontend/run_server.py"]
