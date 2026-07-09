import json

from src.changes.models import ToolCallTrace
from src.db.models import ToolTraceRecord
from src.db.session import SessionLocal


class SQLiteToolTraceStore:
    def add(self, trace: ToolCallTrace) -> ToolCallTrace:
        with SessionLocal() as db:
            db.add(
                ToolTraceRecord(
                    tool_name=trace.tool_name,
                    query=trace.query,
                    input_json=json.dumps(trace.input),
                    result_count=trace.result_count,
                    status=trace.status,
                    error=trace.error,
                    created_at=trace.created_at,
                )
            )
            db.commit()

        return trace

    def list(self) -> list[ToolCallTrace]:
        with SessionLocal() as db:
            rows = db.query(ToolTraceRecord).order_by(ToolTraceRecord.created_at).all()

            return [
                ToolCallTrace(
                    tool_name=row.tool_name,
                    query=row.query,
                    input=json.loads(row.input_json),
                    result_count=row.result_count,
                    status=row.status,
                    error=row.error,
                    created_at=row.created_at,
                )
                for row in rows
            ]


tool_trace_store = SQLiteToolTraceStore()