#!/usr/bin/env python3
"""Check the configured native bridge handshake/discovery without calling apps."""

import argparse
import importlib.util
import json
from pathlib import Path
import sys

from provider_tools import SafeError, bridge_config, read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Explicit bridge JSON configuration")
    parser.add_argument("--validate-only", action="store_true", help="No native process or app discovery")
    args = parser.parse_args()
    bridge = None
    try:
        config = bridge_config(read_json(args.config))
        if args.validate_only:
            print(json.dumps({"valid": True, "nativeStarted": False}))
            return 0
        spec = importlib.util.spec_from_file_location("native_apps_bridge", Path(__file__).with_name("codex-apps-bridge.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        bridge = module.Bridge(config)
        result = bridge.message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "h-stack-discovery-check", "version": "1"}}})
        if "result" not in result:
            raise SafeError("Bridge initialization failed")
        bridge.message({"jsonrpc": "2.0", "method": "notifications/initialized"})
        result = bridge.message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        if "result" not in result:
            raise SafeError("Bridge discovery failed; inspect the native client privately")
        print(json.dumps({"initialized": True, "tools": len(result["result"]["tools"]),
                          "executedTools": 0, "inferenceTurns": 0,
                          "authenticatedAppReadVerified": False}))
        return 0
    except (SafeError, OSError, ValueError):
        print("Bridge check failed; inspect the selected route privately", file=sys.stderr)
        return 1
    finally:
        if bridge:
            bridge.close()


if __name__ == "__main__":
    sys.exit(main())
