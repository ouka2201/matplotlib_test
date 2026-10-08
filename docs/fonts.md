# メイリオの設定
フォント処理は`services/font_service.py`の`ReportFonts`にまとめています。各ワーカーの開始時に一度だけ「通常・太字の選択 → TTCの展開 → matplotlibへの登録」を行い、終了時に`close()`で追加登録と一時ファイルを片付けます。
Windowsでは`meiryo.ttc`・`meiryob.ttc`を自動検出します。通常書体を指定した場合、同じフォルダーの`meiryob.ttc`も探します。別の場所にある場合は`--font-bold`を指定してください。
```bash
python main.py --csv examples/sample.csv --font C:/Windows/Fonts/meiryo.ttc --font-bold C:/Windows/Fonts/meiryob.ttc --output output/report.pdf
```
TTCには複数書体が入っているため、Meiryo RegularとMeiryo Boldだけを取り出します。Meiryo UI・斜体は選びません。展開する場合だけワーカー固有の一時フォルダーを使い、フォント本体はソースに同梱しません。
通常書体と太字書体を初期化時に確認します。メイリオがない場合や、太字がない・別ファミリーの場合はエラーで通知します。他のTTF/OTFを使う場合は、通常と太字を両方指定してください。
描画側では`fontweight="normal"`または`fontweight="bold"`を指定するだけです。文字ごとの太字検出と、輪郭を重ねて太字に見せる処理は削除しました。
文字はすべてmatplotlibでページPNGに含めています。Jinja2のHTMLにはPNGだけを渡すため、フォントのbase64化・@font-face・ブラウザー側のフォント待機は不要です。
単体・並列のCLI引数は従来どおり`--font`と`--font-bold`を使用できます。No.0〜No.7の編集先も変わりません。
