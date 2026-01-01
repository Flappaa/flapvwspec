from __future__ import annotations
import sys
from typing import Optional


def main() -> None:
    # Import and delegate to the CLI main
    try:
        # prefer package-local CLI if available
        from vlinker import vlinker_cli as _cli
    except Exception:
        try:
            import vlinker_cli as _cli
        except Exception as e:
            print('Failed to import CLI module:', e)
            sys.exit(2)
    _cli.main()


def profile_interactive_main() -> None:
    # Run the interactive profile builder; prompt for path if omitted
    try:
        from vlinker.profile_builder import interactive_build
    except Exception as e:
        print('Failed to import profile builder:', e)
        sys.exit(2)
    cap = None
    if len(sys.argv) > 1:
        cap = sys.argv[1]
    else:
        cap = input('Path to capture file (or Enter to cancel): ').strip()
        if not cap:
            print('No capture provided; aborting')
            return
    interactive_build(cap)
