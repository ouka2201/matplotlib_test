from cndx_corp_back import db
from cndx_corp_back.common.decorators import service
from cndx_corp_back.common.load_master import get_mst_data, load_mst_data


class MstDataManageService:
    """
    マスタデータ管理サービス
    """

    @service
    def refresh(self, logger=None):
        """マスタデータを再読込"""

        load_mst_data(db.engine)

    @service
    def inquiry(self, request_dict, logger=None):
        """マスタデータを取得"""

        return get_mst_data(**request_dict)
