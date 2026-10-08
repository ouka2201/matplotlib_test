"""メイリオの通常書体・太字書体を、各ワーカーで一度だけ準備する。"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from fontTools.ttLib import TTCollection, TTFont
from matplotlib import font_manager


def _is_bold(face):
    """フォントの太字フラグまたはウェイト値を確認する。

    Args:
        face (fontTools.ttLib.TTFont): 判定する書体。

    Returns:
        bool: 太字フラグがある、またはウェイト値が600以上ならTrue。
    """
    return (
        bool(face["OS/2"].fsSelection & (1 << 5)) or face["OS/2"].usWeightClass >= 600
    )


def _clear_cache():
    """登録変更を反映し、Windowsでも一時フォントを削除できるようにする。"""
    font_manager.fontManager._findfont_cached.cache_clear()
    font_manager._get_font.cache_clear()


class ReportFonts:
    """通常書体・太字書体と、TTC展開用の固有一時フォルダーを保持する。"""

    def __init__(self, regular=None, bold=None):
        """通常・太字の2書体を準備し、matplotlibに登録する。

        検出→TTCの展開→登録の順に、ワーカーの初期化時だけ実行する。
        両書体の準備後は、描画側でfontweightを指定するだけで使い分けられる。

        Args:
            regular (pathlib.Path | None): 通常書体のTTF/OTF/TTC。
                省略時はインストール済みのメイリオを探す。
            bold (pathlib.Path | None): 同じファミリーの太字書体。
                メイリオなら省略時にmeiryob.ttcまたは登録済み太字を探す。
                他のファミリーを明示指定する場合は太字も指定する。

        Raises:
            RuntimeError: メイリオが未導入、または太字書体が見つからない場合。
            ValueError: TTCに対象書体がない、太字のファミリーが異なる、
                または太字ファイルが通常書体だった場合。
            OSError: フォントを読み込めない場合。
        """
        self._temporary = None
        self._registered = []
        try:
            if regular is None:
                regular = self._installed(False)
                if regular is None:
                    raise RuntimeError(
                        "メイリオが見つかりません。--font meiryo.ttc --font-bold meiryob.ttcを指定してください"
                    )
            regular = Path(regular).resolve()
            self.regular = self._prepare(regular, False)
            self.family = font_manager.FontProperties(
                fname=str(self.regular)
            ).get_name()
            if bold is None and self.family == "Meiryo":
                sibling = regular.with_name("meiryob.ttc")
                bold = sibling if sibling.is_file() else self._installed(True)
                if bold is None:
                    raise RuntimeError(
                        "メイリオの太字が見つかりません。--font-bold meiryob.ttcを指定してください"
                    )
            if bold is None:
                raise RuntimeError("太字書体を--font-boldで指定してください")
            self.bold = self._prepare(Path(bold).resolve(), True)
            with TTFont(self.bold) as face:
                if face["name"].getBestFamilyName() != self.family or not _is_bold(
                    face
                ):
                    raise ValueError(
                        "通常書体と同じファミリーの太字ファイルを指定してください"
                    )
            for path in (self.regular, self.bold):
                font_manager.fontManager.addfont(str(path))
                self._registered.append(font_manager.fontManager.ttflist[-1])
            # 同名の別バージョンが登録済みでも、今回指定された実ファイルを優先する。
            # 複数サービスが同じプロセス内で使われる場合にも書体が混在しないようにする。
            entries = font_manager.fontManager.ttflist
            entries[:] = self._registered + entries[:-2]
            _clear_cache()
        except Exception:
            self.close()
            raise

    @staticmethod
    def _installed(bold):
        """登録済み書体またはWindowsの標準フォント配置からメイリオを探す。

        Args:
            bold (bool): Trueなら太字、Falseなら通常書体を探す。

        Returns:
            pathlib.Path | None: 見つかったファイル。なければNone。
        """
        for entry in font_manager.fontManager.ttflist:
            weight = font_manager.weight_dict.get(entry.weight, entry.weight)
            if (
                entry.name == "Meiryo"
                and entry.style == "normal"
                and (weight >= 600) == bold
                and Path(entry.fname).is_file()
            ):
                return Path(entry.fname)
        windows = os.environ.get("WINDIR", "C:/Windows")
        candidate = Path(windows) / "Fonts" / ("meiryob.ttc" if bold else "meiryo.ttc")
        return candidate if candidate.is_file() else None

    def _prepare(self, path, bold):
        """TTCからMeiryoの指定書体を取り出し、TTF/OTFはそのまま使う。

        Args:
            path (pathlib.Path): 入力フォントの絶対パス。
            bold (bool): Trueなら太字、Falseなら通常書体を選ぶ。

        Returns:
            pathlib.Path: matplotlibで使用するTTF/OTF。

        Raises:
            ValueError: TTCに指定したMeiryo書体がない場合。
        """
        if path.suffix.lower() != ".ttc":
            return path
        # Meiryo UIや斜体を選ばない。書体番号に依存せず名前・太さで選ぶ。
        collection = TTCollection(path)
        try:
            for face in collection.fonts:
                style = face["OS/2"].fsSelection
                if (
                    face["name"].getBestFamilyName() == "Meiryo"
                    and not style & 1
                    and _is_bold(face) == bold
                ):
                    if self._temporary is None:
                        self._temporary = TemporaryDirectory(prefix="report-font-")
                    output = Path(self._temporary.name) / (
                        "Meiryo-Bold.ttf" if bold else "Meiryo-Regular.ttf"
                    )
                    face.save(output)
                    return output
            raise ValueError(
                f'TTCにMeiryoの{"太字" if bold else "通常"}書体がありません: {path.name}'
            )
        finally:
            collection.close()

    def close(self):
        """登録を解除して一時フォントを削除する。ワーカー終了時に呼ぶ。"""
        # 今回追加した登録だけを外す。同じファイルの既存登録は保持する。
        registered = {id(entry) for entry in self._registered}
        entries = font_manager.fontManager.ttflist
        entries[:] = [entry for entry in entries if id(entry) not in registered]
        self._registered.clear()
        _clear_cache()
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None
