import json
import subprocess

#
# Spårbarhet för varje prediktion: vilken kodversion som skapade den
# och alla delmått (horse.metrics) hästen fick. Learning Engine behöver
# båda för att kunna säga vilka signaler som bär vikt och för att inte
# blanda utfall från olika systemversioner.
#
_CACHED_VERSION = None


def code_version():
    # Kort git-hash (+ "-dirty" vid ej incheckade ändringar). Ingen
    # manuell versionssträng att glömma uppdatera. "okand" utan git.
    global _CACHED_VERSION
    if _CACHED_VERSION is not None:
        return _CACHED_VERSION
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        version = head.stdout.strip() if head.returncode == 0 else ""
        if version:
            status = subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                capture_output=True, text=True, timeout=5,
            )
            if status.returncode == 0 and status.stdout.strip():
                version += "-dirty"
    except (OSError, subprocess.SubprocessError):
        version = ""
    _CACHED_VERSION = version or "okand"
    return _CACHED_VERSION


def metrics_to_dict(metrics):
    # Bara tal sparas (inga objekt), så att loggen alltid är läsbar.
    clean = {}
    for key, value in (metrics or {}).items():
        if isinstance(value, bool):
            clean[str(key)] = int(value)
        elif isinstance(value, (int, float)):
            clean[str(key)] = value
    return clean


def dump_metrics(metrics):
    # JSON-sträng för kolumnen metrics_json; None om inget att spara.
    if not metrics:
        return None
    return json.dumps(metrics, ensure_ascii=False, sort_keys=True)


def load_metrics(text):
    if not text:
        return {}
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}
