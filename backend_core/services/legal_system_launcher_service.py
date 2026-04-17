import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Service:
    name: str
    cmd: list[str]
    cwd: Path
    port: int | None = None
    required: bool = True


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _backend_dir() -> Path:
    return _repo_root() / "legal-agent" / "legal-agent-backend"


def _frontend_dir() -> Path:
    return _backend_dir().parent / "legal-agent-frontend"


def _qa_entry_script() -> Path:
    return _repo_root() / "backend_core" / "services" / "qa_rag_main_service.py"


def _backend_core_service_script(filename: str) -> Path:
    return _repo_root() / "backend_core" / "services" / filename


def _backend_core_module_name(module_leaf: str) -> str:
    return f"backend_core.services.{module_leaf}"


def _npm_cmd() -> str | None:
    return shutil.which("npm.cmd") or shutil.which("npm")


def _find_listening_pids(port: int) -> set[int]:
    if os.name == "nt":
        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            errors="ignore",
            check=False,
        )
        pids: set[int] = set()
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = re.split(r"\s+", line)
            if len(parts) < 5:
                continue
            local_addr = parts[1]
            state = parts[3].upper()
            pid_text = parts[4]
            if state != "LISTENING":
                continue
            if not (local_addr.endswith(f":{port}") or local_addr.endswith(f"]:{port}")):
                continue
            try:
                pid = int(pid_text)
            except ValueError:
                continue
            if pid > 0:
                pids.add(pid)
        return pids

    pids: set[int] = set()
    lsof = shutil.which("lsof")
    if not lsof:
        return pids
    result = subprocess.run(
        [lsof, "-t", f"-iTCP:{port}", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
        errors="ignore",
        check=False,
    )
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pids.add(int(line))
        except ValueError:
            continue
    return pids


def _force_kill_pid(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            errors="ignore",
            check=False,
        )
        return
    try:
        os.kill(pid, 15)
    except OSError:
        return


def _force_kill_all_python_except_self() -> None:
    if os.name != "nt":
        return
    # Final fallback for reloader/orphan cases that keep ports occupied.
    current_pid = os.getpid()
    subprocess.run(
        [
            "taskkill",
            "/F",
            "/FI",
            "IMAGENAME eq python.exe",
            "/FI",
            f"PID ne {current_pid}",
        ],
        capture_output=True,
        text=True,
        errors="ignore",
        check=False,
    )


def ensure_port_released(port: int, timeout_sec: float = 10.0) -> None:
    deadline = time.time() + timeout_sec
    warned_once = False
    tried_python_fallback = False

    while True:
        pids = _find_listening_pids(port)
        pids.discard(os.getpid())

        if not pids:
            if warned_once:
                print(f"[info] Port {port} released.")
            return

        pid_text = ", ".join(str(pid) for pid in sorted(pids))
        if not warned_once:
            print(f"[warn] Port {port} is occupied by PID(s): {pid_text}; stopping them...")
            warned_once = True

        for pid in sorted(pids):
            _force_kill_pid(pid)

        if time.time() >= deadline:
            if os.name == "nt" and not tried_python_fallback:
                print("[warn] Precise PID kill did not release the port. Run fallback: taskkill /F /IM python.exe")
                _force_kill_all_python_except_self()
                tried_python_fallback = True
                deadline = time.time() + 8
                time.sleep(0.8)
                continue
            raise RuntimeError(f"Port {port} is still occupied (PID(s): {pid_text})")

        time.sleep(0.4)


def ensure_frontend_deps(frontend_dir: Path) -> None:
    node_modules = frontend_dir / "node_modules"
    if node_modules.exists():
        return
    npm = _npm_cmd()
    if not npm:
        raise RuntimeError("npm not found. Install Node.js with npm first.")
    print("[setup] Installing frontend dependencies (npm install)...")
    subprocess.run([npm, "install"], cwd=frontend_dir, check=True)


def _optional_python_service(
    services: list[Service],
    name: str,
    script: Path,
    port: int,
    required: bool = False,
) -> None:
    if script.exists():
        services.append(
            Service(
                name=name,
                cmd=[sys.executable, str(script)],
                cwd=script.parent,
                port=port,
                required=required,
            )
        )
    else:
        print(f"[warn] service entry not found: {script}")


def _optional_python_module_service(
    services: list[Service],
    name: str,
    module_name: str,
    cwd: Path,
    port: int,
    required: bool = False,
) -> None:
    services.append(
        Service(
            name=name,
            cmd=[sys.executable, "-m", module_name],
            cwd=cwd,
            port=port,
            required=required,
        )
    )


def build_services(start_frontend: bool, start_qa: bool, profile: str) -> list[Service]:
    backend = _backend_dir()
    services = [
        Service(
            name="legal-agent-backend",
            cmd=[
                sys.executable,
                "-m",
                "uvicorn",
                "app.server:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=backend,
            port=8000,
            required=True,
        )
    ]

    if start_qa:
        _optional_python_module_service(
            services,
            "qa-rag-service",
            _backend_core_module_name("qa_rag_main_service"),
            _repo_root(),
            port=8012,
            required=True,
        )

    if profile == "full":
        root = _repo_root()
        _optional_python_module_service(
            services,
            "legal-login",
            _backend_core_module_name("legal_login_service"),
            root,
            port=5000,
        )
        _optional_python_module_service(
            services,
            "legal-user",
            _backend_core_module_name("legal_user_service"),
            root,
            port=5009,
        )
        _optional_python_module_service(
            services,
            "legal-contractdata",
            _backend_core_module_name("legal_contractdata_service"),
            root,
            port=5010,
        )
        _optional_python_module_service(
            services,
            "legal-administrator",
            _backend_core_module_name("legal_administrator_service"),
            root,
            port=5011,
        )
        _optional_python_service(
            services,
            "manager-portal",
            root / "Manager" / "manager.py",
            port=8003,
        )
        _optional_python_service(
            services,
            "sparkshow-dashboard",
            root / "SparkShow" / "show.py",
            port=5008,
        )
        _optional_python_service(
            services,
            "analysis-case",
            root / "AnalysisCase" / "kimiapi.py",
            port=5006,
        )
        _optional_python_service(services, "lawshow", root / "LawShow" / "lawshow.py", port=5003)
        _optional_python_service(
            services,
            "modelagreement",
            root / "ModelAgreement" / "modelagreement.py",
            port=5002,
        )
        _optional_python_service(
            services,
            "manage-agreement",
            root / "ModelAgreement" / "managelagreement.py",
            port=5027,
        )
        _optional_python_service(services, "calculate", root / "Calculate" / "caculate.py", port=5007)
        _optional_python_service(
            services,
            "riskanalysis",
            root / "RiskAnalysis" / "riskanalysis.py",
            port=5020,
        )
        _optional_python_service(
            services,
            "modellitigation",
            root / "ModelLitigation" / "modellitigation.py",
            port=5025,
        )
        _optional_python_service(
            services,
            "manage-litigation",
            root / "ModelLitigation" / "managelitigation.py",
            port=5026,
        )
        _optional_python_service(
            services,
            "modelagreement-mymodel",
            root / "ModelAgreement" / "mymodel.py",
            port=5029,
        )
        _optional_python_service(
            services,
            "modellitigation-mymodel",
            root / "ModelLitigation" / "mymodel.py",
            port=5030,
        )
        _optional_python_service(
            services,
            "modelagreement-feedback",
            root / "ModelAgreement" / "feedback.py",
            port=5099,
        )
        _optional_python_service(
            services,
            "manager-feedback",
            root / "Manager" / "feedback.py",
            port=5032,
        )
        _optional_python_service(
            services,
            "modellitigation-feedback",
            root / "ModelLitigation" / "feedback.py",
            port=5031,
        )
        _optional_python_service(
            services,
            "manager-feedback-b",
            root / "Manager" / "feedback_b.py",
            port=5033,
        )

    if start_frontend:
        frontend = _frontend_dir()
        package_json = frontend / "package.json"
        if not package_json.exists():
            print(f"[warn] Frontend package.json not found: {package_json}")
        else:
            ensure_frontend_deps(frontend)
            npm = _npm_cmd()
            if not npm:
                raise RuntimeError("npm not found, cannot start frontend dev server.")
            services.append(
                Service(
                    name="legal-agent-frontend",
                    cmd=[
                        npm,
                        "run",
                        "dev",
                        "--",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "5173",
                        "--strictPort",
                    ],
                    cwd=frontend,
                    port=5173,
                    required=True,
                )
            )

    return services


def terminate_all(processes: list[tuple[Service, subprocess.Popen]]) -> None:
    for service, process in reversed(processes):
        if process.poll() is None:
            print(f"[stop] {service.name}")
            process.terminate()

    deadline = time.time() + 8
    for service, process in reversed(processes):
        if process.poll() is None:
            timeout = max(0, deadline - time.time())
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                print(f"[kill] {service.name}")
                process.kill()


def _primary_entry_url(start_frontend: bool, start_qa: bool, profile: str) -> str:
    if profile == "full":
        return "http://127.0.0.1:5000"
    if start_frontend:
        return "http://127.0.0.1:5173"
    return "http://127.0.0.1:8000"


def _open_primary_entry(url: str) -> None:
    try:
        webbrowser.open(url, new=2)
        print(f"[info] Opened primary entry: {url}")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] Failed to open browser automatically: {exc}")


def _wait_for_port(host: str, port: int, timeout_sec: float = 20.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.8):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def _wait_and_open_primary_entry(url: str) -> None:
    match = re.match(r"^https?://([^:/]+):(\d+)", url)
    if not match:
        _open_primary_entry(url)
        return

    host = match.group(1)
    port = int(match.group(2))
    if _wait_for_port(host, port):
        _open_primary_entry(url)
        return

    print(f"[warn] Primary entry did not become ready in time: {url}")


def run_all(start_frontend: bool, start_qa: bool, profile: str, auto_open: bool) -> int:
    services = build_services(start_frontend=start_frontend, start_qa=start_qa, profile=profile)
    ready_services: list[Service] = []

    for service in services:
        if service.port is None:
            ready_services.append(service)
            continue
        try:
            ensure_port_released(service.port)
            ready_services.append(service)
        except RuntimeError as exc:
            if service.required:
                raise
            print(
                f"[warn] {service.name} on port {service.port} could not be released. "
                f"Skip launching this service and keep existing process. ({exc})"
            )

    services = ready_services
    processes: list[tuple[Service, subprocess.Popen]] = []

    print("[info] Starting services:")
    for service in services:
        print(f"  - {service.name}: {' '.join(service.cmd)}")
        process = subprocess.Popen(service.cmd, cwd=service.cwd)
        processes.append((service, process))
        time.sleep(0.4)

    print("[ready] Service URLs:")
    print("  - Backend/API: http://127.0.0.1:8000")
    if start_frontend:
        print("  - Frontend dev: http://127.0.0.1:5173")
    else:
        print("  - Frontend(static): http://127.0.0.1:8000")
    if start_qa:
        print("  - QA API: http://127.0.0.1:8012/v1/chat/completions")
    if profile == "full":
        print("  - Login: http://127.0.0.1:5000")
        print("  - UserData: http://127.0.0.1:5009")
        print("  - ContractData: http://127.0.0.1:5010")
        print("  - Administrator: http://127.0.0.1:5011")
        print("  - Manager Portal: http://127.0.0.1:8003")
        print("  - SparkShow Dashboard: http://127.0.0.1:5008")
        print("  - Analysis Case: http://127.0.0.1:5006")
        print("  - LawShow: http://127.0.0.1:5003")
        print("  - ModelAgreement: http://127.0.0.1:5002")
        print("  - Manage Agreement: http://127.0.0.1:5027")
        print("  - Calculate: http://127.0.0.1:5007")
        print("  - RiskAnalysis: http://127.0.0.1:5020")
        print("  - ModelLitigation: http://127.0.0.1:5025")
        print("  - Manage Litigation: http://127.0.0.1:5026")
        print("  - ModelAgreement MyModel: http://127.0.0.1:5029")
        print("  - ModelLitigation MyModel: http://127.0.0.1:5030")
        print("  - ModelAgreement Feedback: http://127.0.0.1:5099")
        print("  - ModelLitigation Feedback: http://127.0.0.1:5031")
        print("  - Manager Feedback: http://127.0.0.1:5032")
        print("  - Manager Feedback B: http://127.0.0.1:5033")
    primary_entry = _primary_entry_url(start_frontend=start_frontend, start_qa=start_qa, profile=profile)
    print(f"  - Primary entry: {primary_entry}")
    print("[info] Press Ctrl+C to stop all services.")
    if auto_open:
        _wait_and_open_primary_entry(primary_entry)

    try:
        while True:
            for service, process in processes:
                code = process.poll()
                if code is not None:
                    print(f"[exit] {service.name} exited with code {code}")
                    return code
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[info] Stopping services...")
        return 0
    finally:
        terminate_all(processes)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-command launcher for legal-agent backend + frontend + QA service."
    )
    parser.add_argument(
        "--frontend",
        choices=["dev", "static"],
        default="dev",
        help="dev: start Vite frontend; static: only use backend static/dist",
    )
    parser.add_argument(
        "--skip-qa",
        action="store_true",
        help="Do not start QA rag service on port 8012.",
    )
    parser.add_argument(
        "--profile",
        choices=["core", "full"],
        default="full",
        help="core: legal-agent core services; full: core + linked sub-services",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the primary entry page automatically after startup.",
    )
    args = parser.parse_args()

    exit_code = run_all(
        start_frontend=args.frontend == "dev",
        start_qa=not args.skip_qa,
        profile=args.profile,
        auto_open=not args.no_browser,
    )
    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
