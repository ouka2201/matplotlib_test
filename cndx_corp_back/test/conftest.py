from unittest.mock import MagicMock

import pytest

import cndx_corp_back as app_module

# pytest経由で読み込む場合、create_app が実行されないため
# engine / SessionLocal / Base が定義されず ImportError になる。
# テスト内でダミーの値をセットしておくことで import を成立させる。
setattr(app_module, "engine", MagicMock())
setattr(app_module, "SessionLocal", MagicMock())
setattr(app_module, "Base", MagicMock())

from cndx_corp_back import create_app, db  # noqa: E402


@pytest.fixture
def app():
    app = create_app("testing")
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_session(app):
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()
