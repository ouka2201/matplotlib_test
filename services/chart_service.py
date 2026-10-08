"""PNGをBytesIOで生成し、HTML埋込み用のdata URIを返す。"""

import base64
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from services.font_service import ReportFonts
from rendering.pages.first_page import draw_first_page
from rendering.pages.second_page import draw_second_page


class ChartService:
    """日本語のグラフと帳票ページをPNGへ変換するサービス。

    Attributes:
        output_dir (pathlib.Path | None): PNGの任意保存先。Noneなら画像ファイルを作成しない。
        png_bytes (dict[str, bytes]): 処理中の画像。レポートごとにクリアする。
    """

    def __init__(self, output_dir=None, font=None, bold_font=None):
        """PNGの出力先と、日本語を描画するフォントを設定する。

        matplotlibの全体設定を変更する。複数顧客の帳票を並列生成する
        場合は、ワーカーごとにプロセスを分ける。

        Args:
            output_dir (str | pathlib.Path | None): デバッグ用の任意保存先。既定はメモリのみ。
            font (pathlib.Path | None): 通常書体のTTF/OTF/TTC。省略時はメイリオを検出する。
            bold_font (pathlib.Path | None): 同じファミリーの太字書体。

        Raises:
            RuntimeError: メイリオの通常書体・太字書体を検出できない場合。
            OSError: 出力先の作成または指定フォントの読み込みに失敗した場合。
        """
        self.output_dir = Path(output_dir) if output_dir is not None else None
        if self.output_dir is not None:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        self.png_bytes = {}
        self.fonts = ReportFonts(font, bold_font)
        plt.rcParams.update(
            {
                "font.family": self.fonts.family,
                "font.size": 8,
                "axes.unicode_minus": False,
                "axes.spines.top": False,
                "axes.spines.right": False,
                "axes.edgecolor": "#b8c6c8",
                "axes.labelcolor": "#45565b",
                "xtick.color": "#45565b",
                "ytick.color": "#45565b",
            }
        )

    def save(self, name, fig):
        """Figureを白背景のPNGとして保存し、HTML用の画像URIを返す。

        BytesIOへ190dpiで描画する。output_dir指定時だけファイルにも保存する。保存に失敗した場合もFigureを閉じるため、
        呼び出し後に同じFigureを再利用しないこと。

        Args:
            name (str): PNGのファイル名（拡張子を除く）。
            fig (matplotlib.figure.Figure): 保存対象のFigure。保存後に閉じる。

        Returns:
            str: data:image/png;base64,で始まる画像のdata URI。

        Raises:
            OSError: PNGの保存または読み込みに失敗した場合。
        """
        try:
            # PNGをメモリへ描画する。getvalueでbytesを取り出した後、バッファはwithで閉じる。
            with BytesIO() as buffer:
                fig.savefig(buffer, format="png", dpi=190, facecolor="white")
                data = buffer.getvalue()
            # 完成ページのPNGだけを保持する。各No.の中間PNGは生成しない。
            # HTMLへ渡すときはbase64のdata URIにするので、画像パスは不要。
            self.png_bytes[name] = data
            if self.output_dir is not None:
                (self.output_dir / f"{name}.png").write_bytes(data)
            return "data:image/png;base64," + base64.b64encode(data).decode("ascii")
        finally:
            plt.close(fig)

    def create_all(self, s, config, context=None):
        """全No.をページへ直接描画し、完成した2ページだけをPNG化する。

        各No.の文字・図形・グラフを同じページFigureへ描画する。
        contextがなければ集計処理で作る。

        Args:
            s (dict): build_contextが返すseries。全枠・日別・月別・週別・TOP50の集計データ。
            config (dict): 契約情報と対象月の設定。customer_name、address、
                customer_number、contract_kw、target_monthを用途に応じて使用する。
                issuer、holidays、is_sampleは任意設定。
            context (dict | None): build_contextが返す表示用の値。create_allでは省略時に生成する。

        Returns:
            dict[str, str]: 画像名をキー、PNGのdata URIを値とする辞書。
                first_page・second_pageのみ。文字や説明欄を含むページ全体の画像。

        Raises:
            ValueError: 契約情報や説明文を画像内に読める大きさで収められない場合。
            OSError: PNGの保存または読み込みに失敗した場合。
        """
        # 再利用するサービスに前の顧客の画像を残さない。
        self.png_bytes.clear()
        images = {}
        # 各グラフはページFigure内へ直接描き、使用しない個別PNGの二重生成を避ける。
        images["first_page"] = self.save("first_page", draw_first_page(s, config))
        if context is None:
            from services.data_service import build_context

            context, _ = build_context(s["df"], config)
        images["second_page"] = self.save(
            "second_page", draw_second_page(s, config, context)
        )
        return images
