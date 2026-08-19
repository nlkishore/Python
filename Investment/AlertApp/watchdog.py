"""
Watchdog for the AlertApp Green API listener.

Run periodically (Task Scheduler: at logon + every few minutes). If the listener
is not running, start it detached (no window, logs to listener.log) and send a
WhatsApp notification that it was restarted.

Detection uses the same single-instance named mutex the listener holds, so it
works across sessions and is race-free.

NOTE: A watchdog can only recover a crashed process while the machine is UP. To
be alerted when the whole machine is DOWN (power loss, no internet, OS crash),
rely on the listener's external heartbeat (dead-man's switch) — see
LISTENER_HEARTBEAT_URL / heartbeat_url.txt in backgroundAlert1.py.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
INVESTMENT_ROOT = SCRIPT_DIR.parent
if str(INVESTMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(INVESTMENT_ROOT))

from shared.config_loader import green_api_credentials, read_merged_ini  # noqa: E402

LISTENER_SCRIPT = SCRIPT_DIR / "backgroundAlert1.py"
LISTENER_LOG = SCRIPT_DIR / "listener.log"

_MUTEX_NAME = "Global\\AlertApp_GreenAPI_Listener"
_SYNCHRONIZE = 0x00100000
_DETACHED_PROCESS = 0x00000008


def listener_running() -> bool:
    """True if the listener's single-instance mutex already exists."""
    if os.name != "nt":
        try:
            out = subprocess.run(
                ["pgrep", "-f", "backgroundAlert1.py"],
                capture_output=True, text=True, timeout=10,
            )
            return bool(out.stdout.strip())
        except Exception:  # noqa: BLE001
            return False
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenMutexW(_SYNCHRONIZE, False, _MUTEX_NAME)
    if handle:
        kernel32.CloseHandle(handle)
        return True
    return False


def start_listener() -> None:
    """Launch the listener detached (no console) with output appended to log."""
    log_file = open(LISTENER_LOG, "a", encoding="utf-8")
    creationflags = _DETACHED_PROCESS if os.name == "nt" else 0
    subprocess.Popen(
        [sys.executable, str(LISTENER_SCRIPT)],
        cwd=str(SCRIPT_DIR),
        stdout=log_file,
        stderr=log_file,
        creationflags=creationflags,
        close_fds=True,
    )


def notify(text: str) -> None:
    """Best-effort WhatsApp notification; never raises."""
    try:
        from whatsapp_api_client_python import API

        parser = read_merged_ini(SCRIPT_DIR)
        id_inst, token, phone = green_api_credentials(parser, section="whatsapp")
        if not (id_inst and token and phone):
            print("[!] Watchdog notify skipped: credentials missing.", flush=True)
            return
        API.GreenAPI(id_inst, token).sending.sendMessage(f"{phone}@c.us", text)
    except Exception as exc:  # noqa: BLE001
        print(f"[!] Watchdog notify failed: {exc}", flush=True)


def main() -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if listener_running():
        print(f"[{now}] Listener running. OK.", flush=True)
        return 0
    print(f"[{now}] Listener DOWN. Restarting...", flush=True)
    start_listener()
    notify(
        f"AlertApp listener was DOWN and has been restarted at {now}. "
        "If you see this often, check the PC."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
