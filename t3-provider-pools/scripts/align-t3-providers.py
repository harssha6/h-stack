#!/usr/bin/env python3
"""Validate selected provider-home updates and optionally write a NEW candidate.

Never edits the selected settings file, creates an account, or copies a login.
"""

import argparse
import json
from pathlib import Path
import sys

from provider_tools import SafeError, alignment_candidate, read_json, write_candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", required=True, help="Explicit existing settings JSON to read")
    parser.add_argument("--spec", required=True, help="Explicit versioned updates JSON")
    parser.add_argument("--output", help="Write new candidate file with mode 0600; refuses existing paths")
    args = parser.parse_args()
    try:
        settings = read_json(args.settings)
        spec = read_json(args.spec)
        candidate = alignment_candidate(settings, spec)
        if args.output:
            if Path(args.output).resolve() == Path(args.settings).resolve():
                raise SafeError("Candidate must not be the source settings path")
            write_candidate(candidate, args.output)
        # Never print a whole settings document, account identifiers or paths.
        print(json.dumps({"valid": True, "changed": candidate != settings,
                          "updatedInstances": len(spec["updates"]),
                          "candidateWritten": bool(args.output), "liveSettingsChanged": False}))
        return 0
    except (SafeError, OSError, ValueError, RecursionError, RuntimeError) as error:
        message = str(error) if isinstance(error, SafeError) else "Candidate validation failed"
        print(message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
