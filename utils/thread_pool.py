import threading
import uuid
import time
import json
from typing import Callable
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm


class ThreadPool:
    def __init__(self, max_workers: int = 16, callback: Callable = None):
        self.max_workers = max_workers
        self.callback = callback or self.default_callback
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.tasks = {}
        self.lock = threading.Lock()

    def default_callback(self, task_id, result):
        with open("./data/questions/task_results.jsonl", "a", encoding="utf-8") as f:
            f.write(
                json.dumps({"task_id": task_id, "result": result}, ensure_ascii=False)
                + "\n"
            )

    def _wrap_task(self, task_id: str, func: Callable, args: tuple, kwargs: dict):
        with self.lock:
            self.tasks[task_id]["status"] = "running"
        try:
            result = func(*args, **kwargs)
            with self.lock:
                self.tasks[task_id].update({"status": "finished", "result": result})
            self.callback(task_id, result)
        except Exception as e:
            with self.lock:
                self.tasks[task_id].update({"status": "error", "error": str(e)})
            self.callback(task_id, {"error": str(e)})

    def submit(self, func: Callable, args: tuple = (), kwargs: dict = {}) -> str:
        task_id = str(uuid.uuid4())
        with self.lock:
            self.tasks[task_id] = {"status": "submitted"}
        self.executor.submit(self._wrap_task, task_id, func, args, kwargs)
        return task_id

    def submit_all_and_wait(
        self, task_list: list[tuple[Callable, tuple, dict]]
    ) -> dict:
        task_ids = [self.submit(func, args, kwargs) for func, args, kwargs in task_list]
        total = len(task_ids)
        completed = set()

        pbar = tqdm(total=total, desc="任务进度")
        while True:
            running = 0
            with self.lock:
                for tid in task_ids:
                    status = self.tasks[tid]["status"]
                    if tid not in completed and status in {"finished", "error"}:
                        completed.add(tid)
                        pbar.update(1)
                    elif status == "running":
                        running += 1
            pbar.set_description(f"运行中: {running}个")
            if len(completed) == total:
                pbar.close()
                return {tid: self.tasks[tid] for tid in task_ids}
            time.sleep(0.5)
