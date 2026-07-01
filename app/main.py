"""
Main pipeline orchestrator.

Flow:
1. Load config & validate
2. Load checkpoint (which md5s are already done)
3. Cross-reference with output file for safety
4. Read input CSV, skip completed books
5. Fill async queue
6. Spawn N workers
7. Periodic checkpoint saves
8. Final output validation report
"""

import asyncio
import os
import time
from typing import Set

from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
from rich.console import Console

from app.config import config
from app.utils.llm_logger import llm_logger
from app.parser.csv_reader import iter_books, count_rows
from app.parser.csv_writer import CSVWriter
from app.router.load_balancer import LoadBalancer
from app.router.router import Router
from app.workers.queue_manager import QueueManager
from app.workers.worker import Worker
from app.validator.csv_validator import validate_output_csv
from app.utils.logger import logger
from app.utils.helpers import human_time, eta

console = Console()




async def main() -> None:
    start_time = time.time()
    config.validate()

    console.rule("[bold blue]Book Classification Pipeline")
    logger.info(f"Input:   {config.INPUT_FILE}")
    logger.info(f"Output:  {config.OUTPUT_FILE}")
    logger.info(f"Workers: {config.MAX_WORKERS}  |  Batch size: {config.MAX_BOOKS_PER_BATCH}")

    # ── Setup ──────────────────────────────────────────────────────────────
    os.makedirs("output", exist_ok=True)
    os.makedirs("checkpoints", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("cache", exist_ok=True)

    writer = CSVWriter(config.OUTPUT_FILE)
    writer.prepare()

    # Rebuild processed set directly from the output CSV file
    output_md5s: Set[str] = writer.get_existing_md5s()
    logger.info(f"Total already done: {len(output_md5s):,}")

    # ── Load books ─────────────────────────────────────────────────────────
    logger.info("Counting input rows…")
    total_rows = count_rows(config.INPUT_FILE)
    logger.info(f"Total rows in input: {total_rows:,}")

    books = []
    skipped = 0
    for book in iter_books(config.INPUT_FILE):
        if book.md5 in output_md5s:
            skipped += 1
            continue
        books.append(book)

    logger.info(
        f"Books to classify: {len(books):,}  |  Already done (skipped): {skipped:,}"
    )

    if not books:
        console.print("[green]✓ All books already classified. Nothing to do.")
        validate_output_csv(config.OUTPUT_FILE)
        return

    # ── Providers & router ─────────────────────────────────────────────────
    balancer = LoadBalancer()
    balancer.setup()
    router = Router(balancer)

    # ── Queue & workers ────────────────────────────────────────────────────
    queue_mgr = QueueManager(max_queue_size=config.MAX_WORKERS * 10)
    num_workers = min(config.MAX_WORKERS, max(balancer.provider_count * 4, 8))

    # Shared progress counter (thread-safe via asyncio single-thread)
    progress_state = {"done": 0}

    def on_progress(n: int) -> None:
        progress_state["done"] += n

    workers = [
        Worker(
            worker_id=i,
            router=router,
            writer=writer,
            progress_callback=on_progress,
        )
        for i in range(num_workers)
    ]

    stop_updater = asyncio.Event()

    # ── Run ────────────────────────────────────────────────────────────────
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console,
        refresh_per_second=4,
    ) as progress:

        task = progress.add_task("Classifying books…", total=len(books))

        last_done = 0

        async def update_progress():
            nonlocal last_done
            while not stop_updater.is_set():
                new = progress_state["done"] - last_done
                if new > 0:
                    progress.advance(task, new)
                    last_done = progress_state["done"]
                await asyncio.sleep(0.5)

        # Start progress updater
        updater_task = asyncio.create_task(update_progress())

        # Fill queue (producer)
        producer = asyncio.create_task(
            queue_mgr.fill(books, config.MAX_BOOKS_PER_BATCH, num_workers)
        )

        # Start workers (consumers)
        worker_tasks = [
            asyncio.create_task(w.run(queue_mgr.queue)) for w in workers
        ]

        # Wait for all workers to finish
        await asyncio.gather(*worker_tasks)
        await producer

        stop_updater.set()
        await updater_task
        updater_task.cancel()

        # Final progress sync
        progress.advance(task, progress_state["done"] - last_done)

    elapsed = time.time() - start_time
    total_processed = sum(w.processed for w in workers)
    total_failed = sum(w.failed for w in workers)

    in_tok, out_tok = llm_logger.get_stats()

    console.rule("[bold green]Pipeline Complete")
    console.print(f"  Time elapsed : {human_time(elapsed)}")
    console.print(f"  Processed    : {total_processed:,}")
    console.print(f"  Failed       : {total_failed:,}")
    console.print(f"  Input tokens : {in_tok:,}")
    console.print(f"  Output tokens: {out_tok:,}")
    console.print(f"  Total tokens : {in_tok + out_tok:,}")
    console.print(f"  Output file  : {config.OUTPUT_FILE}")

    # ── Validate output ────────────────────────────────────────────────────
    console.print("\n[bold]Running output validation…")
    validate_output_csv(config.OUTPUT_FILE)