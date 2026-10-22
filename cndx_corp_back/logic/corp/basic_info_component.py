from flask import abort, current_app
from sqlalchemy import and_, case, collate, func, or_, select

from cndx_corp_back.common.database_manager import (
    get_scoped_session,
    update_entity_fields,
)
from cndx_corp_back.common.decorators import component, controller, jwt_user_context_db
from cndx_corp_back.dto.corp.basic_info_in_post_dto import BasicInfoInPostDto
from cndx_corp_back.dto.corp.basic_info_list_out_get_dto import (
    CorpBasicInfoOutGetDto as OutDto,
)
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_consent_route_info_entity import MConsentRouteInfo
from cndx_corp_back.entity.m_corporate_basic_entity import MCorporateBasic
from cndx_corp_back.entity.m_corporate_details_info_entity import (
    MCorporateDetailsInfo,
)
from cndx_corp_back.entity.m_jp_st_industry_classification_entity import (
    MJpStIndustryClassification,
)
from cndx_corp_back.entity.m_prefecture_entity import PrefectureMst
from cndx_corp_back.entity.m_staff_info_entity import MStaffInfo
from cndx_corp_back.entity.m_user_organization_info_entity import MUserOrganizationInfo


class CorpBuildingInfoComponent:

    @component
    def get(
        self,
        request_dict: dict,
        login_org_id,
        org_type_code,
        role_id,
        user_id,
        logger=None,
    ) -> list:
        if logger is None:
            logger = current_app.logger

        rows = None
        try:
            with get_scoped_session() as session:
                stmt = (
                    select(
                        MCorporateDetailsInfo.corporate_number,
                        # MCorporateDetailsInfo.agreement_category,
                        # MConsentRouteInfo.agreement_name,
                        # MBuilding.agreement_org.label("org_id"),
                        MCorporateBasic.company_name,
                        func.concat(
                            PrefectureMst.pref_nm,
                            MCorporateBasic.company_address_city,
                        ).label("company_address"),
                        MCorporateDetailsInfo.industry_class_major_name,
                        MCorporateDetailsInfo.industry_class_middle_name,
                        MCorporateDetailsInfo.industry_class_minor_name,
                        MCorporateDetailsInfo.industry_class_detail_name,
                        MCorporateDetailsInfo.business_office_count,
                    )
                    # .filter_by(**request_dict)
                    .filter_by(corporate_number=request_dict.get("corporate_number"))
                    .filter(MCorporateDetailsInfo.delete_flg.isnot(True))
                    .outerjoin(
                        MCorporateBasic,
                        MCorporateBasic.corporate_number
                        == MCorporateDetailsInfo.corporate_number,
                    )
                    # .outerjoin(
                    #     MConsentRouteInfo,
                    #     MCorporateDetailsInfo.agreement_category
                    #     == MConsentRouteInfo.agreement_category,
                    # )
                    .outerjoin(
                        PrefectureMst,
                        PrefectureMst.pref_cd
                        == MCorporateBasic.company_address_prefecture,
                    )
                    .distinct(
                        MCorporateDetailsInfo.corporate_number,
                        MCorporateDetailsInfo.agreement_category,
                        MBuilding.agreement_org,
                    )
                    .order_by(MCorporateDetailsInfo.agreement_category)
                )

                vis_category_dict = {
                    "ASE": "12",
                    "ZRB": "13",
                    "JFS": "14",
                }
                # if org_type_code == "06":
                #     stmt = stmt.filter(agreement_category=vis_category_dict.get(login_org_id))

                if request_dict.get("agreement_category") is not None:
                    stmt = stmt.filter(
                        agreement_category=request_dict.get("agreement_category"),
                        # org_id=request_dict.get("org_id"),
                    )

                staff_aggrement_category = self.get_staff_agreement_category(
                    session, user_id, request_dict.get("corporate_number"), login_org_id
                )
                if org_type_code == "01":
                    if role_id == "0":
                        stmt = (
                            stmt.add_columns(
                                MBuilding.agreement_category.label(
                                    "agreement_category"
                                ),
                                MConsentRouteInfo.agreement_name,
                                MBuilding.agreement_org.label("org_id"),
                                MUserOrganizationInfo.org_name.label("org_name"),
                            )
                            .outerjoin(
                                MBuilding,
                                and_(
                                    MCorporateDetailsInfo.agreement_category
                                    == MBuilding.agreement_category,
                                    MCorporateDetailsInfo.corporate_number
                                    == MBuilding.corporate_number,
                                    MCorporateDetailsInfo.org_id == MBuilding.org_id,
                                    MBuilding.delete_flg.is_(False),
                                ),
                            )
                            .outerjoin(
                                MUserOrganizationInfo,
                                and_(
                                    MBuilding.agreement_org
                                    == MUserOrganizationInfo.org_id,
                                    MUserOrganizationInfo.delete_flg.is_(False),
                                ),
                            )
                            .outerjoin(
                                MConsentRouteInfo,
                                MBuilding.agreement_category
                                == MConsentRouteInfo.agreement_category,
                            )
                        )
                    elif role_id == "1":
                        agreement_category_expr = case(
                            (
                                and_(
                                    MCorporateDetailsInfo.agreement_category == "01",
                                    MStaffInfo.user_id == user_id,
                                ),
                                MStaffInfo.agreement_category,
                            ),
                            (
                                MCorporateDetailsInfo.agreement_category != "01",
                                MCorporateDetailsInfo.agreement_category,
                            ),
                        )
                        stmt = (
                            stmt.add_columns(
                                case(
                                    (
                                        and_(
                                            MCorporateDetailsInfo.agreement_category
                                            == "01",
                                            MStaffInfo.user_id == user_id,
                                        ),
                                        MStaffInfo.agreement_category,
                                    ),
                                    (
                                        MCorporateDetailsInfo.agreement_category
                                        != "01",
                                        MCorporateDetailsInfo.agreement_category,
                                    ),
                                ).label("agreement_category"),
                                MConsentRouteInfo.agreement_name,
                                MBuilding.agreement_org.label("org_id"),
                                MUserOrganizationInfo.org_name.label("org_name"),
                            )
                            .outerjoin(
                                MStaffInfo,
                                and_(
                                    MCorporateDetailsInfo.corporate_number
                                    == MStaffInfo.corporate_number,
                                    MCorporateDetailsInfo.agreement_category
                                    == MStaffInfo.agreement_category,
                                    MStaffInfo.delete_flg.is_(False),
                                ),
                            )
                            .outerjoin(
                                MBuilding,
                                and_(
                                    MStaffInfo.agreement_category
                                    == MBuilding.agreement_category,
                                    MStaffInfo.corporate_number
                                    == MBuilding.corporate_number,
                                    MBuilding.delete_flg.is_(False),
                                ),
                            )
                            .outerjoin(
                                MUserOrganizationInfo,
                                and_(
                                    MBuilding.agreement_org
                                    == MUserOrganizationInfo.org_id,
                                    MUserOrganizationInfo.delete_flg.is_(False),
                                ),
                            )
                            .outerjoin(
                                MConsentRouteInfo,
                                and_(
                                    MConsentRouteInfo.agreement_category
                                    == agreement_category_expr,
                                    MConsentRouteInfo.delete_flg.is_(False),
                                ),
                            )
                            .filter(
                                or_(
                                    MCorporateDetailsInfo.agreement_category != "01",
                                    and_(
                                        MCorporateDetailsInfo.agreement_category
                                        == "01",
                                        MStaffInfo.user_id == user_id,
                                        MStaffInfo.delete_flg.is_(False),
                                    ),
                                )
                            )
                        )

                if org_type_code in ("02", "03", "04", "05"):
                    stmt = stmt.add_columns(
                        MStaffInfo.agreement_category.label("agreement_category"),
                        MConsentRouteInfo.agreement_name,
                        MBuilding.agreement_org.label("org_id"),
                        MUserOrganizationInfo.org_name.label("org_name"),
                    )
                    if role_id == "0":
                        stmt = stmt.join(
                            MStaffInfo,
                            and_(
                                MCorporateDetailsInfo.corporate_number
                                == MStaffInfo.corporate_number,
                                MCorporateDetailsInfo.agreement_category
                                == MStaffInfo.agreement_category,
                            ),
                        ).filter(
                            MStaffInfo.org_id == login_org_id,
                            MStaffInfo.delete_flg.is_(False),
                        )
                    elif role_id == "1":
                        stmt = stmt.join(
                            MStaffInfo,
                            and_(
                                MCorporateDetailsInfo.corporate_number
                                == MStaffInfo.corporate_number,
                                MCorporateDetailsInfo.agreement_category
                                == MStaffInfo.agreement_category,
                            ),
                        ).filter(
                            MStaffInfo.user_id == user_id,
                            MStaffInfo.delete_flg.is_(False),
                        )
                    elif role_id == "9":
                        mUserOrganizationInfo = select(
                            MUserOrganizationInfo.org_id,
                        ).where(
                            MUserOrganizationInfo.parent_org_id == login_org_id,
                            MUserOrganizationInfo.delete_flg.is_(False),
                        )
                        stmt = stmt.outerjoin(
                            MStaffInfo,
                            and_(
                                MCorporateDetailsInfo.corporate_number
                                == MStaffInfo.corporate_number,
                                MCorporateDetailsInfo.agreement_category
                                == MStaffInfo.agreement_category,
                            ),
                        ).filter(
                            or_(
                                MStaffInfo.org_id.in_(mUserOrganizationInfo),
                                MStaffInfo.org_id == login_org_id,
                            ),
                            MStaffInfo.delete_flg.is_(False),
                        )
                    if org_type_code in ["02", "03"]:
                        stmt = stmt.join(
                            MBuilding,
                            and_(
                                MStaffInfo.agreement_category
                                == MBuilding.agreement_category,
                                MStaffInfo.corporate_number
                                == MBuilding.corporate_number,
                                MStaffInfo.org_id == MBuilding.agreement_org,
                                MBuilding.delete_flg.is_(False),
                            ),
                        )
                    else:
                        stmt = stmt.outerjoin(
                            MBuilding,
                            and_(
                                MStaffInfo.agreement_category
                                == MBuilding.agreement_category,
                                MStaffInfo.corporate_number
                                == MBuilding.corporate_number,
                                MBuilding.delete_flg.is_(False),
                            ),
                        )

                    stmt = stmt.outerjoin(
                        MUserOrganizationInfo,
                        and_(
                            MBuilding.agreement_org == MUserOrganizationInfo.org_id,
                            MUserOrganizationInfo.delete_flg.is_(False),
                        ),
                    ).outerjoin(
                        MConsentRouteInfo,
                        MStaffInfo.agreement_category
                        == MConsentRouteInfo.agreement_category,
                    )

                if org_type_code == "06":
                    stmt = (
                        stmt.add_columns(
                            MCorporateDetailsInfo.agreement_category.label(
                                "agreement_category"
                            ),
                            MConsentRouteInfo.agreement_name,
                            MBuilding.agreement_org.label("org_id"),
                            MUserOrganizationInfo.org_name.label("org_name"),
                        )
                        .outerjoin(
                            MBuilding,
                            and_(
                                MCorporateDetailsInfo.corporate_number
                                == MBuilding.corporate_number,
                                MBuilding.delete_flg.is_(False),
                            ),
                        )
                        .outerjoin(
                            MUserOrganizationInfo,
                            and_(
                                MBuilding.agreement_org == MUserOrganizationInfo.org_id,
                                MUserOrganizationInfo.delete_flg.is_(False),
                            ),
                        )
                        .outerjoin(
                            MConsentRouteInfo,
                            MCorporateDetailsInfo.agreement_category
                            == MConsentRouteInfo.agreement_category,
                        )
                        .filter(
                            MCorporateDetailsInfo.agreement_category
                            == vis_category_dict.get(login_org_id),
                            MBuilding.agreement_org == login_org_id,
                            # MStaffInfo.user_id == user_id,
                            MStaffInfo.delete_flg.is_(False),
                        )
                    )

                subq = stmt.order_by(
                    MCorporateDetailsInfo.corporate_number,
                    MCorporateDetailsInfo.agreement_category,
                    MBuilding.agreement_org,
                ).subquery()

                final_stmt = select(subq).order_by(subq.c.org_name.collate("C"))

                rows = session.execute(final_stmt).mappings().all()

        except Exception as e:
            logger.error("データベース接続失敗")
            abort(500)

        order_map = {
            "01": 1,  # 地銀
            "02": 2,  # EP・TCS・REP
            "00": 3,  # 同意書未取得
        }

        if rows is None:
            return []
        else:
            # agreement_categoryが"00"同意書未取得、かつorg_idが"NONE"の場合は、org_nameを"同意書未取得"に固定して返す
            results = []
            for row in rows:
                row_dict = dict(row)
                row_org_id = row_dict.get("org_id")
                if row_dict.get("agreement_category") == "00" and (
                    not row_org_id or row_org_id == "dummy"
                ):
                    row_dict["org_name"] = "同意書未取得"
                    row_dict["org_id"] = "dummy"
                results.append(row_dict)

            results.sort(key=lambda x: order_map.get(x.get("agreement_category"), 99))

            return results

    @component
    # 企業基本情報の更新ロジック（POST処理）
    def post(self, request_dict: dict, user_id, org_id, logger=None):
        # ロガーが未指定の場合はアプリ既定のロガーを使用
        if logger is None:
            # Flaskアプリケーションのロガーをセット
            logger = current_app.logger

        # 入力パラメータのバリデーションを試行
        try:
            # DTOで検証し、Python辞書へ変換
            checked = BasicInfoInPostDto.model_validate(request_dict).model_dump()
        # バリデーション失敗時の例外ハンドリング
        except Exception as e:
            # 入力不備をエラーログに記録
            logger.error("リクエストのパラメータ不備")
            # 例外をそのまま呼び出し元へ送出
            raise e

        # DB検索用の条件ディクショナリを初期化
        cond = {}
        # 条件: 企業番号
        cond["corporate_number"] = checked["corporate_number"]
        # 条件: 契約区分
        cond["agreement_category"] = checked["agreement_category"]
        # 条件: 組織ID
        # cond["org_id"] = org_id

        # TODO フロント側Headerの不具合により一時的にコメントアウト
        # リクエストに基づき、編集者を設定するための準備
        # checked["updated_by"] = user_info["email"]  # 編集者メール（将来的に有効化）

        # TODO TEPなどの権限制御時、user_info に基づいて絞り込みを行う

        # DBトランザクション処理開始
        try:
            # コンテキスト管理でセッション（トランザクション）を開始
            with get_scoped_session() as session:
                # 条件に一致する企業詳細レコードを1件取得
                d_info = session.query(MCorporateDetailsInfo).filter_by(**cond).first()

                # 業種マスタから入力の細分類コードに該当するレコードを取得
                industry = (
                    session.query(MJpStIndustryClassification).filter_by(
                        # フィルタ条件（細分類コード）
                        industry_code=checked["industry_class_detail_code"],
                    )
                    # 最初の1件を取得
                    .first()
                )

                # マスタに一致が無い場合の分岐
                if industry is None:
                    # 存在しない旨をログ出力
                    logger.error("細分類番号が存在しない。")
                    # サーバエラー（500）で処理を中断
                    abort(500)

                # マスタから大分類名を補完
                checked["industry_class_major_name"] = industry.division_name
                # マスタから中分類名を補完
                checked["industry_class_middle_name"] = industry.major_group_name
                # マスタから小分類名を補完
                checked["industry_class_minor_name"] = industry.group_name
                # マスタから細分類名を補完
                checked["industry_class_detail_name"] = industry.industry_name
                checked["updated_by"] = user_id  # 編集者メール（将来的に有効化）
                checked["org_id"] = "TEP"

                # 入力値をエンティティへ反映（差分更新）
                update_entity_fields(d_info, checked)
                # 変更をコミット（確定）
                session.commit()

        # DB更新処理全体のエラーハンドリング
        except Exception as e:
            # 失敗内容をエラーログに記録
            logger.error(f"企業情報更新失敗: {str(e)}")
            # サーバエラー（500）を返却
            abort(500)

    def get_staff_agreement_category(self, session, user_id, corporate_number, org_id):
        stmt = select(MStaffInfo.agreement_category).where(
            and_(
                MStaffInfo.user_id == user_id,
                MStaffInfo.corporate_number == corporate_number,
                MStaffInfo.org_id == org_id,
                MStaffInfo.delete_flg.is_(False),
            )
        )

        return session.execute(stmt).scalar()
