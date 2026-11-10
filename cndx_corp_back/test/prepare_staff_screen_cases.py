"""担当者設定情報管理画面の項番別データ準備。"""
if __package__:
    from .api_screen_case_runner import main
else:
    from api_screen_case_runner import main

if __name__ == "__main__":
    raise SystemExit(main("staff_screen"))
