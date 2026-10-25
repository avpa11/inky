import json
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

LESSONS = json.loads((Path(__file__).parent / "data" / "french.json").read_text())


def learning_day(now, timezone, rollover):
    local = now.astimezone(ZoneInfo(timezone))
    cutoff = time.fromisoformat(rollover)
    return (local.date() - timedelta(days=local.time().replace(tzinfo=None) < cutoff)).isoformat()


def lesson_for(day, anchor):
    index = (datetime.fromisoformat(day).date() - datetime.fromisoformat(anchor).date()).days
    return LESSONS[max(0, index) % len(LESSONS)]
