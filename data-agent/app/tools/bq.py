"""BigQuery read-only tools with dataset allowlist enforcement."""

from __future__ import annotations

import logging
import re
from typing import Any

from google.cloud import bigquery

from app.config import Settings, get_settings

log = logging.getLogger(__name__)

# Match project.dataset.table or `project.dataset.table` or dataset.table
_FQN_RE = re.compile(
    r"`?(?:(?P<project>[a-zA-Z0-9_\-]+)\.)?(?P<dataset>[a-zA-Z0-9_]+)\.(?P<table>[a-zA-Z0-9_]+)`?"
)
_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE|"
    r"EXPORT|LOAD|CALL|EXECUTE|SCRIPT)\b",
    re.IGNORECASE,
)


class BqGuardError(ValueError):
    """Raised when a query violates read-only / allowlist policy."""


class BigQueryTools:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = bigquery.Client(
            project=self.settings.bq_project,
            location=self.settings.bq_location,
        )

    def list_tables(self, dataset: str, max_results: int = 100) -> dict[str, Any]:
        dataset = dataset.strip()
        if dataset not in self.settings.allowed_datasets:
            raise BqGuardError(
                f"Dataset '{dataset}' not allowed. "
                f"Allowed: {sorted(self.settings.allowed_datasets)}"
            )
        tables = []
        for i, table in enumerate(
            self.client.list_tables(f"{self.settings.bq_project}.{dataset}")
        ):
            if i >= max_results:
                break
            tables.append(
                {
                    "table_id": table.table_id,
                    "fqn": f"{table.project}.{table.dataset_id}.{table.table_id}",
                    "type": table.table_type,
                }
            )
        return {"dataset": dataset, "count": len(tables), "tables": tables}

    def describe_table(self, table_fqn: str) -> dict[str, Any]:
        project, dataset, table = self._parse_and_guard_fqn(table_fqn)
        ref = self.client.get_table(f"{project}.{dataset}.{table}")
        return {
            "fqn": f"{ref.project}.{ref.dataset_id}.{ref.table_id}",
            "description": ref.description,
            "num_rows": ref.num_rows,
            "num_bytes": ref.num_bytes,
            "partitioning": (
                {
                    "type": ref.time_partitioning.type_,
                    "field": ref.time_partitioning.field,
                }
                if ref.time_partitioning
                else None
            ),
            "clustering_fields": list(ref.clustering_fields or []),
            "schema": [
                {
                    "name": f.name,
                    "type": f.field_type,
                    "mode": f.mode,
                    "description": f.description,
                }
                for f in ref.schema
            ],
        }

    def run_query(self, sql: str) -> dict[str, Any]:
        sql = sql.strip().rstrip(";")
        self._assert_readonly(sql)
        self._assert_datasets_allowed(sql)

        job_config = bigquery.QueryJobConfig(
            dry_run=False,
            use_query_cache=True,
            maximum_bytes_billed=self.settings.bq_max_bytes_billed,
        )
        # Dry-run first for early guard / cost estimate
        dry_config = bigquery.QueryJobConfig(
            dry_run=True,
            use_query_cache=False,
            maximum_bytes_billed=self.settings.bq_max_bytes_billed,
        )
        dry_job = self.client.query(sql, job_config=dry_config)
        estimated_bytes = dry_job.total_bytes_processed or 0
        if estimated_bytes > self.settings.bq_max_bytes_billed:
            raise BqGuardError(
                f"Query would scan ~{estimated_bytes} bytes, "
                f"exceeds limit {self.settings.bq_max_bytes_billed}"
            )

        job = self.client.query(sql, job_config=job_config)
        result = job.result(timeout=self.settings.bq_query_timeout_sec)
        rows: list[dict[str, Any]] = []
        for i, row in enumerate(result):
            if i >= self.settings.bq_max_rows:
                break
            rows.append(dict(row.items()))

        return {
            "row_count_returned": len(rows),
            "total_rows": result.total_rows,
            "bytes_processed": job.total_bytes_processed,
            "bytes_billed": job.total_bytes_billed,
            "truncated": len(rows) < (result.total_rows or 0),
            "schema": [f.name for f in result.schema] if result.schema else [],
            "rows": rows,
        }

    def _parse_and_guard_fqn(self, table_fqn: str) -> tuple[str, str, str]:
        cleaned = table_fqn.strip().strip("`")
        parts = cleaned.split(".")
        if len(parts) == 2:
            project = self.settings.bq_project
            dataset, table = parts
        elif len(parts) == 3:
            project, dataset, table = parts
        else:
            raise BqGuardError(
                f"Invalid table FQN '{table_fqn}'. Expect dataset.table or project.dataset.table"
            )
        if project != self.settings.bq_project:
            raise BqGuardError(f"Project '{project}' not allowed")
        if dataset not in self.settings.allowed_datasets:
            raise BqGuardError(
                f"Dataset '{dataset}' not allowed. "
                f"Allowed: {sorted(self.settings.allowed_datasets)}"
            )
        return project, dataset, table

    def _assert_readonly(self, sql: str) -> None:
        if _FORBIDDEN_SQL.search(sql):
            raise BqGuardError(
                "Only read-only SELECT/WITH queries are allowed "
                "(no DML/DDL/EXPORT/LOAD)."
            )
        # Must look like a query starting with SELECT or WITH
        head = sql.lstrip().split(None, 1)[0].upper() if sql.strip() else ""
        if head not in {"SELECT", "WITH"}:
            raise BqGuardError("SQL must start with SELECT or WITH")

    def _assert_datasets_allowed(self, sql: str) -> None:
        """Reject any table reference outside project + dataset allowlist.

        Parses backtick FQNs, bare project.dataset.table, and FROM/JOIN
        dataset.table forms. Alias.column is not treated as a table unless
        it appears after FROM/JOIN.
        """
        allowed = self.settings.allowed_datasets
        project = self.settings.bq_project
        violations: set[str] = set()

        def _check(proj: str | None, dataset: str, raw: str) -> None:
            if proj and proj != project:
                violations.add(f"project:{proj} via {raw}")
            if dataset not in allowed:
                violations.add(f"dataset:{dataset} via {raw}")

        # `project.dataset.table` or `dataset.table`
        for m in re.finditer(r"`([^`]+)`", sql):
            inner = m.group(1).strip()
            parts = inner.split(".")
            if len(parts) == 3:
                _check(parts[0], parts[1], inner)
            elif len(parts) == 2:
                # Treat as dataset.table (common BQ style inside backticks)
                _check(None, parts[0], inner)

        # Bare project.dataset.table (hyphen allowed in project id)
        for m in re.finditer(
            r"(?<![`\w])([a-zA-Z0-9_\-]+)\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)(?![`\w])",
            sql,
        ):
            _check(m.group(1), m.group(2), m.group(0))

        # FROM/JOIN dataset.table (with or without backticks already partially handled)
        for m in re.finditer(
            r"(?is)\b(?:FROM|JOIN)\s+`?([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)`?",
            sql,
        ):
            _check(None, m.group(1), f"{m.group(1)}.{m.group(2)}")

        if violations:
            raise BqGuardError(
                f"SQL references disallowed resources: {sorted(violations)}. "
                f"Allowed project={project}, datasets={sorted(allowed)}"
            )


