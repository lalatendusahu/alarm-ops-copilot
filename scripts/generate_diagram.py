"""Renders docs/architecture-diagram.png from a fixed layout. Only needs to be re-run if
the architecture changes -- the output is committed so the docs don't depend on this
script at review time. Requires: pip install -r requirements-docs.txt
"""
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

OUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "architecture-diagram.png"

COLORS = {
    "gui": "#3B82F6",
    "orchestration": "#8B5CF6",
    "mcp": "#10B981",
    "connector": "#10B981",
    "source": "#F59E0B",
    "rag": "#14B8A6",
    "external": "#6B7280",
}


def box(ax, x, y, w, h, label, color, fontsize=9, text_color="white"):
    patch = mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.3,rounding_size=0.4",
        linewidth=1.2, edgecolor="#1F2937", facecolor=color,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=fontsize, color=text_color, wrap=True)
    return (x, y, w, h)


def dashed_boundary(ax, x, y, w, h, label):
    patch = mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.6,rounding_size=0.6",
        linewidth=1.4, edgecolor="#9CA3AF", facecolor="none", linestyle="--",
    )
    ax.add_patch(patch)
    ax.text(x + 0.3, y + h - 0.6, label, fontsize=8, color="#6B7280", style="italic")


def arrow(ax, src, dst, color="#374151", style="-|>", linestyle="solid"):
    sx, sy, sw, sh = src
    dx, dy, dw, dh = dst
    start = (sx + sw / 2, sy)
    end = (dx + dw / 2, dy + dh)
    if sy < dy:
        start = (sx + sw / 2, sy + sh)
        end = (dx + dw / 2, dy)
    patch = mpatches.FancyArrowPatch(
        start, end, arrowstyle=style, mutation_scale=14, linewidth=1.3, color=color, linestyle=linestyle,
    )
    ax.add_patch(patch)


def side_arrow(ax, src, dst, color="#374151"):
    sx, sy, sw, sh = src
    dx, dy, dw, dh = dst
    start = (sx + sw, sy + sh / 2)
    end = (dx, dy + dh / 2)
    patch = mpatches.FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=14, linewidth=1.3, color=color)
    ax.add_patch(patch)


def main():
    fig, ax = plt.subplots(figsize=(15, 11))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.set_title("Multi-MCP Enterprise Operations Copilot -- Architecture", fontsize=14, fontweight="bold", pad=20)

    gui = box(ax, 30, 88, 40, 8, "GUI (Chainlit)\nchat • tool discovery view • execution trace • RAG citations", COLORS["gui"])
    orch = box(ax, 30, 74, 40, 9, "Copilot Orchestration\nReAct loop • trace collector • confirmation gating", COLORS["orchestration"])

    mcp_client = box(ax, 12, 60, 30, 8, "MCP Client / Tool Registry\ndiscovery + namespaced dispatch", COLORS["mcp"])
    rag_service = box(ax, 58, 60, 30, 8, "RAG Retrieval Service\nembed query • FAISS search • min-score filter", COLORS["rag"])

    mcp_alarm = box(ax, 4, 46, 24, 8, "MCP Server\nAlarm Management (14 tools)", COLORS["mcp"])
    mcp_wo = box(ax, 32, 46, 24, 8, "MCP Server\nWork Orders (4 tools)", COLORS["mcp"])
    vector_index = box(ax, 60, 46, 13, 8, "Vector Index\n(FAISS)", COLORS["rag"])
    doc_store = box(ax, 76, 46, 20, 8, "Document Store\nrag/documents/*.md", COLORS["rag"])

    alarm_conn = box(ax, 4, 32, 24, 7, "Alarm API connector\n(auth, retry, trace)", COLORS["connector"])
    wo_conn = box(ax, 32, 32, 24, 7, "Work Order connector\n(auth, retry, trace)", COLORS["connector"])
    ingestion = box(ax, 62, 32, 32, 7, "RAG Ingestion Pipeline\nchunk • embed • index", COLORS["rag"])

    alarm_api = box(ax, 4, 16, 24, 9, "Alarm Management API\nFastAPI + SQLite\nbearer auth", COLORS["source"])
    wo_api = box(ax, 32, 16, 24, 9, "Work Order API\nFastAPI + SQLite\nbearer auth", COLORS["source"])

    llm = box(ax, 60, 74, 20, 9, "LLM Provider\n(OpenAI, swappable)", COLORS["external"])
    obs = box(ax, 84, 74, 14, 8, "Observability\nstructured logs, trace_id/\nclient_id propagation\n(every service below)", COLORS["external"], fontsize=7.5)

    arrow(ax, gui, orch)
    arrow(ax, orch, mcp_client)
    arrow(ax, orch, rag_service)
    side_arrow(ax, orch, llm)
    arrow(ax, mcp_client, mcp_alarm)
    arrow(ax, mcp_client, mcp_wo)
    arrow(ax, rag_service, vector_index)
    arrow(ax, vector_index, doc_store)
    arrow(ax, mcp_alarm, alarm_conn)
    arrow(ax, mcp_wo, wo_conn)
    arrow(ax, alarm_conn, alarm_api)
    arrow(ax, wo_conn, wo_api)
    arrow(ax, ingestion, vector_index)
    side_arrow(ax, doc_store, ingestion)

    side_arrow(ax, orch, obs, color="#9CA3AF")

    dashed_boundary(ax, 2, 14, 56, 12, "Auth boundary: per-source-system bearer token")
    dashed_boundary(ax, 58, 72, 24, 12, "Auth boundary: LLM provider API key")

    plt.tight_layout()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_PATH, dpi=160, facecolor="white")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
