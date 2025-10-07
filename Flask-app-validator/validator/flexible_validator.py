import os
import sys
import re
import subprocess
import time
import json
import sqlite3
import threading
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None  # route & runtime testing requires requests

# Optional offline syntax checking
try:
    import flake8.api.legacy as flake8
except ImportError:
    flake8 = None


class FlexibleFlaskValidator:
    """
    Enhanced Flask project validator:
    - discovers Flask files & main app
    - starts student's app in a subprocess (headless)
    - discovers endpoints (static + dynamic)
    - inspects SQLite databases (if present)
    - attempts CRUD-style operations on discovered endpoints
    - logs everything in a text log and JSON summary
    """

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 5000
    STARTUP_TIMEOUT = 12      # seconds to wait for app to become reachable
    REQUEST_TIMEOUT = 4       # seconds for individual HTTP requests
    PROCESS_TERMINATE_TIMEOUT = 3  # seconds to wait after terminate()

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name if self.project_path.name else "project"
        self.logs_path = Path("Logs") / self.project_name
        self.logs_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.logs_path / f"validation_{timestamp}.log"
        self.json_file = self.logs_path / f"validation_{timestamp}.json"

        self.errors = []
        self.warnings = []
        self.checks_passed = 0
        self.total_checks = 0
        self.validation_results = []  # list of check dicts
        self.flask_files = []
        self.template_files = []
        self.main_app_file = None

        # runtime process bookkeeping
        self.proc = None
        self._stdout_thread = None
        self._stderr_thread = None
        self._stop_reader = threading.Event()

        # structured run log
        self.run_log = {
            "project": str(self.project_path),
            "project_name": self.project_name,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "events": [],      # chronological events
            "endpoints": [],
            "db_inspection": {},
            "crud_results": [],
            "summary": {}
        }

        # Logging file pointer
        self.log_fp = open(self.log_file, "w", encoding="utf-8")


    def auto_install_dependencies(self):
        """
        Automatically install dependencies from requirements.txt if found.
        Otherwise, attempt to install commonly used Flask packages referenced in the code.
        """
        req_files = list(self.project_path.glob("requirements*.txt"))
        if req_files:
            req_file = req_files[0]
            self.log(f"Installing dependencies from {req_file}...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                    stdout=sys.stdout, stderr=sys.stderr
                )
                self.log("Dependencies installed successfully.")
                self.add_check("Dependencies installation", True, 5, f"Installed from {req_file.name}")
                return
            except subprocess.CalledProcessError as e:
                self.log(f"Failed to install dependencies from {req_file}: {e}", level="WARN")
                self.add_check("Dependencies installation", False, 0, "Failed to install requirements.txt")

        # No requirements file: try to infer needed Flask packages
        common_pkgs = {
            "flask_sqlalchemy": "flask_sqlalchemy",
            "flask_wtf": "flask_wtf",
            "flask_login": "flask_login",
            "flask_bcrypt": "flask_bcrypt",
            "flask_mail": "flask_mail",
        }

        found = set()
        for py_file in self.project_path.glob("**/*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    for key in common_pkgs:
                        if key in content:
                            found.add(common_pkgs[key])
            except Exception:
                continue

        if found:
            self.log(f"Auto-installing detected Flask packages: {', '.join(found)}")
            for pkg in found:
                try:
                    subprocess.check_call(
                        [sys.executable, "-m", "pip", "install", pkg],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    self.log(f"Installed package: {pkg}")
                except Exception as e:
                    self.log(f"Failed to install package {pkg}: {e}", level="WARN")
        else:
            self.log("No dependencies or recognizable Flask packages to install.", level="INFO")

    # -------------------- Logging helpers --------------------
    def _timestamp(self):
        return datetime.utcnow().isoformat() + "Z"

    def log(self, message, level="INFO"):
        ts = self._timestamp()
        line = f"[{ts}] [{level}] {message}"
        # print to stdout for visibility and write to file
        print(line)
        self.log_fp.write(line + "\n")
        self.log_fp.flush()
        # add to structured run log
        self.run_log["events"].append({"timestamp": ts, "level": level, "message": message})

    def add_check(self, check_name, passed, points=0, message=""):
        """Record a validation check result"""
        self.total_checks += 1
        status = "PASS" if passed else "FAIL"
        if passed:
            self.checks_passed += 1
        entry = {
            "name": check_name,
            "passed": bool(passed),
            "status": status,
            "points": points,
            "message": message
        }
        self.validation_results.append(entry)
        self.log(f"{status}: {check_name} - {message}", level="CHECK")

    # -------------------- File discovery --------------------
    def find_flask_files(self):
        self.log("Scanning for Python files containing Flask imports...")
        python_files = list(self.project_path.glob("**/*.py"))
        flask_files = []
        for file in python_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "Flask" in content or "from flask import" in content:
                        flask_files.append(file)
            except Exception as e:
                self.log(f"Could not read {file}: {e}", level="WARN")
                continue
        self.flask_files = flask_files
        self.log(f"Found {len(flask_files)} Flask-related Python file(s).")
        return flask_files

    def find_template_files(self):
        html_files = list(self.project_path.glob("**/*.html"))
        self.template_files = html_files
        self.log(f"Found {len(html_files)} HTML template file(s).")
        return html_files

    def find_main_app_file(self):
        self.log("Locating main Flask application file...")
        candidates = []
        for file in self.flask_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
                if re.search(r"\bapp\s*=\s*Flask\(", content) or "app.run(" in content:
                    candidates.append(file)
            except Exception:
                continue

        # prioritize common filenames
        priority_names = ["app.py", "main.py", "server.py", "run.py"]
        for name in priority_names:
            for file in candidates:
                if file.name == name:
                    self.main_app_file = file
                    self.log(f"Selected main app file: {file}")
                    return file

        if candidates:
            self.main_app_file = candidates[0]
            self.log(f"Selected main app file (fallback): {candidates[0]}")
            return candidates[0]

        self.log("No main Flask app file detected by heuristics.", level="WARN")
        return None

    # -------------------- Static analysis helpers --------------------
    def discover_endpoints_static(self):
        """Parse route decorators from Python files (static analysis)."""
        endpoints = set()
        pattern = re.compile(r"@app\.route\(\s*['\"]([^'\"]+)['\"]")
        for file in self.flask_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
                    for m in pattern.findall(content):
                        endpoints.add(m)
            except Exception as e:
                self.log(f"Failed parsing {file}: {e}", level="WARN")
        self.log(f"Statically discovered endpoints: {sorted(endpoints)}")
        return sorted(endpoints)

    # -------------------- Process management & stream capture --------------------
    def _reader_thread(self, stream, prefix):
        """Continuously read from a stream and write to log until stopped."""
        try:
            while not self._stop_reader.is_set():
                line = stream.readline()
                if not line:
                    break
                try:
                    decoded = line.decode(errors="replace").rstrip()
                except Exception:
                    decoded = str(line).rstrip()
                self.log(f"{prefix}: {decoded}", level="APP")
        except Exception as e:
            self.log(f"Reader thread stopped with error: {e}", level="WARN")

    def _start_app_subprocess(self):
        """
        Start the student's Flask app in a subprocess.
        Uses the parent folder (project_path) as cwd. Expects main_app_file to be set.
        Returns True if process started.
        """
        if not self.main_app_file:
            self.log("No main app file to run.", level="ERROR")
            return False

        cmd = [sys.executable, str(self.main_app_file)]
        self.log(f"Starting student's app subprocess: {' '.join(cmd)} (cwd={self.project_path})")
        try:
            self.proc = subprocess.Popen(
                cmd,
                cwd=str(self.project_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1
            )
        except Exception as e:
            self.log(f"Failed to start subprocess: {e}", level="ERROR")
            self.proc = None
            return False

        # start threads to capture stdout/stderr without blocking
        self._stop_reader.clear()
        self._stdout_thread = threading.Thread(target=self._reader_thread, args=(self.proc.stdout, "STDOUT"), daemon=True)
        self._stderr_thread = threading.Thread(target=self._reader_thread, args=(self.proc.stderr, "STDERR"), daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()
        return True

    def _stop_app_subprocess(self):
        """Terminate the subprocess and stop reader threads."""
        if not self.proc:
            return
        self.log("Stopping student's app subprocess...")
        try:
            self.proc.terminate()
            # wait for graceful shutdown
            try:
                self.proc.wait(timeout=self.PROCESS_TERMINATE_TIMEOUT)
            except subprocess.TimeoutExpired:
                self.log("Subprocess did not exit after terminate(); killing.", level="WARN")
                self.proc.kill()
        except Exception as e:
            self.log(f"Error terminating subprocess: {e}", level="WARN")
        finally:
            self._stop_reader.set()
            # Allow threads to finish
            if self._stdout_thread:
                self._stdout_thread.join(timeout=1)
            if self._stderr_thread:
                self._stderr_thread.join(timeout=1)
            self.proc = None

    # -------------------- Runtime checks --------------------
    def wait_for_app(self, host=None, port=None, timeout=None):
        """Wait until the app responds on host:port or timeout. Returns True if reachable."""
        if not requests:
            self.log("requests not installed; cannot perform runtime HTTP checks.", level="WARN")
            return False

        host = host or self.DEFAULT_HOST
        port = port or self.DEFAULT_PORT
        timeout = timeout or self.STARTUP_TIMEOUT

        base_url = f"http://{host}:{port}"
        self.log(f"Waiting for app to become reachable at {base_url} (timeout {timeout}s)...")
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = requests.get(base_url, timeout=self.REQUEST_TIMEOUT)
                self.log(f"App responded to GET {base_url} with status {r.status_code}", level="APP")
                return True
            except Exception:
                time.sleep(0.5)
                # also check if subprocess ended unexpectedly
                if self.proc and self.proc.poll() is not None:
                    self.log("Subprocess exited while waiting for app to start.", level="ERROR")
                    return False
                continue
        self.log(f"App did not become reachable within {timeout} seconds.", level="ERROR")
        return False

    def discover_endpoints_dynamic(self, host=None, port=None):
        """Try to hit a few known places to discover endpoints dynamically."""
        if not requests:
            self.log("requests not installed; skipping dynamic discovery.", level="WARN")
            return []

        host = host or self.DEFAULT_HOST
        port = port or self.DEFAULT_PORT
        base_url = f"http://{host}:{port}"
        discovered = set()

        # Try root to capture links (if any)
        try:
            r = requests.get(base_url, timeout=self.REQUEST_TIMEOUT)
            if r.status_code == 200 and r.text:
                # find hrefs that look like app routes
                for href in re.findall(r'href=["\'](/[^"\']+)["\']', r.text):
                    discovered.add(href)
        except Exception as e:
            self.log(f"Could not GET {base_url}: {e}", level="DEBUG")

        # if there's a /routes or /_routes endpoint (student might expose), try them
        for probe in ["/routes", "/_routes", "/_all_routes"]:
            try:
                r = requests.get(base_url + probe, timeout=self.REQUEST_TIMEOUT)
                if r.status_code == 200:
                    # attempt to parse JSON or text lines
                    try:
                        data = r.json()
                        if isinstance(data, (list, dict)):
                            # flatten list or dict values
                            if isinstance(data, list):
                                discovered.update([str(x) for x in data])
                            else:
                                discovered.update([str(k) for k in data.keys()])
                    except Exception:
                        # fallback to regex parsing
                        for m in re.findall(r'(/[\w/\-_]+)', r.text):
                            discovered.add(m)
            except Exception:
                continue

        discovered_list = sorted(discovered)
        self.log(f"Dynamically discovered endpoints: {discovered_list}")
        return discovered_list

    # -------------------- Database inspection --------------------
    def find_sqlite_databases(self):
        """Locate .db / .sqlite files inside project path. Returns list of Path."""
        db_candidates = list(self.project_path.glob("**/*.db")) + list(self.project_path.glob("**/*.sqlite")) + list(self.project_path.glob("**/*.sqlite3"))
        # common Flask instance path
        instance_db = self.project_path / "instance" / "app.db"
        if instance_db.exists():
            db_candidates.insert(0, instance_db)
        self.log(f"Database files found: {[str(p) for p in db_candidates]}")
        return db_candidates

    def inspect_sqlite_db(self, db_path: Path):
        """Return schema info for a sqlite DB path."""
        info = {"path": str(db_path), "tables": {}}
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cur.fetchall()]
            for tbl in tables:
                cur.execute(f"PRAGMA table_info('{tbl}');")
                cols = [{"cid": r[0], "name": r[1], "type": r[2], "notnull": r[3], "dflt_value": r[4], "pk": r[5]} for r in cur.fetchall()]
                info["tables"][tbl] = cols
            conn.close()
            self.log(f"Inspected DB {db_path}: tables={list(info['tables'].keys())}")
        except Exception as e:
            self.log(f"Error inspecting DB {db_path}: {e}", level="WARN")
        return info

    # -------------------- CRUD testing --------------------
    def _normalize_endpoint(self, ep):
        """Ensure endpoint begins with / and doesn't include host/port."""
        if not ep:
            return "/"
        if ep.startswith("http://") or ep.startswith("https://"):
            m = re.search(r'https?://[^/]+(/.*)', ep)
            if m:
                ep = m.group(1)
            else:
                ep = "/"
        if not ep.startswith("/"):
            ep = "/" + ep
        return ep

    def generate_test_payload(self, table_name=None, endpoint_name=None):
        """
        Generate a context-aware test payload.
        Uses DB schema if available, otherwise uses intelligent defaults.
        Also adjusts payloads based on endpoint name patterns (register, login, etc.)
        """
        base = {
            "username": "test_user",
            "email": "test_user@example.com",
            "password": "P@ssw0rd!",
            "name": "Test Name",
            "title": "Test Title",
            "content": "Sample content",
            "description": "Test record",
            "id": 1,
        }

        # Adjust for common endpoint types
        if endpoint_name:
            ep = endpoint_name.lower()
            if "register" in ep or "signup" in ep:
                base["confirm_password"] = base["password"]
            if "login" in ep:
                base = {"email": base["email"], "password": base["password"]}
            if "user" in ep:
                base["role"] = "student"
            if "post" in ep or "blog" in ep:
                base["title"] = "Sample Post"
                base["content"] = "This is test content for validation."
            if "feedback" in ep or "comment" in ep:
                base["message"] = "This is an automated test message."

        # Try to enrich payload with DB schema if available
        db_info = self.run_log.get("db_inspection", [])
        if db_info and table_name:
            for db in db_info:
                tables = db.get("tables", {})
                if table_name in tables:
                    for col in tables[table_name]:
                        cname = col["name"].lower()
                        ctype = (col["type"] or "").lower()
                        if "email" in cname:
                            base[col["name"]] = base["email"]
                        elif "user" in cname:
                            base[col["name"]] = base["username"]
                        elif "pass" in cname:
                            base[col["name"]] = base["password"]
                        elif "title" in cname:
                            base[col["name"]] = base["title"]
                        elif "content" in cname or "text" in cname:
                            base[col["name"]] = base["content"]
                        elif "created" in cname or "date" in cname:
                            base[col["name"]] = "2025-10-07"
                        elif "id" in cname:
                            base[col["name"]] = 1
        return base

    def perform_crud_tests(self, endpoints, host=None, port=None):
        results = []
        if not requests:
            self.log("requests not installed; skipping CRUD tests.", level="WARN")
            return results

        host = host or self.DEFAULT_HOST
        port = port or self.DEFAULT_PORT
        base_url = f"http://{host}:{port}"
        session = requests.Session()

        for ep in endpoints:
            ep_norm = self._normalize_endpoint(ep)
            url = base_url + ep_norm
            action = "UNKNOWN"
            try:
                # generate context-aware payload
                payload = self.generate_test_payload(endpoint_name=ep_norm)

                # classify by keywords
                lower = ep_norm.lower()
                if any(k in lower for k in ["/create", "/add", "/register", "/new"]):
                    action = "CREATE"
                    r = session.post(url, data=payload, timeout=self.REQUEST_TIMEOUT, allow_redirects=True)
                elif any(k in lower for k in ["/update", "/edit", "/modify"]):
                    action = "UPDATE"
                    r = session.post(url, data=payload, timeout=self.REQUEST_TIMEOUT, allow_redirects=True)
                elif any(k in lower for k in ["/delete", "/remove"]):
                    action = "DELETE"
                    r = session.post(url, data={"id": payload.get("id", 1)}, timeout=self.REQUEST_TIMEOUT, allow_redirects=True)
                else:
                    action = "READ"
                    r = session.get(url, timeout=self.REQUEST_TIMEOUT)

                status = getattr(r, "status_code", None)
                ok = status in (200, 201, 302)
                msg = f"{action} {url} -> {status}"
                self.log(msg, level="HTTP")

                result = {
                    "endpoint": ep_norm,
                    "url": url,
                    "action": action,
                    "status_code": status,
                    "ok": bool(ok),
                    "payload": payload,  # store payload used
                    "response_snippet": (r.text[:400] if hasattr(r, "text") else "")
                }
                results.append(result)
                self.add_check(f"{action} test for {ep_norm}", ok, points=5, message=f"HTTP {status}")
                self.run_log["crud_results"].append(result)

            except Exception as e:
                self.log(f"Error during CRUD test for {url}: {e}", level="ERROR")
                results.append({
                    "endpoint": ep_norm,
                    "url": url,
                    "action": action,
                    "ok": False,
                    "error": str(e)
                })
        return results

    # -------------------- Syntax checks --------------------
    def validate_syntax(self):
        """Offline syntax and code completeness check with flake8 (optional)."""
        if not flake8:
            self.log("flake8 not installed; skipping syntax checks", level="INFO")
            return
        self.log("Running flake8 syntax checks...")
        try:
            style_guide = flake8.get_style_guide(ignore=['E501', 'W293', 'E302', 'E305', 'F401', 'F841', 'W292', 'E226', 'W291'])
            report = style_guide.check_files([str(f) for f in self.flask_files])
            total = getattr(report, "total_errors", None)
            if total == 0:
                self.add_check("Syntax check (flake8)", True, points=0, message="No critical syntax errors found")
            else:
                self.add_check("Syntax check (flake8)", True, points=0, message=f"Non-critical syntax issues: {total} (ignored)")
        except Exception as e:
            self.log(f"flake8 check failed: {e}", level="WARN")

    # -------------------- High-level run --------------------
    def run_validation(self, host=None, port=None):
        """
        Run the full validation pipeline and return True/False.
        The method orchestrates static checks, runtime app start, discovery,
        DB inspection, CRUD tests, and final summary.
        """
        host = host or self.DEFAULT_HOST
        port = port or self.DEFAULT_PORT

        self.log("Starting Flexible Flask Application Validation")
        self.log("=" * 60)

        # Static checks
        self.validate_project_structure()
        self.validate_flask_imports()
        self.validate_database_imports()
        self.validate_routes()
        self.validate_authentication_flow()
        self.validate_template_usage()
        self.validate_functionality()
        self.validate_syntax()

        # Runtime: start app
        main_file = self.main_app_file
        if not main_file:
            self.add_check("Runtime: main app file present", False, 0, "No main app file found")
            # finalize and return
            self._finalize_run()
            return False

        self.auto_install_dependencies()
        started = self._start_app_subprocess()
        if not started:
            self.add_check("Runtime: start subprocess", False, 0, "Failed to start subprocess")
            self._finalize_run()
            return False

        try:
            reachable = self.wait_for_app(host=host, port=port, timeout=self.STARTUP_TIMEOUT)
            if not reachable:
                self.add_check("Runtime: app reachable", False, 0, "App did not respond in time")
                self.errors.append("Flask app did not start or crashed at runtime")
                # collect final logs and stop subprocess
                self._finalize_run()
                return False
            else:
                self.add_check("Runtime: app reachable", True, 10, "App responded on host:port")
        except Exception as e:
            self.add_check("Runtime: app reachable", False, 0, f"Error while waiting for app: {e}")
            self._finalize_run()
            return False

        # Discovery - static + dynamic
        static_eps = self.discover_endpoints_static()
        dynamic_eps = self.discover_endpoints_dynamic(host=host, port=port)
        # merge and deduplicate, prefer static ordering then dynamic
        endpoints = []
        for e in static_eps + dynamic_eps:
            norm = self._normalize_endpoint(e)
            if norm not in endpoints:
                endpoints.append(norm)
        # Always ensure root is present
        if "/" not in endpoints:
            endpoints.insert(0, "/")

        self.run_log["endpoints"] = endpoints
        self.log(f"Final endpoint list for testing: {endpoints}")

        # DB inspection
        db_candidates = self.find_sqlite_databases()
        db_inspections = []
        for db_path in db_candidates:
            try:
                info = self.inspect_sqlite_db(db_path)
                db_inspections.append(info)
            except Exception as e:
                self.log(f"DB inspection error for {db_path}: {e}", level="WARN")
        self.run_log["db_inspection"] = db_inspections

        # CRUD tests
        crud_results = self.perform_crud_tests(endpoints, host=host, port=port)
        self.run_log["crud_results"] = crud_results

        # finalize (stop app, write logs)
        self._finalize_run()
        return not bool(self.errors)

    # -------------------- Validation units (from earlier) --------------------
    def validate_project_structure(self):
        self.log("Validating project structure...")
        flask_files = self.find_flask_files()
        if flask_files:
            self.add_check("Flask files found", True, 15, f"Found {len(flask_files)} Flask Python file(s)")
        else:
            self.add_check("Flask files found", False, 0, "No Flask files found")
            self.errors.append("No Flask files found")
            return

        main_file = self.find_main_app_file()
        if main_file:
            self.add_check("Main app file", True, 10, f"Main Flask app: {main_file.name}")
        else:
            self.add_check("Main app file", False, 0, "No main Flask app file found")
            self.errors.append("No main Flask app file found")
            return

        req_files = list(self.project_path.glob("requirements*.txt")) + list(self.project_path.glob("dependencies*.txt"))
        if req_files:
            self.add_check("Dependencies file", True, 5, f"Found: {req_files[0].name}")
        else:
            self.add_check("Dependencies file", False, 0, "No dependencies file found")
            self.warnings.append("No requirements.txt or dependencies file found")

        template_files = self.find_template_files()
        if template_files:
            self.add_check("Template files", True, 10, f"Found {len(template_files)} HTML templates")
        else:
            self.add_check("Template files", False, 0, "No HTML template files found")
            self.warnings.append("No HTML templates found")

    def validate_flask_imports(self):
        self.log("Validating Flask imports in main app file...")
        if not self.main_app_file:
            self.add_check("Main app exists", False, 0, "No main app file")
            return
        with open(self.main_app_file, "r", encoding="utf-8") as f:
            content = f.read()
        checks = [
            ("from flask import", 8, "Flask core imports"),
            ("Flask(", 5, "Flask app creation"),
            ("render_template", 5, "Template rendering"),
            ("request", 3, "Request handling"),
            ("redirect", 3, "Redirect functionality"),
        ]
        for substr, pts, desc in checks:
            self.add_check(f"Import: {substr}", substr in content, pts, desc)

    def validate_database_imports(self):
        self.log("Validating database imports...")
        if not self.main_app_file:
            self.add_check("Main app exists", False, 0, "No main app file")
            return
        with open(self.main_app_file, "r", encoding="utf-8") as f:
            content = f.read()
        db_checks = [
            ("from flask_sqlalchemy import", 5, "SQLAlchemy ORM"),
            ("from werkzeug.security import", 5, "Password security"),
            ("generate_password_hash", 3, "Password hashing"),
            ("check_password_hash", 3, "Password verification"),
        ]
        for substr, pts, desc in db_checks:
            self.add_check(f"Database: {substr}", substr in content, pts, desc)

    def validate_routes(self):
        self.log("Validating route definitions statically...")
        if not self.main_app_file:
            self.add_check("Main app exists", False, 0, "No main app file")
            return
        with open(self.main_app_file, "r", encoding="utf-8") as f:
            content = f.read()
        route_patterns = [
            (r"@app\.route\([\'\"][/\w\-\_]*[\'\"]", "Route decorators", 10),
            (r"def\s+\w+\s*\(.*\):", "Route functions", 5),
            (r"return\s+render_template", "Template rendering", 5),
            (r"return\s+redirect", "Redirects", 3),
        ]
        for pattern, desc, pts in route_patterns:
            matches = re.findall(pattern, content)
            self.add_check(f"Routes: {desc}", bool(matches), pts, f"Found {len(matches)} {desc.lower()}" if matches else f"Missing {desc.lower()}")

    def validate_authentication_flow(self):
        self.log("Validating authentication-related code statically...")
        if not self.main_app_file:
            self.add_check("Main app exists", False, 0, "No main app file")
            return
        with open(self.main_app_file, "r", encoding="utf-8") as f:
            content = f.read()
        auth_patterns = [
            ("session[", "Session management", 8),
            ("request.method", "HTTP method handling", 5),
            ("request.form[", "Form data access", 5),
            ("flash(", "Flash messages", 3),
            ("SECRET_KEY", "Secret key", 5),
        ]
        for pattern, desc, pts in auth_patterns:
            self.add_check(f"Auth: {desc}", pattern in content, pts, desc if pattern in content else f"Missing {desc}")

    def validate_template_usage(self):
        self.log("Validating template usage (render_template references)...")
        referenced_templates = set()
        for file in self.flask_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    matches = re.findall(r"render_template\(['\"](.*?)['\"]", f.read())
                    referenced_templates.update(matches)
            except Exception:
                continue
        existing_templates = {t.name for t in self.template_files}
        missing = [t for t in referenced_templates if t not in existing_templates]
        if missing:
            self.add_check("Template reference check", False, 0, f"Missing templates: {', '.join(missing)}")
            self.errors.extend([f"Referenced template not found: {t}" for t in missing])
        else:
            self.add_check("Template reference check", True, 5, "All referenced templates exist")

    def validate_functionality(self):
        self.log("Basic functionality checks...")
        if not self.main_app_file:
            self.add_check("Main app exists", False, 0, "No main app file")
            return
        with open(self.main_app_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.add_check("App execution method", "app.run(" in content, 5, "app.run() found" if "app.run(" in content else "No app.run() found")
        self.add_check("Database initialization", "db.create_all()" in content or "create_all()" in content, 5, "DB initialization found" if "db.create_all()" in content else "No DB initialization found")

    # -------------------- Finalization --------------------
    def _finalize_run(self):
        """Write JSON summary, stop subprocess, close files, update run summary."""
        self.run_log["ended_at"] = self._timestamp()
        self.run_log["validation_results"] = self.validation_results
        self.run_log["errors"] = self.errors
        self.run_log["warnings"] = self.warnings
        self.run_log["summary"] = {
            "checks_passed": self.checks_passed,
            "total_checks": self.total_checks,
            "success": len(self.errors) == 0
        }

        # stop subprocess if running
        try:
            self._stop_app_subprocess()
        except Exception as e:
            self.log(f"Error while stopping subprocess: {e}", level="WARN")

        # write JSON summary
        try:
            with open(self.json_file, "w", encoding="utf-8") as jf:
                json.dump(self.run_log, jf, indent=2)
            self.log(f"Wrote JSON summary to {self.json_file}")
        except Exception as e:
            self.log(f"Failed to write JSON file {self.json_file}: {e}", level="WARN")

        # write closure lines and close log file
        self.log("=" * 60)
        self.log("VALIDATION SUMMARY")
        self.log(f"Checks Passed: {self.checks_passed}/{self.total_checks}")
        self.log(f"Errors: {len(self.errors)}")
        self.log(f"Warnings: {len(self.warnings)}")
        if self.errors:
            self.log("ERRORS (summary):", level="ERROR")
            for error in self.errors:
                self.log(f"  - {error}", level="ERROR")
        if self.warnings:
            self.log("WARNINGS (summary):", level="WARN")
            for w in self.warnings:
                self.log(f"  - {w}", level="WARN")

        if not self.errors:
            self.log("Validation PASSED - No critical errors found", level="RESULT")
        else:
            self.log("Validation FAILED - Critical errors found", level="RESULT")

        try:
            self.log_fp.close()
        except Exception:
            pass

    # -------------------- Utility for Streamlit integration --------------------
def run_flexible_validation(project_path: str, host: str = None, port: int = None):
    """
    Helper for Streamlit or other integrations.
    Returns a dict with success bool, log paths, and errors/warnings.
    """
    validator = FlexibleFlaskValidator(project_path)
    success = validator.run_validation(host=host, port=port)
    return {
        "success": success,
        "log_file": str(validator.log_file),
        "json_file": str(validator.json_file),
        "errors": validator.errors,
        "warnings": validator.warnings,
        "validation_results": validator.validation_results
    }


# -------------------- CLI --------------------
if __name__ == "__main__":
    if len(sys.argv) not in (2, 4):
        print("Usage: python flexible_validator.py <project_path> [host port]")
        sys.exit(1)

    proj = sys.argv[1]
    host = None
    port = None
    if len(sys.argv) == 4:
        host = sys.argv[2]
        port = int(sys.argv[3])

    validator = FlexibleFlaskValidator(proj)
    success = validator.run_validation(host=host, port=port)

    if success:
        print("\nValidation PASSED!")
        sys.exit(0)
    else:
        print("\nValidation FAILED!")
        sys.exit(1)
