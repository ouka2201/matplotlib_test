from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from cndx_corp_back.common.constants_values import FormatTypeCode, SiteSelectionType
from cndx_corp_back.dto.report.cn_karte_create_vis_in_dto import (
    CreateCnKarteVisInDto,
    GroupFilterDto,
)


class MultiConditionDto(BaseModel):
    # 企業全体の選択有無
    entire_company: Optional[bool] = Field(default=False, alias="entireCompany")
    # グループ選択の有無
    group_option: Optional[bool] = Field(default=False, alias="groupOption")
    # グループの詳細選択（任意）
    group_items: Optional[List[GroupFilterDto]] = Field(
        default=None, alias="groupItems"
    )


class DownloadsDto(BaseModel):
    # 欠損一覧の出力有無
    missing_data_pdf: bool = Field(default=False, alias="missingData")
    # バックデータ（CSV）の出力有無
    report_back_csv: bool = Field(default=False, alias="cnKarteCsv")
    # KPI一覧（CSV）の出力有無
    kpi_csv: bool = Field(default=False, alias="kpi")


# --- ターゲット種別 → コード（DB保存用） ---
_TARGET_TYPE_CODE_MAP = {
    "企業全体": SiteSelectionType.ALL.value,
    "グループ": SiteSelectionType.GROUP.value,
    "個別": SiteSelectionType.SINGLE.value,
}


