from dataclasses import asdict

from cndx_corp_back import db  # noqa
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.user_mst_entity import MUser
from cndx_corp_back.utils.utils import get_current_timestamp


class UserInsertComponent:
    @component
    def insert_user(self, user_dto, logger=None):
        """
        ユーザ情報登録を処理する
        """
        # 現在日時
        current_timestamp = get_current_timestamp()

        # ダミーデータを1万件作成
        user_entities = []

        for i in range(10000):
            user_data = {
                "user_id": f"user{i}@example.com",
                "user_name": f"ユーザ{i}",
                "company_name": "地銀テスト",
                "department_id": f"{i:03d}",  # '001', '002'...
                "department_name": f"部署{i}",
                "user_password": f"Password@{i}",
                "org_id": f"org_{i%100:03d}",  # 分散例
                "user_role": "001",
                "start_date": "20250401",  # 日付型変換が必要なら後述
                "end_date": None,
                "delete_flg": False,
                "created_by": "wang",
                "created_at": current_timestamp,
                "updated_by": None,
                "updated_at": None,
            }

            user_entities.append(MUser(**user_data))

        # 一括登録
        db.session.add_all(user_entities)
        db.session.query(MUser).join()

        db.session.commit()

        return {"success": "ok"}
