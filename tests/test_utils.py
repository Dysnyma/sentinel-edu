"""core.utils 单元测试 — run_concurrently、JSONL 工具。"""

import time
from core.utils import run_concurrently


class TestRunConcurrently:
    """并发执行工具（任务 3.1）。"""

    def test_normal_execution(self):
        def double(x):
            return x * 2
        tasks = [(double, (1,)), (double, (2,)), (double, (3,))]
        results = run_concurrently(tasks)
        assert results == [2, 4, 6]

    def test_preserves_order(self):
        """结果按输入顺序返回，即使任务完成顺序不同。"""
        def slow_task(n):
            time.sleep(0.01 * (3 - n))  # 第3个最快，第1个最慢
            return n

        tasks = [(slow_task, (1,)), (slow_task, (2,)), (slow_task, (3,))]
        results = run_concurrently(tasks)
        assert results == [1, 2, 3]

    def test_exception_collection(self):
        """异常任务在结果列表中对应位置为 Exception。"""
        def ok(x):
            return x

        def broken(x):
            raise ValueError(f"fail {x}")

        tasks = [(ok, (1,)), (broken, (2,)), (ok, (3,))]
        results = run_concurrently(tasks)
        assert results[0] == 1
        assert isinstance(results[1], ValueError)
        assert str(results[1]) == "fail 2"
        assert results[2] == 3

    def test_exception_does_not_block_others(self):
        """一个任务抛异常不影响其他任务执行。"""
        def ok(x):
            return x

        tasks = [(ok, (1,)), (ok, (2,)), (ok, (3,))]
        results = run_concurrently(tasks, max_workers=6)
        assert results == [1, 2, 3]

    def test_progress_callback(self):
        """进度回调次数 = 任务总数。"""
        def ok(x):
            return x

        calls = []
        tasks = [(ok, (1,)), (ok, (2,)), (ok, (3,)), (ok, (4,))]
        run_concurrently(tasks, progress_callback=lambda d, t: calls.append((d, t)))
        assert len(calls) == 4
        assert calls[-1] == (4, 4)  # 最后回调 (completed=4, total=4)

    def test_dict_args(self):
        """支持关键字参数传参。"""
        def greet(greeting, name):
            return f"{greeting}, {name}!"

        tasks = [(greet, {"greeting": "Hello", "name": "Alice"})]
        results = run_concurrently(tasks)
        assert results == ["Hello, Alice!"]
