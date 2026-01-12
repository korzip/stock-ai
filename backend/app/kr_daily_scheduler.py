import os
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .ingest_dart import main as ingest_dart
from .ingest_kr_daily_bulk import main as ingest_kr_daily_bulk
from .ingest_us_daily_bulk import main as ingest_us_daily_bulk
from .sync_kr_instruments import main as sync_kr_instruments


def _parse_time(value: str) -> tuple[int, int]:
    hour, minute = value.split(":")
    return int(hour), int(minute)


def _run_all() -> None:
    sync_kr_instruments()
    ingest_kr_daily_bulk()
    if os.getenv("DART_API_KEY"):
        ingest_dart()
    ingest_us_daily_bulk()


def main() -> None:
    run_time = os.getenv("KR_DAILY_RUN_TIME", "18:30")
    hour, minute = _parse_time(run_time)

    scheduler = BlockingScheduler(timezone="Asia/Seoul")
    scheduler.add_job(
        _run_all,
        CronTrigger(hour=hour, minute=minute),
        id="kr_daily_job",
        replace_existing=True,
    )

    us_time = os.getenv("US_DAILY_RUN_TIME", "20:00")
    us_hour, us_minute = _parse_time(us_time)
    scheduler.add_job(
        ingest_us_daily_bulk,
        CronTrigger(hour=us_hour, minute=us_minute),
        id="us_daily_job",
        replace_existing=True,
    )

    print(f"KR daily scheduler started (Asia/Seoul) at {run_time}.")
    print(f"US daily scheduler started (Asia/Seoul) at {us_time}.")
    print("Press Ctrl+C to stop.")
    scheduler.start()


if __name__ == "__main__":
    main()
