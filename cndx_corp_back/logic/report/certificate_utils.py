import pandas as pd
# 電気
ELECTRIC_CERTIFICATE_CODES = {
    "9900010002",
    "9900010003",
    "9900010004",
    "9900011002",
    "9900011003",
    "9900011004",
    "9900011005",
    "9900010006",
    "9900011007",
    "9900010013",
    "9900011013",
}

HEAT_CERTIFICATE_CODES = {
    "9900011006",
    "9900011008",
    "9900011009",
    "9900011010",
    "9900011011",
    "9900011012",
    "9900011014",
}


def is_electric_energy_code(code: str) -> bool:
    code_str = str(code) if code is not None else ""
    return code_str.startswith("02") and code_str.endswith("011")


def apply_certificate_adjustments(df: pd.DataFrame, co2_column: str):
    """Remove certificate rows and adjust electric totals. Returns (df, heat_cert_sum_by_building)."""
    if df is None or df.empty:
        return df, pd.Series(dtype=float)
    if "energy_code" not in df.columns or co2_column not in df.columns:
        return df, pd.Series(dtype=float)

    adjusted_df = df.copy()
    adjusted_df[co2_column] = pd.to_numeric(adjusted_df[co2_column], errors="coerce").fillna(0)
    code_series = adjusted_df["energy_code"].astype(str)
    adjusted_df["energy_code"] = code_series

    electric_certificate_mask = code_series.isin(ELECTRIC_CERTIFICATE_CODES)
    heat_certificate_mask = code_series.isin(HEAT_CERTIFICATE_CODES)
    electric_energy_mask = code_series.apply(is_electric_energy_code)

    subtract_map = (
        adjusted_df.loc[electric_certificate_mask]
        .groupby("building_id")[co2_column]
        .sum()
        if electric_certificate_mask.any()
        else pd.Series(dtype=float)
    )

    for building_id, subtract_value in subtract_map.items():
        if subtract_value <= 0:
            continue
        electric_mask = (adjusted_df["building_id"] == building_id) & electric_energy_mask
        if not electric_mask.any():
            continue

        current_total = adjusted_df.loc[electric_mask, co2_column].sum()
        if current_total <= 0:
            adjusted_df.loc[electric_mask, co2_column] = 0
            continue

        new_total = max(current_total - subtract_value, 0)
        if new_total == 0:
            adjusted_df.loc[electric_mask, co2_column] = 0
        else:
            scale = new_total / current_total
            adjusted_df.loc[electric_mask, co2_column] = adjusted_df.loc[electric_mask, co2_column] * scale

    if electric_certificate_mask.any():
        adjusted_df.loc[electric_certificate_mask, co2_column] = 0

    heat_certificate_map = (
        adjusted_df.loc[heat_certificate_mask]
        .groupby("building_id")[co2_column]
        .sum()
        if heat_certificate_mask.any()
        else pd.Series(dtype=float)
    )

    removal_mask = electric_certificate_mask | heat_certificate_mask
    adjusted_df = adjusted_df.loc[~removal_mask].reset_index(drop=True)
    return adjusted_df, heat_certificate_map
