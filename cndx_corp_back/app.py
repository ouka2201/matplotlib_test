from cndx_corp_back import create_app

# import sys
# print(sys.path)
# sys.path.remove("C:\\Users\\msduser\\sprint1_back\\cndx_corp_back")
app = create_app(config_name="localtest")

if __name__ == "__main__":
    app.run(
        # 外部からアクセス可能にする場合はコメントアウトを外す
        host="0.0.0.0",
        debug=True,
    )
