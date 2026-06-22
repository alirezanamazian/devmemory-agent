import math
from datetime import datetime, timezone

from app.config import settings

# Ebbinghaus (1885) forgetting curve: R = e^(-t/S)
# We adapt it: importance = base * e^(-effective_decay * days)
# with access_count adding log-scale retention (spaced repetition effect)

# Tuned empirically — preferences outlast bug fixes by ~5x in practice
DECAY_RATES = {
    "preference": 0.02,
    "pattern": 0.03,
    "decision": 0.05,
    "bug_fix": 0.08,
    "general": 0.10,
}


class DecayEngine:
    def calculate_current_importance(
        self,
        base_importance: float,
        decay_rate: float,
        last_accessed: datetime,
        access_count: int,
    ) -> float:
        """Ebbinghaus-based decay. Access count adds log-scale retention bonus."""
        now = datetime.now(timezone.utc)
        if last_accessed.tzinfo is None:
            last_accessed = last_accessed.replace(tzinfo=timezone.utc)
        days_since_access = (now - last_accessed).total_seconds() / 86400

        # log1p(n) * 0.1: first few accesses matter most, diminishing returns after ~10
        retention_bonus = math.log1p(access_count) * 0.1
        effective_decay = max(0.0, decay_rate - retention_bonus)

        current = base_importance * math.exp(-effective_decay * days_since_access)
        return max(0.0, min(1.0, current))

    def should_forget(self, current_importance: float) -> bool:
        return current_importance < settings.MEMORY_IMPORTANCE_THRESHOLD

    def boost_importance(self, base_importance: float, boost: float = 0.2) -> float:
        """Called when a memory is successfully recalled — strengthens it (spaced repetition)."""
        return min(1.0, base_importance + boost)

    def calculate_decay_rate_for_type(self, memory_type: str) -> float:
        return DECAY_RATES.get(memory_type, DECAY_RATES["general"])
