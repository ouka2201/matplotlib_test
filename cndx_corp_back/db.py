# cndx_corp_back/db.py
from flask import current_app


def get_db():
    return current_app.extensions["sqlalchemy"]
