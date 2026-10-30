"""
Main Entry Point for DMAI NLP-to-Database Project.
Supports:
  python main.py             -> Interactive CLI mode
  python main.py --web       -> Web browser GUI mode (http://localhost:8000)
  python main.py --demo      -> Runs automated flowchart demo
  python main.py --seed      -> Re-seeds the SQLite student database
  python main.py -q "query"  -> Directly runs a single query
"""

import sys
import os
import argparse

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.seed_data import init_database
from nlp_engine import parse_query
from executor import execute_query
from ui.cli import interactive_loop, run_pipeline
from ui.web_app import start_server
from demo import run_demo

def main():
    parser = argparse.ArgumentParser(
        description="DMAI Project: NLP for Database Interaction (Text-to-SQL)"
    )
    parser.add_argument("--web", "-w", action="store_true", help="Launch the Web Browser GUI")
    parser.add_argument("--demo", "-d", action="store_true", help="Run the automated demonstration suite")
    parser.add_argument("--seed", "-s", action="store_true", help="Reinitialize and seed the SQLite database")
    parser.add_argument("--query", "-q", type=str, help="Execute a single natural language question directly")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Port for the Web GUI server (default 8000)")

    args = parser.parse_args()

    # Ensure database exists before running
    db_path = os.path.join(PROJECT_ROOT, "database", "students.db")
    if not os.path.exists(db_path) or args.seed:
        print("[*] Initializing student database...")
        init_database()
        if args.seed and not (args.web or args.demo or args.query):
            return

    if args.web:
        start_server(port=args.port)
    elif args.demo:
        run_demo()
    elif args.query:
        run_pipeline(args.query)
    else:
        # Default to interactive CLI
        interactive_loop()

if __name__ == "__main__":
    main()
