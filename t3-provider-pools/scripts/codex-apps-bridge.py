#!/usr/bin/env python3
"""Expose explicitly allowed native Codex app tools as a local stdio MCP server."""

import argparse
import json
import signal
import sys

from provider_tools import MAX_BYTES, NativeTransport, SafeError, bridge_config, parse_json, read_json

PROTOCOL = "2025-06-18"


def check_content(block):
    if not isinstance(block, dict):
        raise SafeError("Native content block is incompatible")
    kind = block.get("type")
    if kind == "text":
        valid = isinstance(block.get("text"), str)
    elif kind in ("image", "audio"):
        valid = isinstance(block.get("data"), str) and isinstance(block.get("mimeType"), str)
    elif kind == "resource_link":
        valid = isinstance(block.get("uri"), str) and isinstance(block.get("name"), str)
    elif kind == "resource":
        resource = block.get("resource")
        valid = (isinstance(resource, dict) and isinstance(resource.get("uri"), str)
                 and (isinstance(resource.get("text"), str) or isinstance(resource.get("blob"), str)))
    else:
        valid = False
    if not valid:
        raise SafeError("Native content block is incompatible")


class Bridge:
    def __init__(self, config):
        self.config = config
        self.native = NativeTransport(config)
        self.initialized = False
        self.ready = False
        self.thread_id = None
        self.tools = {}
        self.failed = False

    def discover(self):
        if self.failed:
            raise SafeError("Native route failed; restart explicitly before another attempt")
        if self.tools:
            return
        try:
            self.native.rpc("initialize", {
                "clientInfo": {"name": "h-stack-native-apps", "version": "1.0.0"},
                "capabilities": {"experimentalApi": True}})
            self.native.send({"method": "initialized"})
            result = self.native.rpc("thread/start", {
                "ephemeral": True, "cwd": self.config["home"], "approvalPolicy": "untrusted"})
            thread = result.get("thread") if isinstance(result, dict) else None
            if not isinstance(thread, dict) or not isinstance(thread.get("id"), str) or not thread["id"]:
                raise SafeError("Native thread response is incompatible")
            self.thread_id = thread["id"]
            cursor = None
            seen = set()
            found = {}
            for _ in range(100):
                response = self.native.rpc("mcpServerStatus/list", {
                    "threadId": self.thread_id, "serverName": "codex_apps",
                    "detail": "toolsAndAuthOnly", "limit": 100, "cursor": cursor})
                if not isinstance(response, dict) or not isinstance(response.get("data"), list):
                    raise SafeError("Native tool-discovery response is incompatible")
                for server in response["data"]:
                    if not isinstance(server, dict):
                        raise SafeError("Invalid native server status")
                    if server.get("name") != "codex_apps":
                        continue
                    if server.get("toolsError") or not isinstance(server.get("tools"), dict):
                        raise SafeError("Native app tool discovery failed")
                    for original, tool in server["tools"].items():
                        if original in found:
                            raise SafeError("Duplicate native tool definition")
                        if not isinstance(tool, dict) or not isinstance(tool.get("inputSchema"), dict):
                            raise SafeError("Native tool definition is incompatible")
                        found[original] = tool
                cursor = response.get("nextCursor")
                if cursor is None:
                    break
                if not isinstance(cursor, str) or not cursor or cursor in seen:
                    raise SafeError("Invalid or repeated native discovery cursor")
                seen.add(cursor)
            else:
                raise SafeError("Native discovery page limit exceeded")
            for alias, original in self.config["allowed"].items():
                if original not in found:
                    raise SafeError("A configured tool is not available in the selected native account")
                # Preserve upstream JSON Schema and annotations. Metadata may
                # contain connector identities and is deliberately not published.
                source = found[original]
                for key in ("description", "title"):
                    if key in source and not isinstance(source[key], str):
                        raise SafeError("Native tool metadata is incompatible")
                for key in ("outputSchema", "annotations"):
                    if key in source and not isinstance(source[key], dict):
                        raise SafeError("Native tool schema is incompatible")
                public = {key: source[key] for key in (
                    "description", "inputSchema", "outputSchema", "annotations", "title"
                ) if key in source}
                public["name"] = alias
                self.tools[alias] = (original, public)
        except SafeError:
            self.failed = True
            self.tools = {}
            self.native.close()
            raise

    def dispatch(self, method, params):
        if method == "initialize":
            if self.initialized:
                raise SafeError("Already initialized")
            if not isinstance(params.get("protocolVersion"), str):
                raise SafeError("initialize requires protocolVersion")
            if not isinstance(params.get("capabilities"), dict) or not isinstance(params.get("clientInfo"), dict):
                raise SafeError("initialize requires client information and capabilities")
            if not all(isinstance(params["clientInfo"].get(key), str) and params["clientInfo"][key]
                       for key in ("name", "version")):
                raise SafeError("Client information requires name and version")
            self.initialized = True
            # Older clients must see the implemented version and decide whether
            # to continue; we do not emit newer schemas under an older version.
            return {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                    "serverInfo": {"name": "h-stack-native-apps", "version": "1.0.0"}}
        if method == "ping":
            return {}
        if not self.ready:
            raise SafeError("Complete initialize and notifications/initialized first")
        if method == "tools/list":
            if set(params) - {"cursor", "_meta"} or params.get("cursor") is not None:
                raise SafeError("This adapter does not accept client pagination")
            if "_meta" in params and not isinstance(params["_meta"], dict):
                raise SafeError("Request metadata must be an object")
            self.discover()
            return {"tools": [tool for _, tool in self.tools.values()]}
        if method == "tools/call":
            if set(params) - {"name", "arguments", "_meta"}:
                raise SafeError("Unsupported tool-call field")
            if "_meta" in params and not isinstance(params["_meta"], dict):
                raise SafeError("Request metadata must be an object")
            alias = params.get("name")
            if not isinstance(alias, str) or alias not in self.config["allowed"]:
                raise SafeError("Tool is not explicitly allowed")
            arguments = params.get("arguments", {})
            if not isinstance(arguments, dict):
                raise SafeError("Tool arguments must be an object")
            self.discover()
            try:
                result = self.native.rpc("mcpServer/tool/call", {
                    "threadId": self.thread_id, "server": "codex_apps",
                    "tool": self.tools[alias][0], "arguments": arguments})
                if not isinstance(result, dict) or not isinstance(result.get("content"), list):
                    raise SafeError("Native tool result is incompatible")
                if "isError" in result and type(result["isError"]) is not bool:
                    raise SafeError("Native tool result is incompatible")
                if result.get("isError") is True:
                    # Tool-level errors can echo credentials just like native
                    # RPC errors. Preserve failure without publishing their body.
                    # The session stays usable; no call is retried automatically.
                    return {"isError": True, "content": [{"type": "text", "text":
                        "Native app tool reported an error; inspect the native client privately"}]}
                if result.get("structuredContent") is not None and not isinstance(result["structuredContent"], dict):
                    raise SafeError("Native structured result is incompatible")
                for block in result["content"]:
                    check_content(block)
                return {key: result[key] for key in ("content", "structuredContent", "isError")
                        if key in result and result[key] is not None}
            except SafeError:
                # A timed-out call may already have acted. Never replay it or
                # silently start a replacement route on the next request.
                self.failed = True
                self.native.close()
                self.tools = {}
                raise
        raise SafeError("Unsupported MCP method")

    def message(self, request):
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            return {"jsonrpc": "2.0", "id": None,
                    "error": {"code": -32600, "message": "Invalid JSON-RPC request"}}
        request_id = request.get("id")
        valid_id = isinstance(request_id, str) or type(request_id) is int
        if "id" in request and not valid_id:
            return {"jsonrpc": "2.0", "id": None,
                    "error": {"code": -32600, "message": "Invalid request ID"}}
        method = request.get("method")
        params = request.get("params", {})
        if not isinstance(method, str) or not isinstance(params, dict):
            return None if "id" not in request else {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32600, "message": "Invalid request shape"}}
        if "id" not in request:
            if method == "notifications/initialized" and self.initialized:
                self.ready = True
            return None
        try:
            result = self.dispatch(method, params)
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except SafeError as error:
            code = -32601 if str(error) == "Unsupported MCP method" else -32000
            return {"jsonrpc": "2.0", "id": request_id,
                    "error": {"code": code, "message": str(error)}}

    def close(self):
        self.native.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Explicit bridge JSON configuration")
    parser.add_argument("--validate-only", action="store_true", help="Validate config without starting native Codex")
    args = parser.parse_args()
    bridge = None
    try:
        config = bridge_config(read_json(args.config))
        if args.validate_only:
            print(json.dumps({"valid": True, "allowedTools": len(config["allowed"])}))
            return 0
        bridge = Bridge(config)
        for signum in (signal.SIGTERM, signal.SIGINT):
            signal.signal(signum, lambda *_: sys.exit(0))
        for line in iter(lambda: sys.stdin.buffer.readline(MAX_BYTES + 1), b""):
            if len(line) > MAX_BYTES:
                raise SafeError("MCP message exceeds size limit")
            try:
                reply = bridge.message(parse_json(line))
            except SafeError:
                reply = {"jsonrpc": "2.0", "id": None,
                         "error": {"code": -32700, "message": "Invalid JSON"}}
            if reply is not None:
                encoded = json.dumps(reply, allow_nan=False)
                if len(encoded.encode()) > MAX_BYTES:
                    raise SafeError("MCP response exceeds size limit")
                print(encoded, flush=True)
        return 0
    except (SafeError, OSError, ValueError, RecursionError) as error:
        message = str(error) if isinstance(error, SafeError) else "Adapter failed; inspect the native client privately"
        print(message, file=sys.stderr)
        return 1
    finally:
        if bridge:
            bridge.close()


if __name__ == "__main__":
    sys.exit(main())
