import base64
from io import BytesIO

import pandas as pd


def base64_to_excel(base64_data: str) -> pd.ExcelFile | str:
    """
    base64形式のデータをExcelファイルとして読み込み関数

    Args:
        base64_data (str): base64形式のデータ
    Returns:
        pandas.ExcelFile: 検証に成功した場合、読み込んだExcelFileオブジェクトを返す
        str: 検証に失敗した場合、エラーメッセージを返す
    """
    try:
        file_data = base64.b64decode(base64_data)
        excel_file = pd.ExcelFile(BytesIO(file_data))
        return excel_file
    except Exception as e:
        return f"ファイルの読込に失敗しました: {str(e)}"


def exists_sheet(excel_file: pd.ExcelFile, sheet_name: str) -> bool:
    """
    指定されたシートが存在するかを確認する関数

    Args:
        excel_file (pandas.ExcelFile): pandasのExcelFileオブジェクト
        sheet_name (str): シート名
    Returns:
        bool: シートが存在する場合はTrue、存在しない場合はFalseを返す
    raises:
        Any
    """
    return sheet_name in excel_file.sheet_names


def exists_sheet_like(excel_file: pd.ExcelFile, sheet_name: str) -> bool:
    """
    シート名が目標文字列を含めたシートが存在するかを確認する関数

    Args:
        excel_file (pandas.ExcelFile): pandasのExcelFileオブジェクト
        sheet_name (str): シート名
    Returns:
        bool: シートが存在する場合はTrue、存在しない場合はFalseを返す
    raises:
        Any
    """
    for nm in excel_file.sheet_names:
        if sheet_name in nm:
            return nm


def get_data_frame(excel_file: pd.ExcelFile, sheet_name: str) -> dict:
    """
    Excel ファイルから指定されたシートを DataFrame 形式で取得する関数

    Args:
        excel_file (pandas.ExcelFile): ExcelFile オブジェクト
        sheet_name (str): シート名
    Returns:
        any: 指定されたセルのデータを返す
        list[str]: データ取得に失敗した場合、すべてのエラーメッセージを list として返す
    """
    return pd.read_excel(excel_file, sheet_name=sheet_name, header=None)


def get_cell_value(excel_file: pd.ExcelFile, sheet_name: str, row: int, col: int):
    """
    指定されたセルのデータを取得する関数

    Args:
        excel_file (pandas.ExcelFile): pandasのExcelFileオブジェクト
        sheet_name (str): シート名
        row: セルの行数
        rol: セルの列数
    Returns:
        any: 指定されたセルのデータを返す
    """
    try:
        df: pd.DataFrame = pd.read_excel(excel_file, sheet_name=sheet_name)
        cell_value = df.iat[row, col]

        return cell_value
    except Exception as e:
        return [f"セルのデータ取得に失敗しました: {str(e)}"]


def get_range_values(
    excel_file: pd.ExcelFile, sheet_name: str, cell_rows: list, cell_cols: list
):
    """
    指定されたセル範囲のデータを取得する関数

    Args:
        excel_file (pandas.ExcelFile): pandasのExcelFileオブジェクト
        sheet_name (str): シート名
        cell_rows (str): 範囲の行数 list ※例: ``3:10``, ``[1,9]``
        cell_cols (str): 範囲の列数 list ※例: ``3:10``, ``[1,9]``
    Returns:
        list[list]: 指定されたセル範囲のデータをリスト形式で返す
    raises:
        Any
    """

    df = pd.read_excel(excel_file, sheet_name=sheet_name)
    data = df.iloc[cell_rows, cell_cols].values.tolist()
    return data
