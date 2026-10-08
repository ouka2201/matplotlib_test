"""No.0のタイトル・契約情報を、ページのmm座標へ直接描画する。"""

from matplotlib.patches import Rectangle
from rendering.styles import WIDTH

HEADER_BLUE = "#4f91b9"
LABEL_BLUE = "#4f91b9"
TEXT_COLOR = "#172b36"


def draw_no0(page, config):
    """No.0のタイトル帯と契約情報を、既存のページFigureに描画する。

    左上原点・mm単位で位置と寸法を指定する。契約値の文字幅を
    実測し、必要に応じて縮小する。Figureの作成・保存はページ側で行う。

    Args:
        page (FirstPageCanvas): 1ページ目の共通描画先。
        config (dict): customer_name、address、customer_number、contract_kwが必須。
            is_sampleがTrueの場合は「架空データ」を表示する。

    Raises:
        ValueError: 契約値が長すぎて5.4pt以上で収まらない場合。
        KeyError: 必須の契約設定がない場合。
    """
    canvas = page.canvas
    # タイトル帯と白い細線。寸法は完成した帳票上のmmで指定する。
    canvas.add_patch(
        Rectangle((0, -0.0075), 140.5, 18.8055, facecolor=HEADER_BLUE, edgecolor="none")
    )
    for y in (4.2909, 15.0369):
        canvas.add_patch(
            Rectangle((0, y), 140.5, 0.5373, facecolor="white", edgecolor="none")
        )
    canvas.text(
        70.25,
        10.1415,
        "電力使用状況見える化レポート",
        ha="center",
        va="center",
        fontsize=12.5,
        fontweight="bold",
        color="#101010",
    )
    rows = [
        ("ご契約名義", str(config["customer_name"])),
        ("ご契約住所", str(config["address"])),
        ("お客さま番号", str(config["customer_number"])),
        ("契約電力", f'{float(config["contract_kw"]):,.0f}kW'),
    ]
    value_texts = []
    # 青いラベルと契約値を対応させ、4行を同じ間隔で並べる。
    for index, (label, value) in enumerate(rows):
        top = 24.4695 + index * 7.5819
        canvas.add_patch(
            Rectangle(
                (7.7275, top), 23.1825, 7.1043, facecolor=LABEL_BLUE, edgecolor="none"
            )
        )
        canvas.text(
            8.8515,
            top + 3.55215,
            label,
            ha="left",
            va="center",
            fontsize=7.2,
            fontweight="bold",
            color="white",
        )
        value_texts.append(
            canvas.text(
                33.0175,
                top + 3.55215,
                value,
                ha="left",
                va="center",
                fontsize=7.7,
                fontweight="bold",
                color=TEXT_COLOR,
            )
        )
    if config.get("is_sample", False):
        canvas.text(
            136.9875,
            56.5284,
            "架空データ",
            ha="right",
            va="center",
            fontsize=5.2,
            color="#778d97",
        )

    # HTMLでは画像内の文字を検査できないため、右余白までの幅をここで実測する。
    page.fig.canvas.draw()
    renderer = page.fig.canvas.get_renderer()
    available_width = canvas.get_window_extent(renderer).width * 103.97 / WIDTH
    for text in value_texts:
        width = text.get_window_extent(renderer).width
        if width > available_width:
            size = text.get_fontsize() * available_width / width * 0.98
            if size < 5.4:
                raise ValueError(
                    "No.0の契約情報が長すぎます。値を短くするかno0_contract.pyの配置を調整してください"
                )
            text.set_fontsize(size)