# --- フォーマット種別（CNカルテ） → コード（DB保存用） ---
# 画面側は「CNカルテ(簡易版) / CNカルテ(標準版)」等の表記想定。
# 全角かっこ・半角かっこ表記ゆれに配慮し、DTO内で正規化してからマップ。
def _normalize_label(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.replace("(", "（").replace(")", "）").strip()


_SIMPLE_CODE = "00"
_STANDARD_CODE = "01"

_SIMPLE_KEYS = {
    FormatTypeCode.SIMPLE.value,
    _SIMPLE_CODE,
    "0",
    "00",
}

_STANDARD_KEYS = {
    FormatTypeCode.STANTARD.value,
    _STANDARD_CODE,
    "1",
    "01",
}

_REPORT_TYPE_CODE_MAP = {
    _normalize_label("CNカルテ(簡易版)"): _SIMPLE_CODE,
    _normalize_label("CNカルテ（簡易版）"): _SIMPLE_CODE,
    _normalize_label("簡易版"): _SIMPLE_CODE,
    _normalize_label("CNカルテ(標準版)"): _STANDARD_CODE,
    _normalize_label("CNカルテ（標準版）"): _STANDARD_CODE,
    _normalize_label("標準版"): _STANDARD_CODE,
    _normalize_label("00"): _SIMPLE_CODE,
    _normalize_label("0"): _SIMPLE_CODE,
    _normalize_label("01"): _STANDARD_CODE,
    _normalize_label("1"): _STANDARD_CODE,
}


class CreateCnKarteVisExtendedDto(CreateCnKarteVisInDto):
    """
    CreateCnKarteVisInDto を拡張し、後続処理で使用する追加パラメータを補完する DTO
    """

    # 生成一意ID（サービス側で上書き可能）
    creation_id: Optional[str] = None
    # 人間可読なレポート種別名（例：CNカルテ（簡易版））
    report_type: Optional[str] = None
    # 人間可読な対象種別名（例：企業全体 / グループ / 個別）
    target_type: Optional[str] = None
    # マルチ条件
    multi_condition: Optional[MultiConditionDto] = None
    # ダウンロード指定
    downloads: Optional[DownloadsDto] = None

    # --- 追加：DB登録用のコード項目 ---
    # 対象種別コード（01=企業全体, 02=グループ, 03=個別）
    site_selection_type_code: Optional[str] = None
    # フォーマット種別コード（00=簡易版, 01=標準版）
    format_type_code: Optional[str] = None

    # === 追加（内部利用のみ）========================================
    # グループ作成時に m_building に作成した「仮想拠点」の building_id を保持する
    # - 入力JSONで渡す必要はない（サービス側で設定する）
    # - t_report_storage_info 登録時、"GROUP" などの代表IDの代わりにここを使う
    virtual_group_building_id: Optional[str] = None
    # =============================================================

    @model_validator(mode="after")
    def enrich_missing_fields(self):
        """
        受領値の不足分を補完し、DB登録用のコードも同時に算出する。
        """
        # --- 対象種別（target_type）を補完 ---
        if not self.target_type:
            if getattr(self, "is_for_multibuilding", False) and getattr(
                self, "group_for_multibuilding", None
            ):
                self.target_type = "グループ"
            elif getattr(self, "is_for_multibuilding", False):
                self.target_type = "企業全体"
            else:
                self.target_type = "個別"

        # --- レポート種別（report_type）を補完 ---
        # creation_format の表記ゆれ（半角/全角かっこ）を吸収して正規化してから判定
        def _normalize(s: Optional[str]) -> str:
            if not s:
                return ""
            return s.replace("(", "（").replace(")", "）").strip()

        if self.report_type:
            normalized_report_type = _normalize(self.report_type)
            if normalized_report_type in _SIMPLE_KEYS:
                self.report_type = "CNカルテ（簡易版）"
            elif normalized_report_type in _STANDARD_KEYS:
                self.report_type = "CNカルテ（標準版）"
            else:
                self.report_type = normalized_report_type

        if not self.report_type:
            cf = _normalize(getattr(self, "creation_format", ""))
            if cf in _SIMPLE_KEYS or "簡易" in cf:
                self.report_type = "CNカルテ（簡易版）"
            elif cf in _STANDARD_KEYS or "標準" in cf:
                self.report_type = "CNカルテ（標準版）"
            else:
                # 不明時は UNKNOWN とする（DBにはコード未設定にしないため、後段でデフォルトを与える）
                self.report_type = "UNKNOWN"

        # --- creation_id を補完 ---
        if not self.creation_id:
            self.creation_id = f"system_{datetime.now().timestamp()}"

        # --- downloads を補完 ---
        if not self.downloads:
            self.downloads = DownloadsDto()

        # --- DB登録用：対象種別コードを算出 ---
        if not self.site_selection_type_code:
            self.site_selection_type_code = _TARGET_TYPE_CODE_MAP.get(
                self.target_type, "03"
            )  # 既定=個別

        # --- DB登録用：フォーマット種別コードを算出 ---
        if self.format_type_code:
            normalized_code = _normalize(self.format_type_code)
            if normalized_code in _SIMPLE_KEYS:
                self.format_type_code = _SIMPLE_CODE
            elif normalized_code in _STANDARD_KEYS:
                self.format_type_code = _STANDARD_CODE
            else:
                self.format_type_code = None

        if not self.format_type_code:
            normalized_report_type = _normalize(self.report_type)
            # report_type を正としてコード化（簡易/標準 いずれでも判定可）
            self.format_type_code = _REPORT_TYPE_CODE_MAP.get(normalized_report_type)

            if not self.format_type_code:
                # 直接 creation_format からも念のため判定
                cf = _normalize(getattr(self, "creation_format", ""))
                if "簡易" in cf:
                    self.format_type_code = _SIMPLE_CODE
                    if not self.report_type or self.report_type == "UNKNOWN":
                        self.report_type = "CNカルテ（簡易版）"
                elif "標準" in cf:
                    self.format_type_code = _STANDARD_CODE
                    if not self.report_type or self.report_type == "UNKNOWN":
                        self.report_type = "CNカルテ（標準版）"
                else:
                    # 不明時は簡易に倒す
                    self.format_type_code = _SIMPLE_CODE
                    if not self.report_type or self.report_type == "UNKNOWN":
                        self.report_type = "CNカルテ（簡易版）"
                self.report_type = _normalize(self.report_type)
            else:
                self.report_type = normalized_report_type

        return self
