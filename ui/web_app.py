"""
Lightweight zero-dependency Web Application server using Python built-in http.server.
Provides an interactive graphical web interface to test natural language queries
and manage/create custom database tables.
"""

import sys
import os
import json
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
try:
    from http.server import ThreadingHTTPServer
    BaseServerClass = ThreadingHTTPServer
except ImportError:
    BaseServerClass = HTTPServer

class DualStackServer(BaseServerClass):
    """
    HTTP server that binds to both IPv4 and IPv6 dual-stack.
    Prevents 'localhost refused to connect' (ERR_CONNECTION_REFUSED) on Windows
    when browsers resolve 'localhost' to IPv6 ::1 instead of 127.0.0.1.
    """
    address_family = socket.AF_INET6

    def server_bind(self):
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()

ServerClass = DualStackServer

# Add root directory to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from nlp_engine import parse_query
from executor import execute_query
from database.table_manager import (
    get_all_tables_info,
    create_table,
    import_csv_data,
    insert_single_row,
    delete_table,
    delete_row,
    update_row,
    get_table_data
)
from database.seed_data import init_database

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "templates",
    "index.html"
)

class NLPSQLRequestHandler(BaseHTTPRequestHandler):
    def send_json(self, data, status_code=200):
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            try:
                with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
                    content = f.read().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error loading template: {str(e)}".encode("utf-8"))

        elif self.path == "/api/tables":
            tables = get_all_tables_info()
            self.send_json({"success": True, "tables": tables})

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if self.path == "/api/query":
            question = data.get("question", "")

            # 1. Run NLP pipeline
            nlp_result = parse_query(question)
            response_data = dict(nlp_result)

            # 2. If valid SQL generated, execute it
            if nlp_result["status"] == "success":
                exec_result = execute_query(nlp_result["sql"], nlp_result["params"])
                response_data["execution"] = exec_result

            self.send_json(response_data)

        elif self.path == "/api/tables/create":
            table_name = data.get("table_name", "")
            columns = data.get("columns", [])
            initial_rows = data.get("initial_rows", [])
            ok, msg = create_table(table_name, columns, initial_rows=initial_rows)
            self.send_json({"success": ok, "message": msg})

        elif self.path == "/api/tables/csv":
            table_name = data.get("table_name", "")
            csv_data = data.get("csv_data", "")
            ok, msg = import_csv_data(table_name, csv_data)
            self.send_json({"success": ok, "message": msg})

        elif self.path == "/api/tables/insert":
            table_name = data.get("table_name", "")
            row = data.get("row", {})
            ok, msg = insert_single_row(table_name, row)
            self.send_json({"success": ok, "message": msg})

        elif self.path == "/api/tables/delete":
            table_name = data.get("table_name", "")
            ok, msg = delete_table(table_name)
            self.send_json({"success": ok, "message": msg})

        elif self.path == "/api/tables/row/delete":
            table_name = data.get("table_name", "")
            row_id = data.get("row_id")
            ok, msg = delete_row(table_name, row_id)
            self.send_json({"success": ok, "message": msg})

        elif self.path == "/api/tables/row/update":
            table_name = data.get("table_name", "")
            row_id = data.get("row_id")
            updated_data = data.get("data") or data.get("updated_data") or {}
            ok, msg = update_row(table_name, row_id, updated_data)
            self.send_json({"success": ok, "message": msg})

        elif self.path == "/api/tables/data":
            table_name = data.get("table_name", "")
            res = get_table_data(table_name)
            self.send_json(res)

        elif self.path == "/api/schema/reset":
            try:
                init_database()
                self.send_json({"success": True, "message": "Database reset and re-seeded with 10 students and 10 courses with fees."})
            except Exception as e:
                self.send_json({"success": False, "message": str(e)}, status_code=500)

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def log_message(self, format, *args):
        return

def start_server(port=8000):
    try:
        httpd = DualStackServer(("", port), NLPSQLRequestHandler)
    except Exception:
        httpd = BaseServerClass(("0.0.0.0", port), NLPSQLRequestHandler)

    try:
        print("=" * 70)
        print(" DMAI Project Web UI is running!")
        print(f" Local URL:    http://127.0.0.1:{port}")
        print(f" Browser URL:  http://localhost:{port}")
        print(" Open the link above in your browser to interact with the system.")
        print(" Press Ctrl+C in terminal to stop.")
        print("=" * 70)
        httpd.serve_forever()
    except OSError as e:
        if port < 8010:
            start_server(port + 1)
        else:
            print(f"Error starting server: {e}")

if __name__ == "__main__":
    start_server()
