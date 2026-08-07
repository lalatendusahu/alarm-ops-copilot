import time
import uuid
from dataclasses import dataclass, field


@dataclass
class ToolStep:
    server: str
    tool: str
    input: dict
    status: str  # ok | error
    output: dict | None = None
    error: str | None = None
    duration_ms: float = 0.0
    trace_id: str = ""


@dataclass
class TraceCollector:
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    steps: list[ToolStep] = field(default_factory=list)

    def timer(self):
        return _StepTimer(self)

    def as_dicts(self) -> list[dict]:
        return [
            {
                "server": s.server, "tool": s.tool, "input": s.input, "status": s.status,
                "output": s.output, "error": s.error, "duration_ms": round(s.duration_ms, 1),
                "trace_id": s.trace_id,
            }
            for s in self.steps
        ]

    def failed_steps(self) -> list[ToolStep]:
        return [s for s in self.steps if s.status == "error"]


class _StepTimer:
    """Context manager that times a tool call and appends a ToolStep to the collector on exit."""

    def __init__(self, collector: TraceCollector):
        self.collector = collector
        self.server = ""
        self.tool = ""
        self.input: dict = {}
        self._start = 0.0

    def begin(self, server: str, tool: str, input_args: dict):
        self.server = server
        self.tool = tool
        self.input = input_args
        self._start = time.perf_counter()
        return self

    def finish_ok(self, output: dict, trace_id: str = ""):
        self.collector.steps.append(ToolStep(
            server=self.server, tool=self.tool, input=self.input, status="ok",
            output=output, duration_ms=(time.perf_counter() - self._start) * 1000, trace_id=trace_id,
        ))

    def finish_error(self, error: str, trace_id: str = ""):
        self.collector.steps.append(ToolStep(
            server=self.server, tool=self.tool, input=self.input, status="error",
            error=error, duration_ms=(time.perf_counter() - self._start) * 1000, trace_id=trace_id,
        ))
