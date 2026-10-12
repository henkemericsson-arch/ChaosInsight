#
# ParameterStore - versionerade parameteruppsättningar i Knowledge Base
# (tabellen parameter_sets). Se 005_Learning_Engine_Design.md avsnitt 4 och 16.
#
# Ansvar: lagra och hämta uppsättningar. Store vet inte vilka parametrar som
# finns eller vad de betyder (det gör schemat i learning/trav/), och den
# kör ingen SQL själv - allt går via DatabaseManager.
#
# Version 0 är baseline: dagens värden, oföränderlig. Varje ändring skapar
# en ny version; ingen skrivs över.
#

import json
from datetime import datetime, timezone

BASELINE_VERSION = 0

STATUS_BASELINE = "baseline"
STATUS_ACTIVE = "active"
STATUS_REJECTED = "rejected"
STATUS_ROLLED_BACK = "rolled_back"

CHANGEABLE_STATUSES = (STATUS_ACTIVE, STATUS_REJECTED, STATUS_ROLLED_BACK)


class BaselineProtectedError(Exception):
    pass


class ParameterStore:

    def __init__(self, db):
        self._db = db

    # ------------------------------------------------------------
    # Läsning
    # ------------------------------------------------------------

    def get(self, version):
        return self._decode(self._db.parameter_set(version))

    def all(self):
        return [self._decode(row) for row in self._db.parameter_sets()]

    def active(self):
        #
        # Senaste versionen med status active; annars baseline (om den
        # finns). None om tabellen är tom.
        #
        rows = [r for r in self.all() if r["status"] == STATUS_ACTIVE]
        if rows:
            return max(rows, key=lambda r: r["version"])
        return self.get(BASELINE_VERSION)

    # ------------------------------------------------------------
    # Skrivning
    # ------------------------------------------------------------

    def ensure_baseline(self, values, reason="Dagens värden (baseline)"):
        #
        # Skapar version 0 om den saknas. En redan befintlig baseline
        # rörs aldrig, även om `values` skiljer sig (ny kod får inte
        # i tysthet ändra utgångspunkten). Returnerar baseline-raden.
        #
        existing = self.get(BASELINE_VERSION)
        if existing is not None:
            return existing

        self._db.insert_parameter_set(self._row(
            version=BASELINE_VERSION, parent=None, status=STATUS_BASELINE,
            params=values, reason=reason, evidence=None,
        ))
        self._db.commit()
        return self.get(BASELINE_VERSION)

    def add(self, params, parent, reason, evidence=None, status=STATUS_ACTIVE):
        #
        # Ny version (föregående max + 1). Används av etapp 4.
        #
        versions = [r["version"] for r in self.all()]
        version = (max(versions) + 1) if versions else BASELINE_VERSION + 1
        if version == BASELINE_VERSION:
            version += 1

        self._db.insert_parameter_set(self._row(
            version=version, parent=parent, status=status,
            params=params, reason=reason, evidence=evidence,
        ))
        self._db.commit()
        return version

    def set_status(self, version, status):
        if version == BASELINE_VERSION:
            raise BaselineProtectedError("Baseline (version 0) kan inte ändras")
        if status not in CHANGEABLE_STATUSES:
            raise ValueError(f"Ogiltig status: {status}")
        self._db.update_parameter_status(version, status)
        self._db.commit()

    # ------------------------------------------------------------
    # Hjälpare
    # ------------------------------------------------------------

    @staticmethod
    def _row(version, parent, status, params, reason, evidence):
        return {
            "version": version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "parent": parent,
            "status": status,
            "params": json.dumps(params, sort_keys=True),
            "reason": reason,
            "evidence": json.dumps(evidence, sort_keys=True) if evidence is not None else None,
        }

    @staticmethod
    def _decode(row):
        if row is None:
            return None
        decoded = dict(row)
        decoded["params"] = json.loads(decoded["params"]) if decoded.get("params") else {}
        decoded["evidence"] = json.loads(decoded["evidence"]) if decoded.get("evidence") else None
        return decoded
