"""画像のメモリ化とバッチの保存先競合を検証する。"""

import base64
import json
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.chart_service import ChartService
from batch import load_jobs
from services.data_service import load_data, build_context


class MemoryBatchTests(unittest.TestCase):
    """ファイルを介さないPNG生成と出力競合防止を確認する。"""

    def test_save_without_disk_closes_figure(self):
        """PNGがメモリに生成され、Figureが保存後に閉じることを確認する。"""
        service = ChartService.__new__(ChartService)
        service.output_dir = None
        service.png_bytes = {}
        fig = plt.figure()
        number = fig.number
        with patch.object(
            Path, "write_bytes", side_effect=AssertionError("disk write")
        ):
            uri = service.save("one", fig)
        data = base64.b64decode(uri.split(",", 1)[1])
        self.assertTrue(data.startswith(b"\x89PNG"))
        self.assertEqual(service.png_bytes["one"], data)
        self.assertFalse(plt.fignum_exists(number))

    def test_complete_pages_without_intermediate_pngs(self):
        """部品画像を作らず、完成ページだけをメモリに保持することを確認する。"""
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / "examples/customer.json").read_text())
        frame = load_data(root / "examples/sample.csv", config["target_month"])
        context, series = build_context(frame, config)
        service = ChartService.__new__(ChartService)
        service.output_dir = None
        service.png_bytes = {}
        existing_figures = set(plt.get_fignums())
        try:
            with warnings.catch_warnings(), patch.object(
                Path, "write_bytes", side_effect=AssertionError("disk write")
            ):
                warnings.filterwarnings("ignore", message="Glyph .* missing from font")
                images = service.create_all(series, config, context)
            self.assertEqual(set(images), {"first_page", "second_page"})
            self.assertEqual(set(service.png_bytes), set(images))
            for name, uri in images.items():
                self.assertEqual(
                    base64.b64decode(uri.split(",", 1)[1]), service.png_bytes[name]
                )
            self.assertEqual(set(plt.get_fignums()), existing_figures)
        finally:
            for number in set(plt.get_fignums()) - existing_figures:
                plt.close(number)

    def test_duplicate_customer_ids_rejected(self):
        """同名PDFの生成につながる顧客ID重複を拒否する。"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "jobs.json"
            path.write_text(
                json.dumps([{"id": "a", "csv": "x.csv", "config": "x.json"}] * 2)
            )
            with self.assertRaisesRegex(ValueError, "重複"):
                load_jobs(path, Path(folder) / "out")

    def test_input_output_collision_rejected(self):
        """入力ファイルとPDF保存先の競合を拒否する。"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "jobs.json"
            path.write_text(
                json.dumps([{"id": "a", "csv": "out/a.pdf", "config": "x.json"}])
            )
            with self.assertRaisesRegex(ValueError, "競合"):
                load_jobs(path, Path(folder) / "out")
