#!/usr/bin/env python3
"""
FATGen — Factory Acceptance Test Document Generator
Entry point.

Usage:
    python main.py --web [--port 5000] [--host 0.0.0.0]
    python main.py --desktop
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="FATGen — FAT Document Generator"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--web", action="store_true", default=True,
                       help="Launch browser-based UI (default)")
    group.add_argument("--desktop", action="store_true",
                       help="Launch Tkinter desktop UI")
    parser.add_argument("--port", type=int, default=5000,
                        help="Web server port (default: 5000)")
    parser.add_argument("--host", default="0.0.0.0",
                        help="Web server host (default: 0.0.0.0)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable Flask debug mode")
    args = parser.parse_args()

    if args.desktop:
        from fatgen.app.ui.desktop.main_window import run
        run()
    else:
        from fatgen.app.ui.web.routes import app
        print(f"Starting FATGen web UI on http://{args.host}:{args.port}")
        print("Press Ctrl+C to stop.")
        app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
