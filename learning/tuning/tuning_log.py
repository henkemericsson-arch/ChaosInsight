#
# Tillstånd och beslutslogg för automatisk justering (005 avsnitt 18.5).
# All SQL går via DatabaseManager.
#

import json
from datetime import datetime, timezone

ENABLED_KEY = "auto_enabled"


class TuningLog:

    def __init__(self, db):
        self._db = db

    def enabled(self):
        # Avstängd som standard: bara värdet "1" slår på.
        return self._db.tuning_state_get(ENABLED_KEY) == "1"

    def set_enabled(self, flag, reason):
        self._db.tuning_state_set(ENABLED_KEY, "1" if flag else "0", self._now())
        self.record("enabled" if flag else "disabled", None, reason)

    def record(self, action, version, reason, evidence=None):
        self._db.insert_tuning_log({
            "logged_at": self._now(),
            "action": action,
            "version": version,
            "reason": reason,
            "evidence": json.dumps(evidence, sort_keys=True, default=str) if evidence is not None else None,
        })
        self._db.commit()

    def entries(self, limit=20):
        rows = self._db.tuning_log_entries(limit)
        for row in rows:
            row["evidence"] = json.loads(row["evidence"]) if row.get("evidence") else None
        return rows

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()
