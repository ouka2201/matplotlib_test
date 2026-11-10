"""LMMVMV-API-02の項番別データ準備。"""
if __package__:
    from .api_screen_case_runner import main
else:
    from api_screen_case_runner import main

if __name__ == "__main__":
    raise SystemExit(main("api02"))
