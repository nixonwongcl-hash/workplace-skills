import pandas as pd
import numpy as np
import time
import argparse
import os
import math

def round_up_to_trp(qty, trp):
    if qty <= 0:
        return 0
    return int(math.ceil(qty / trp) * trp)

def round_trp(raw, trp):
    if raw <= 0:
        return 0
    if trp <= 1:
        return int(raw)
    return int(round(raw / trp) * trp)

def process_reorder(file_path, article_master_path=None, pareto_classes=None, rp_type_filter=None, max_shd=None, intransit_zero=False, top_up_days=None):
    print(f"Reading file with calamine: {file_path}", flush=True)
    start_time = time.time()
    try:
        df = pd.read_excel(file_path, engine='calamine')
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    print(f"Read {len(df)} rows in {time.time() - start_time:.2f} seconds", flush=True)

    # Clean intermediate fields
    if 'CombinedPareto' not in df.columns:
        if 'Pareto' in df.columns:
            df.rename(columns={'Pareto': 'CombinedPareto'}, inplace=True)
        else:
            pareto_cols = [c for c in df.columns if 'pareto' in c.lower()]
            if pareto_cols:
                df.rename(columns={pareto_cols[0]: 'CombinedPareto'}, inplace=True)
            else:
                df['CombinedPareto'] = 'C'
    df['CombinedPareto'] = df['CombinedPareto'].fillna('C').astype(str).str.strip().str.upper()
    df.loc[~df['CombinedPareto'].isin(['A', 'B', 'C']), 'CombinedPareto'] = 'C'

    # Filter Pareto Classes
    if pareto_classes:
        classes = [c.strip().upper() for c in pareto_classes.split(',') if c.strip()]
        df = df[df['CombinedPareto'].isin(classes)].copy()
        print(f"Filtered Pareto to classes {classes}: {len(df)} rows remain.", flush=True)

    # Filter RP Type
    if rp_type_filter:
        rp_col = 'RP Type'
        if rp_col not in df.columns:
            found_rp = [c for c in df.columns if 'rp' in c.lower() or 'replenish' in c.lower()]
            if found_rp:
                df.rename(columns={found_rp[0]: rp_col}, inplace=True)
            else:
                df[rp_col] = ''
        df = df[df[rp_col].astype(str).str.contains(rp_type_filter, case=False, na=False)].copy()
        print(f"Filtered RP Type containing '{rp_type_filter}': {len(df)} rows remain.", flush=True)

    # Filter SHD
    if max_shd is not None:
        shd_col = 'SHD'
        if shd_col not in df.columns:
            df[shd_col] = np.nan
        df[shd_col] = pd.to_numeric(df[shd_col], errors='coerce')
        df = df[df[shd_col] <= max_shd].copy()
        print(f"Filtered SHD <= {max_shd}: {len(df)} rows remain.", flush=True)

    # Filter Intransit = 0
    if intransit_zero:
        int_col = 'Intransit'
        if int_col not in df.columns:
            df[int_col] = 0
        df[int_col] = pd.to_numeric(df[int_col], errors='coerce').fillna(0)
        df = df[df[int_col] == 0].copy()
        print(f"Filtered Intransit == 0: {len(df)} rows remain.", flush=True)

    # 1. Filter: Only reorder for those OOS under 'OOS Indicator' col
    oos_col = 'OOS Indicator'
    if oos_col not in df.columns:
        found_oos = [c for c in df.columns if 'oos' in c.lower()]
        if found_oos:
            df.rename(columns={found_oos[0]: oos_col}, inplace=True)
        else:
            df[oos_col] = np.nan

    # Let's count rows before OOS filtering for info
    oos_mask = df[oos_col].astype(str).str.strip().str.upper() == 'OOS'
    df = df[oos_mask].copy()
    print(f"Filtered to {len(df)} OOS rows.", flush=True)

    if len(df) == 0:
        print("No matching rows to calculate reorder suggestions.", flush=True)
        return

    # 3. Daily Demand
    for col in ['Day 1 to 30', 'Day 31 to 60', 'Day 61-90']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['Daily Demand'] = (df['Day 1 to 30'] + df['Day 31 to 60'] + df['Day 61-90']) / 90

    # 4. Return Policy normalization
    ret_col = 'Return Policy'
    if ret_col not in df.columns:
        ret_cols = [c for c in df.columns if 'return' in c.lower()]
        if ret_cols:
            df.rename(columns={ret_cols[0]: ret_col}, inplace=True)
        else:
            df[ret_col] = 'Non Returnable'

    # 5. TRP
    if 'TRP' in df.columns:
        df['TRP'] = pd.to_numeric(df['TRP'], errors='coerce').fillna(1).clip(lower=1).astype(int)
    else:
        df['TRP'] = 1

    # 6. Suggested reorders
    # SOH
    if 'SOH' in df.columns:
        df['SOH'] = pd.to_numeric(df['SOH'], errors='coerce').fillna(0)
    else:
        df['SOH'] = 0

    # Logic SHD
    logic_shd = []
    for idx, row in df.iterrows():
        shd_val = row.get('SHD', np.nan)
        if not pd.isna(shd_val):
            logic_shd.append(float(shd_val))
        else:
            demand = row['Daily Demand']
            pipeline = row['SOH'] + row.get('Intransit', 0)
            if demand > 0:
                logic_shd.append(pipeline / demand)
            else:
                logic_shd.append(999.0)
    df['Logic_SHD'] = logic_shd

    # Calculation logic selection
    if top_up_days is not None:
        final_col = f'Suggested Reorder Qty ({top_up_days} Days)'
        raw_qty = []
        for idx, row in df.iterrows():
            demand = row['Daily Demand']
            raw_qty.append(math.ceil(demand * top_up_days) if demand > 0 else 0)
        df['_raw_suggested'] = raw_qty
        df[final_col] = [round_trp(r, t) for r, t in zip(df['_raw_suggested'], df['TRP'])]
        final_names = [final_col]
        flag_yellow = {final_col: ((df['_raw_suggested'] > 0) & (df[final_col] == 0)).values}
        df.drop(columns=['_raw_suggested'], inplace=True)
    else:
        # Default Multi-Strategy logic (Strat 1 and Strat 2)
        final_col = 'Strat 1: SHD < 45 (Top Up 45)'
        final_col2 = 'Strat 2: SHD < 60 (Top Up 45)'
        final_names = [final_col, final_col2]

        raw1, raw2 = [], []
        for idx, row in df.iterrows():
            shd_d = row['Logic_SHD']
            demand = row['Daily Demand']
            # Strat 1: SHD < 45, top up 45
            raw1.append(math.ceil(demand * 45) if shd_d < 45 and demand > 0 else 0)
            # Strat 2: SHD < 60, top up 45
            raw2.append(math.ceil(demand * 45) if shd_d < 60 and demand > 0 else 0)

        df[final_col] = [round_trp(r, t) for r, t in zip(raw1, df['TRP'])]
        df[final_col2] = [round_trp(r, t) for r, t in zip(raw2, df['TRP'])]
        flag_yellow = {
            final_col: ((np.array(raw1) > 0) & (df[final_col] == 0)).values,
            final_col2: ((np.array(raw2) > 0) & (df[final_col2] == 0)).values
        }

    # Map BulkyLargePack from Article Master if provided
    if article_master_path and os.path.exists(article_master_path):
        print(f"Reading article master: {article_master_path}", flush=True)
        try:
            m_df = pd.read_excel(article_master_path, engine='calamine')
            key_col = 'ArticleCode' if 'ArticleCode' in m_df.columns else 'ArticleNo'
            if key_col in m_df.columns and 'BulkyLargePack' in m_df.columns:
                m_df[key_col] = m_df[key_col].astype(str).str.strip()
                mapping = dict(zip(m_df[key_col], m_df['BulkyLargePack']))
                df['BulkyLargePack'] = df['ArticleCode'].astype(str).str.strip().map(mapping)
            else:
                df['BulkyLargePack'] = np.nan
        except Exception as e:
            print(f"Error mapping article master: {e}", flush=True)
            df['BulkyLargePack'] = np.nan
    else:
        df['BulkyLargePack'] = np.nan

    # Arrange columns to place BulkyLargePack right before suggested quantity
    if 'BulkyLargePack' in df.columns:
        cols = list(df.columns)
        first_final = final_names[0]
        if first_final in cols:
            cols.remove('BulkyLargePack')
            idx = cols.index(first_final)
            cols.insert(idx, 'BulkyLargePack')
            df = df[cols]

    # Precompute formatting flags
    is_ab = df['CombinedPareto'].isin(['A', 'B'])
    flag_red = (df['SOH'] == 0).values
    flag_orange = ((df['Logic_SHD'] < 45) & (df['SOH'] > 0)).values

    # Sorting
    df = df.sort_values(final_names[0], ascending=False).reset_index(drop=True)

    # Save to Excel
    base_dir = os.path.dirname(file_path)
    base_file = os.path.basename(file_path)
    output_path = os.path.join(base_dir, base_file.replace(".xlsx", "_Pareto_Analysis.xlsx"))
    print(f"Saving report to: {output_path}", flush=True)

    writer = None
    try:
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
    except PermissionError:
        name, ext = os.path.splitext(base_file)
        timestamp = int(time.time())
        output_path = os.path.join(base_dir, f"{name}_Pareto_Analysis_{timestamp}{ext}")
        print(f"Original output file was locked. Saving to: {output_path}", flush=True)
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')

    try:
        with writer:
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

            # Apply coloring to strategy columns
            for col_n in final_names:
                col_idx = col_indices[col_n]
                col_vals = df[col_n].values
                for row_idx in range(len(df)):
                    if flag_red[row_idx]:
                        fmt = red_fmt
                    elif flag_orange[row_idx]:
                        fmt = orange_fmt
                    elif flag_yellow[col_n][row_idx]:
                        fmt = yellow_fmt
                    else:
                        continue
                    worksheet.write(row_idx + 1, col_idx, int(col_vals[row_idx]), fmt)

            # Tab 2: Pareto Analysis Summary Tab
            summary_rows = []
            for p_class in ['A', 'B', 'C']:
                p_df = df[df['CombinedPareto'] == p_class]
                row  = {
                    'Pareto Class': p_class, 
                    'Total Articles': len(p_df),
                }
                for col_n in final_names:
                    row[f'{col_n} (Items)'] = (p_df[col_n] > 0).sum()
                    row[f'{col_n} (Qty)'] = p_df[col_n].sum()
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

        print(f"Completed! Saved to {output_path} in {time.time() - start_time:.2f} seconds", flush=True)
        print(f"Total Articles: {len(df)}")
        for col_n in final_names:
            print(f"{col_n} - Items needing order: {(df[col_n] > 0).sum()}, Total Qty: {df[col_n].sum()}", flush=True)
    except Exception as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pareto-Driven Reorder Calculation")
    parser.add_argument("file_path", help="Path to the SHD Excel file")
    parser.add_argument("--article_master", help="Path to the Article Master Excel file", default=r"C:\Users\USER\Downloads\Article_Master_EA.xlsx")
    parser.add_argument("--pareto", help="Comma separated Pareto classes to include (e.g. A,B,C)")
    parser.add_argument("--rp_type", help="RP Type filter substring (e.g. SGO)")
    parser.add_argument("--max_shd", type=float, help="Max SHD threshold filter")
    parser.add_argument("--intransit_zero", action="store_true", help="Filter Intransit == 0 only")
    parser.add_argument("--top_up_days", type=int, help="Specify top up days logic override")
    args = parser.parse_args()
    process_reorder(
        args.file_path,
        article_master_path=args.article_master,
        pareto_classes=args.pareto,
        rp_type_filter=args.rp_type,
        max_shd=args.max_shd,
        intransit_zero=args.intransit_zero,
        top_up_days=args.top_up_days
    )
