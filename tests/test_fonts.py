"""フォント未導入時の通知、TTCの書体選択と太字の使い分けを検証する。"""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fontTools.ttLib import TTCollection, TTFont
from matplotlib import font_manager, rc_context

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.font_service import ReportFonts
from services.pdf_service import HtmlRenderer


class FontTests(unittest.TestCase):
    """システムの検証用書体からTTCを作り、選択処理を独立して検証する。"""

    def make_face(self, family, bold=False, italic=False):
        """テスト用書体の名前とスタイルを設定する。

        実際のメイリオを配布・代用するためのファイルではない。
        処理の検証にだけ使い、テスト終了時に削除する。

        Args:
            family (str): 検証するファミリー名。
            bold (bool): 太字の書体を使うか。
            italic (bool): 斜体のフラグを設定するか。

        Returns:
            fontTools.ttLib.TTFont: 一時TTCへ格納する書体。
        """
        source = font_manager.findfont(
            font_manager.FontProperties(
                family="DejaVu Sans", weight="bold" if bold else "normal"
            )
        )
        face = TTFont(source)
        for record in face["name"].names:
            if record.nameID in (1, 16, 21):
                record.string = family.encode(record.getEncoding())
        if italic:
            face["OS/2"].fsSelection |= 1
            face["OS/2"].fsSelection &= ~(1 << 6)
            face["head"].macStyle |= 2
        return face

    def make_collection(self, path, faces):
        """一時フォルダーへ複数書体のTTCを保存する。

        Args:
            path (pathlib.Path): 一時TTCの保存先。
            faces (list[TTFont]): 保存する書体の一覧。
        """
        collection = TTCollection()
        collection.fonts = faces
        collection.save(path)
        collection.close()

    def test_missing_meiryo_does_not_silently_change_font(self):
        """メイリオ未導入の場合は別書体へ置き換えず、不足を通知する。"""
        with patch.object(ReportFonts, "_installed", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "メイリオが見つかりません"):
                ReportFonts()

    def test_collection_selects_meiryo_regular_and_bold_and_cleans_up(self):
        """Meiryo UI・斜体を除外し、通常と太字を分けて登録・解放する。"""
        with TemporaryDirectory() as folder:
            regular, bold = Path(folder) / "meiryo.ttc", Path(folder) / "meiryob.ttc"
            self.make_collection(
                regular,
                [
                    self.make_face("Meiryo UI"),
                    self.make_face("Meiryo", italic=True),
                    self.make_face("Meiryo"),
                ],
            )
            self.make_collection(
                bold,
                [
                    self.make_face("Meiryo", bold=True, italic=True),
                    self.make_face("Meiryo", bold=True),
                ],
            )
            fonts = ReportFonts(regular)  # 同じフォルダーのmeiryob.ttcを自動検出。
            extracted = [fonts.regular, fonts.bold]
            try:
                self.assertEqual(fonts.family, "Meiryo")
                with rc_context({"font.family": "Meiryo"}):
                    for weight, path in zip(("normal", "bold"), extracted):
                        self.assertEqual(
                            Path(
                                font_manager.findfont(
                                    font_manager.FontProperties(
                                        family="Meiryo", weight=weight
                                    )
                                )
                            ),
                            path,
                        )
                renderer = HtmlRenderer()
                html = renderer.render(
                    {
                        "charts": {
                            "first_page": "data:image/png;base64,a",
                            "second_page": "data:image/png;base64,b",
                        }
                    }
                )
                self.assertIn('src="data:image/png;base64,a"', html)
                self.assertIn('src="data:image/png;base64,b"', html)
                self.assertNotIn("@font-face", html)
                self.assertNotIn("data:font/", html)
            finally:
                fonts.close()
            self.assertTrue(all(not path.exists() for path in extracted))
            self.assertTrue(
                all(
                    entry.fname not in map(str, extracted)
                    for entry in font_manager.fontManager.ttflist
                )
            )

    def test_invalid_bold_font_is_rejected(self):
        """通常書体や別ファミリーを太字に指定した場合は拒否する。"""
        regular = Path(
            font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans"))
        )
        wrong = Path(
            font_manager.findfont(
                font_manager.FontProperties(family="DejaVu Serif", weight="bold")
            )
        )
        for bold in (regular, wrong):
            with self.subTest(bold=bold):
                with self.assertRaisesRegex(ValueError, "同じファミリーの太字"):
                    ReportFonts(regular, bold)
        with self.assertRaisesRegex(RuntimeError, "--font-bold"):
            ReportFonts(regular)

    def test_ttf_registration_preserves_existing_fonts(self):
        """TTFの終了時も追加登録を外し、既存フォントの登録は保持する。"""
        paths = [
            Path(
                font_manager.findfont(
                    font_manager.FontProperties(family="DejaVu Sans", weight=weight)
                )
            )
            for weight in ("normal", "bold")
        ]
        before = [id(entry) for entry in font_manager.fontManager.ttflist]
        fonts = ReportFonts(*paths)
        try:
            self.assertTrue(all(path.is_file() for path in paths))
        finally:
            fonts.close()
        self.assertEqual(
            [id(entry) for entry in font_manager.fontManager.ttflist], before
        )
        self.assertTrue(all(path.is_file() for path in paths))
        fonts.close()  # 終了処理を再度呼んでも既存登録を変えない。
        self.assertEqual(
            [id(entry) for entry in font_manager.fontManager.ttflist], before
        )

    def test_collection_without_meiryo_is_rejected(self):
        """Meiryo UIのみのTTCから、誤って別書体を選ばないことを確認する。"""
        with TemporaryDirectory() as folder:
            path = Path(folder) / "other.ttc"
            self.make_collection(path, [self.make_face("Meiryo UI")])
            with self.assertRaisesRegex(ValueError, "Meiryoの通常書体がありません"):
                ReportFonts(path)

    def test_explicit_collection_takes_priority_over_registered_same_family(self):
        """同名書体が登録済みでも新しい指定を使い、解放後は元に戻す。"""
        with TemporaryDirectory() as folder:
            regular, bold = Path(folder) / "meiryo.ttc", Path(folder) / "meiryob.ttc"
            self.make_collection(regular, [self.make_face("Meiryo")])
            self.make_collection(bold, [self.make_face("Meiryo", bold=True)])
            first = ReportFonts(regular, bold)
            second = None
            try:
                second = ReportFonts(regular, bold)
                normal = font_manager.FontProperties(family="Meiryo", weight="normal")
                self.assertEqual(Path(font_manager.findfont(normal)), second.regular)
                second.close()
                self.assertEqual(Path(font_manager.findfont(normal)), first.regular)
            finally:
                if second is not None:
                    second.close()
                first.close()
