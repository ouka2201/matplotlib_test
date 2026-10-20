"""共通の並列処理を、実際のspawnプロセスで検証する。"""

import multiprocessing
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.batch_service import run_parallel

_barrier = None


def initialize_probe(barrier):
    """子プロセスごとに、テスト用の同期オブジェクトを保持する。

    Args:
        barrier (multiprocessing.Barrier): 2プロセスの開始を待ち合わせる。
    """
    global _barrier
    _barrier = barrier


def run_probe(target):
    """軽い対象を1件受け取り、処理したプロセス情報を返す。

    Args:
        target (dict): idを持つ対象。

    Returns:
        dict: 対象IDと子プロセスID。
    """
    if target["id"] < 2:
        _barrier.wait(timeout=20)
    return {"id": target["id"], "pid": os.getpid()}


class ParallelServiceTests(unittest.TestCase):
    """対象・初期化・1件ずつの実行がspawnでも動くことを確認する。"""

    def test_real_spawn_processes_receive_each_target_once(self):
        """初期化済みの2プロセスへ全対象を重複なく渡す。"""
        barrier = multiprocessing.get_context("spawn").Barrier(2)
        results = list(
            run_parallel(
                [{"id": index} for index in range(20)],
                run_probe,
                workers=2,
                initializer=initialize_probe,
                initargs=(barrier,),
            )
        )
        self.assertEqual(len(results), 20)
        self.assertEqual({row["id"] for row in results}, set(range(20)))
        self.assertEqual(len({row["pid"] for row in results}), 2)
        self.assertTrue(all(row["pid"] != os.getpid() for row in results))
