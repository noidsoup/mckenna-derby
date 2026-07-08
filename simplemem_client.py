#!/usr/bin/env python3
"""
SimpleMem Client - Portable wrapper for SimpleMem memory storage.

Supports both MCP (cloud) and local backends for storing and retrieving
project memory across sessions.

Drop this file into any project. Configure via .env:
  SIMPLEMEM_ENABLED=true
  SIMPLEMEM_TOKEN=<your token from mcp.simplemem.cloud>
  SIMPLEMEM_NAMESPACE=<project-slug>

Requires: requests, python-dotenv
"""

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from pathlib import Path

import requests
from dotenv import load_dotenv


@dataclass
class SimpleMemSettings:
    """Configuration settings for SimpleMem client."""
    enabled: bool
    backend: str
    mcp_url: str
    token: Optional[str]
    user_id: Optional[str]
    namespace: str
    local_dir: str
    dry_run: bool


def _to_fact_like_content(text: str, namespace: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Format content as a clear sentence so SimpleMem's extractor can store it."""
    now = time.strftime("%Y-%m-%d", time.gmtime())
    if not text.strip():
        return f"On {now} {namespace} recorded an event (no details)."
    if " | " in text:
        return f"On {now} {namespace}: {text.replace(' | ', ', ')}."
    return f"On {now} {namespace} recorded: {text}"


def _unwrap_mcp_tool_text(tool_result: Dict[str, Any]) -> Optional[str]:
    """Extract the first text payload from an MCP tools/call result."""
    if not isinstance(tool_result, dict):
        return None
    content = tool_result.get("content")
    if not isinstance(content, list) or not content:
        return None
    first = content[0]
    if not isinstance(first, dict) or first.get("type") != "text":
        return None
    text = first.get("text")
    return text if isinstance(text, str) else None


def _parse_json_if_possible(text: Optional[str]) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def load_simplemem_settings() -> "SimpleMemSettings":
    """Load SimpleMem settings from environment variables."""
    load_dotenv()
    return SimpleMemSettings(
        enabled=os.getenv("SIMPLEMEM_ENABLED", "false").lower() == "true",
        backend=os.getenv("SIMPLEMEM_BACKEND", "mcp"),
        mcp_url=os.getenv("SIMPLEMEM_MCP_URL", "https://mcp.simplemem.cloud/mcp"),
        token=os.getenv("SIMPLEMEM_TOKEN"),
        user_id=os.getenv("SIMPLEMEM_USER_ID"),
        namespace=os.getenv("SIMPLEMEM_NAMESPACE", "my-project"),
        local_dir=os.getenv("SIMPLEMEM_LOCAL_DIR", "docs/simplemem"),
        dry_run=os.getenv("SIMPLEMEM_DRY_RUN", "false").lower() == "true",
    )


class SimpleMemClient:
    """Client for interacting with SimpleMem memory storage."""

    def __init__(self, settings: SimpleMemSettings):
        self.settings = settings
        self._local_db_path = None
        self._session_id: Optional[str] = None
        if self.settings.backend == "local":
            self._init_local_storage()

    # ── MCP session ──────────────────────────────────────────────

    def _ensure_mcp_session(self) -> None:
        """Initialize MCP session (Streamable HTTP, 2025-03-26) and capture Mcp-Session-Id."""
        if self._session_id:
            return
        if not self.settings.token:
            raise RuntimeError("SIMPLEMEM_TOKEN not set - required for MCP backend")
        headers = {
            "Authorization": f"Bearer {self.settings.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                "clientInfo": {"name": f"{self.settings.namespace}-simplemem-client", "version": "1.0.0"},
            },
        }
        resp = requests.post(self.settings.mcp_url, json=init_payload, headers=headers, timeout=30)
        if not resp.ok:
            try:
                err_body = resp.json()
            except Exception:
                err_body = resp.text or resp.reason
            raise RuntimeError(f"SimpleMem MCP initialize failed: {resp.status_code} {resp.reason} - {err_body}")
        session_id = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
        if not session_id:
            raise RuntimeError("SimpleMem MCP initialize did not return Mcp-Session-Id header")
        self._session_id = session_id
        # Send initialized notification (required by MCP lifecycle)
        notif_headers = {**headers, "Mcp-Session-Id": self._session_id}
        requests.post(
            self.settings.mcp_url,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers=notif_headers,
            timeout=30,
        )

    # ── JSON-RPC ─────────────────────────────────────────────────

    def _rpc(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make JSON-RPC 2.0 request to MCP server."""
        if not self.settings.token:
            raise RuntimeError("SIMPLEMEM_TOKEN not set - required for MCP backend")
        self._ensure_mcp_session()
        payload = {"jsonrpc": "2.0", "id": "1", "method": method, "params": params}
        headers = {
            "Authorization": f"Bearer {self.settings.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Mcp-Session-Id": self._session_id,
        }
        try:
            resp = requests.post(self.settings.mcp_url, json=payload, headers=headers, timeout=30)
            if not resp.ok:
                try:
                    err_body = resp.json()
                except Exception:
                    err_body = resp.text or resp.reason
                raise RuntimeError(f"SimpleMem MCP request failed: {resp.status_code} {resp.reason} - {err_body}")
            result = resp.json()
            if "error" in result:
                raise RuntimeError(f"SimpleMem MCP error: {result['error']}")
            return result.get("result", {})
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"SimpleMem MCP request failed: {e}")

    def list_tools(self) -> Dict[str, Any]:
        """List tools exposed by the MCP server (for debugging)."""
        self._ensure_mcp_session()
        return self._rpc("tools/list", {})

    # ── Local storage ────────────────────────────────────────────

    def _init_local_storage(self) -> None:
        local_path = Path(self.settings.local_dir)
        local_path.mkdir(parents=True, exist_ok=True)
        self._local_db_path = local_path / "memories.json"
        if not self._local_db_path.exists():
            self._local_db_path.write_text(json.dumps([]))

    def _add_local(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        if not self._local_db_path:
            self._init_local_storage()
        memories = json.loads(self._local_db_path.read_text()) if self._local_db_path.exists() else []
        memories.append({
            "id": f"local_{int(time.time() * 1000)}",
            "text": text,
            "metadata": metadata or {},
            "namespace": self.settings.namespace,
            "timestamp": time.time(),
        })
        self._local_db_path.write_text(json.dumps(memories, indent=2))

    def _query_local(self, question: str) -> str:
        if not self._local_db_path:
            self._init_local_storage()
        if not self._local_db_path or not self._local_db_path.exists():
            return json.dumps({"results": [], "message": "No memories found"})
        memories = json.loads(self._local_db_path.read_text())
        words = question.lower().split()
        if not words:
            return json.dumps({"results": [], "total": 0, "source": "local"})

        def _matches(m: dict) -> bool:
            haystack = m.get("text", "").lower()
            for v in m.get("metadata", {}).values():
                haystack += " " + str(v).lower()
            return all(w in haystack for w in words)

        matches = [m for m in memories if _matches(m)]
        return json.dumps({"results": matches[:10], "total": len(matches), "source": "local"})

    # ── Public API ───────────────────────────────────────────────

    def add_memory(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a memory entry. Non-fatal: won't break calling code on failure."""
        if not self.settings.enabled:
            return
        if self.settings.dry_run:
            print(f"[SimpleMem DRY RUN] Would add memory: {text[:100]}...", flush=True)
            return
        try:
            if self.settings.backend == "mcp":
                content = _to_fact_like_content(text, self.settings.namespace, metadata)
                tool_result = self._rpc("tools/call", {
                    "name": "memory_add",
                    "arguments": {
                        "speaker": self.settings.namespace,
                        "content": content,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                })
                parsed = _parse_json_if_possible(_unwrap_mcp_tool_text(tool_result))
                if isinstance(parsed, dict) and parsed.get("entries_created") == 0:
                    self._add_local(text, metadata)
                    msg = parsed.get("message", "No extractable information")
                    print(f"[SimpleMem WARNING] Cloud created 0 entries ({msg}); stored locally.", flush=True)
            else:
                self._add_local(text, metadata)
        except Exception as e:
            print(f"[SimpleMem WARNING] Failed to add memory: {e}", flush=True)

    def query(self, question: str) -> str:
        """Query memories. Returns JSON string. Non-fatal."""
        if not self.settings.enabled:
            return json.dumps({"results": [], "message": "SimpleMem disabled"})
        try:
            if self.settings.backend == "mcp":
                result = self._rpc("tools/call", {
                    "name": "memory_retrieve",
                    "arguments": {"query": question, "top_k": 10},
                })
                mcp_text = _unwrap_mcp_tool_text(result)
                parsed = _parse_json_if_possible(mcp_text)
                if isinstance(parsed, dict) and parsed.get("total", 0) == 0:
                    return self._query_local(question)
                return mcp_text or json.dumps(result)
            else:
                return self._query_local(question)
        except Exception as e:
            print(f"[SimpleMem WARNING] Query failed: {e}", flush=True)
            return json.dumps({"results": [], "error": str(e)})

    def log_run(self, summary: Dict[str, Any]) -> None:
        """Log a script/sync run summary. Sanitizes secrets automatically."""
        if not self.settings.enabled:
            return
        sensitive = {"token", "password", "secret", "api_key", "auth"}
        sanitized = {}
        for k, v in summary.items():
            if any(s in k.lower() for s in sensitive):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, (dict, list)):
                sanitized[k] = f"{type(v).__name__}({len(v) if hasattr(v, '__len__') else '?'})"
            else:
                sanitized[k] = v
        parts = [f"Run: {summary.get('operation', 'unknown')}"]
        if "count" in summary:
            parts.append(f"Processed {summary['count']} items")
        if "errors" in summary:
            parts.append(f"Errors: {summary['errors']}")
        if "duration" in summary:
            parts.append(f"Duration: {summary['duration']}s")
        self.add_memory(" | ".join(parts), {"type": "run_log", "namespace": self.settings.namespace, "timestamp": time.time(), **sanitized})
