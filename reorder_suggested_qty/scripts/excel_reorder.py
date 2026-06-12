import pandas as pd
import numpy as np
import time
import argparse
import os

def round_to_trp(qty, trp):
    if trp <= 1:
        return int(qty)
    return int(round(qty / trp) * trp)

def process_reorder(file_path):
    print(f"Reading file with calamine: {file_path}", flush=True)
    start_time = time.time()
    try:
        df = pd.read_excel(file_path, engine='calamine')
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    print(f"Read {len(df)} rows in {time.time() - start_time:.2f} seconds", flush=True)

    # Pareto Mapping
    if 'CombinedPareto' not in df.columns:
        if 'Pareto' in df.columns:
            df.rename(columns={'Pareto': 'CombinedPareto'}, inplace=True)
        else:
            pareto_cols = [c for c in df.columns if 'Pareto' in c]
            if pareto_cols:
                df.rename(columns={pareto_cols[0]: 'CombinedPareto'}, inplace=True)
            else:
                df['CombinedPareto'] = 'C'
    df['CombinedPareto'] = df['CombinedPareto'].fillna('C').astype(str).str.strip().str.upper()
    df.loc[df['CombinedPareto'] == '', 'CombinedPareto'] = 'C'
    df = df[df['CombinedPareto'] == 'A'].copy()

    # Filter BO Type
    if 'BO Type' in df.columns:
        df['BO Type'] = df['BO Type'].replace(r'^\s*$', np.nan, regex=True)
        df = df.dropna(subset=['BO Type']).copy()

    # Daily Demand
    for col in ['Day 1 to 30', 'Day 31 to 60', 'Day 61-90']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['Daily Demand'] = (df['Day 1 to 30'] + df['Day 31 to 60'] + df['Day 61-90']) / 90

    # Pipeline Stock
    for col in ['SOH', 'Intransit']:
        df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)
    df['Pipeline Stock'] = df['SOH'] + df['Intransit']

    # TRP
    if 'TRP' in df.columns:
        df['TRP'] = pd.to_numeric(df['TRP'], errors='coerce').fillna(1).clip(lower=1).astype(int)
    else:
        df['TRP'] = 1

    # Logic SHD
    with np.errstate(divide='ignore', invalid='ignore'):
        df['Calc_SHD'] = np.where(df['Daily Demand'] > 0, df['Pipeline Stock'] / df['Daily Demand'], 999)
    if 'SHD' in df.columns:
        df['Logic_SHD'] = pd.to_numeric(df['SHD'], errors='coerce').fillna(df['Calc_SHD'])
    else:
        df['Logic_SHD'] = df['Calc_SHD']

    # --- RAW strategy values ---
    df['_raw_s1'] = np.where(df['Logic_SHD'] < 45, np.ceil(df['Daily Demand'] * 45), 0)
    df['_raw_s2'] = np.where(df['Logic_SHD'] < 60, np.ceil(df['Daily Demand'] * 45), 0)

    # --- TRP-Adjusted Final Values ---
    raw_cols = ['_raw_s1', '_raw_s2']
    final_names = [
        'Strat 1: SHD < 45 (Top Up 45)',
        'Strat 2: SHD < 60 (Top Up 45)'
    ]
    for raw_col, final_col in zip(raw_cols, final_names):
        df[final_col] = [round_to_trp(r, t) for r, t in zip(df[raw_col], df['TRP'])]

    # --- Precompute Cell Flags ---
    is_ab = df['CombinedPareto'].isin(['A', 'B'])
    flag_red   = (is_ab & (df['SOH'] == 0)).values
    flag_orange = (is_ab & (df['Logic_SHD'] < 45) & ~(is_ab & (df['SOH'] == 0))).values

    # Per-strategy yellow: raw > 0 but TRP rounded to 0
    yellow_flags = {}
    for raw_col, final_col in zip(raw_cols, final_names):
        yellow_flags[final_col] = ((df[raw_col] > 0) & (df[final_col] == 0)).values

    # Cleanup intermediates
    df.drop(columns=['Logic_SHD', 'Calc_SHD'] + raw_cols, inplace=True)

    # Sorting
    df = df.sort_values(['Strat 1: SHD < 45 (Top Up 45)'], ascending=[False])
    df = df.reset_index(drop=True)

    # --- Output ---
    base_dir = os.path.dirname(file_path)
    base_file = os.path.basename(file_path)
    output_path = os.path.join(base_dir, base_file.replace(".xlsx", "_Pareto_Analysis.xlsx"))
    print(f"Saving report to: {output_path}", flush=True)
    start_time = time.time()

    try:
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Reorder Details', index=False)
            workbook  = writer.book
            worksheet = writer.sheets['Reorder Details']

            # Formats
            hdr_fmt    = workbook.add_format({'bg_color': 'black', 'font_color': 'white', 'bold': True, 'align': 'center', 'valign': 'vcenter'})
            center_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
            left_fmt   = workbook.add_format({'align': 'left',   'valign': 'vcenter'})
            red_fmt    = workbook.add_format({'bg_color': '#FFCDD2', 'align': 'center', 'valign': 'vcenter'})
            orange_fmt = workbook.add_format({'bg_color': '#FFE0B2', 'align': 'center', 'valign': 'vcenter'})
            yellow_fmt = workbook.add_format({'bg_color': '#FFFDE7', 'align': 'center', 'valign': 'vcenter'})

            col_indices = {col: i for i, col in enumerate(df.columns)}
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, hdr_fmt)
                col_len = min(max(df[value].astype(str).map(len).max(), len(str(value))) + 2, 50)
                fmt = left_fmt if value == 'ArticleDesc' else center_fmt
                worksheet.set_column(col_num, col_num, col_len, fmt)

            worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
            worksheet.freeze_panes(1, 2)

            # Apply per-cell colour to strategy columns only
            for col_name in final_names:
                col_idx  = col_indices[col_name]
                col_vals = df[col_name].values
                for row_idx in range(len(df)):
                    if flag_red[row_idx]:
                        fmt = red_fmt
                    elif flag_orange[row_idx]:
                        fmt = orange_fmt
                    elif yellow_flags[col_name][row_idx]:
                        fmt = yellow_fmt
                    else:
                        continue  # no colour needed
                    worksheet.write(row_idx + 1, col_idx, int(col_vals[row_idx]), fmt)

            # Pareto Analysis Summary Tab
            summary_rows = []
            for p_class in ['A']:
                p_df = df[df['CombinedPareto'] == p_class]
                row  = {'Pareto Class': p_class, 'Total Articles': len(p_df)}
                for strat in final_names:
                    row[f'{strat} (Items)'] = (p_df[strat] > 0).sum()
                    row[f'{strat} (Qty)']   = p_df[strat].sum()
                summary_rows.append(row)

            df_sum = pd.DataFrame(summary_rows)
            df_sum.to_excel(writer, sheet_name='Pareto Analysis', index=False)
            s_sheet = writer.sheets['Pareto Analysis']
            s_sheet.set_column(0, 0, 15, center_fmt)
            s_sheet.set_column(1, 1, 15, center_fmt)
            for i in range(2, len(df_sum.columns)):
                s_sheet.set_column(i, i, 28, center_fmt)
            for col_num, value in enumerate(df_sum.columns.values):
                s_sheet.write(0, col_num, value, hdr_fmt)

        print(f"Completed! Saved in {time.time() - start_time:.2f} seconds", flush=True)
    except Exception as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pareto-Driven Reorder Calculation")
    parser.add_argument("file_path", help="Path to the SHD Excel file")
    args = parser.parse_args()
    process_reorder(args.file_path)