TOOL_DECLARATIONS = [
    {
        "name": "list_tables",
        "description": (
            "List tables in an allowed BigQuery dataset. "
            "Use when you need to discover available tables. "
            f"Allowed datasets only: qpon_rpt_d, qpon_dws_d, qpon_dwd_d."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "description": "Dataset id, e.g. qpon_rpt_d",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max tables to return (default 100)",
                },
            },
            "required": ["dataset"],
        },
    },
    {
        "name": "describe_table",
        "description": (
            "Get schema, partitioning, and description for a table. "
            "Prefer this before writing SQL."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "table_fqn": {
                    "type": "string",
                    "description": (
                        "Table FQN: dataset.table or project.dataset.table"
                    ),
                },
            },
            "required": ["table_fqn"],
        },
    },
    {
        "name": "run_query",
        "description": (
            "Execute a read-only BigQuery SQL (SELECT/WITH only) against allowed "
            "datasets. Always filter by partition_date when the table is partitioned. "
            "Prefer aggregations and LIMIT. Results are capped."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "BigQuery Standard SQL starting with SELECT or WITH",
                },
            },
            "required": ["sql"],
        },
    },
]


def dispatch_tool(name: str, args: dict[str, Any], tools: BigQueryTools) -> Any:
    if name == "list_tables":
        max_results = min(int(args.get("max_results") or 100), 500)
        return tools.list_tables(dataset=args["dataset"], max_results=max_results)
    if name == "describe_table":
        return tools.describe_table(args["table_fqn"])
    if name == "run_query":
        return tools.run_query(args["sql"])
    raise BqGuardError(f"Unknown tool: {name}")
