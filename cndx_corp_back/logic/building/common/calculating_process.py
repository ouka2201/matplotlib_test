def calculate(formula, variables, input_data):

    import sympy as sp

    """入力値を計算式と変数に代入して、計算を実行する"""
    # 数式で使うための変数をシンボルとして定義
    symbols = {var: sp.Symbol(var) for var in variables.keys()}

    # 文字列の数式を数式に変換
    converted_formula = sp.sympify(formula, locals=symbols)

    # 数式に実際の値を代入
    substituted = converted_formula.subs(
        {symbols[var]: input_data[var] for var in variables.keys()}
    )

    # 計算を実行し、結果を返却
    return float(substituted.evalf())


def get_calculation_result(logic_id, input_data, master_data):
    """master_dataからIDに対応する計算式と変数を取得し、計算結果を返却する"""
    # 指定したlogic_idに対応するデータを抽出
    row = master_data[master_data["LOGIC_ID"] == logic_id]

    # 抽出できなければ、Noneを返却
    if row.empty:
        return None

    # 計算式と変数を抽出し、計算結果を返却
    formula = row.iloc[0]["FORMULA"]
    variables = row.iloc[0]["VARIABLES"]
    return calculate(formula, variables, input_data)
