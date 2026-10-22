import os
from re import match

import pandas as pd
from flask import abort, current_app
from werkzeug.exceptions import HTTPException

import cndx_corp_back.logic.EBMG_BaseEnergy.delete_logic as DeleteLogic
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import service
from cndx_corp_back.dto.EBMG.energy_delete_in_dto import (
    EnergyDeleteIn,
)


class BaseEnergyDeleteService:

    @service
    def delete_building_info(self, indto: EnergyDeleteIn, org_id, user_id, logger=None):

        # DTOからDataFrameへ変換
        df = DeleteLogic.dto_to_df(indto)

        with get_scoped_session() as session:
            # 登録処理
            try:
                # 一括UPDATE
                DeleteLogic.delete_input_data(session, df, org_id, user_id)
                session.commit()
            except HTTPException as e:
                raise
            except Exception as e:
                raise
