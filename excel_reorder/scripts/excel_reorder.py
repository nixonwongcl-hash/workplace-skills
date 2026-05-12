import pandas as pd
import numpy as np
import time
import argparse
import os

def process_reorder(file_path, target_days, max_shd=None):
    print(f"Reading file with calamine: {file_path}", flush=True)
    start_time = time.time()
    try:
        df = pd.read_excel(file_path, engine='calamine')
    except Exception as e:
        print(f"Error reading file: {e}")
        return
        
    print(f"Read {len(df)} rows in {time.time() - start_time:.2f} seconds", flush=True)

    # Filter BO Type column, ignore blank cells
    df['BO Type'] = df['BO Type'].replace(r'^\s*$', np.nan, regex=True)
    df = df.dropna(subset=['BO Type'])
    print(f"Rows after filtering blank BO Type: {len(df)}", flush=True)

    # Calculate Daily Demand
    df['Day 1 to 30'] = pd.to_numeric(df['Day 1 to 30'], errors='coerce').fillna(0)
    df['Day 31 to 60'] = pd.to_numeric(df['Day 31 to 60'], errors='coerce').fillna(0)
    df['Day 61-90'] = pd.to_numeric(df['Day 61-90'], errors='coerce').fillna(0)

    df['Daily Demand'] = (df['Day 1 to 30'] + df['Day 31 to 60'] + df['Day 61-90']) / 90

    # Current Stock Pipeline
    df['SOH'] = pd.to_numeric(df['SOH'], errors='coerce').fillna(0)
    df['OpenPO'] = pd.to_numeric(df['OpenPO'], errors='coerce').fillna(0)
    df['OpenSTO'] = pd.to_numeric(df['OpenSTO'], errors='coerce').fillna(0)
    df['Intransit'] = pd.to_numeric(df['Intransit'], errors='coerce').fillna(0)

    df['Pipeline Stock'] = df['SOH'] + df['OpenPO'] + df['OpenSTO'] + df['Intransit']

    # Calculate Suggested Qty to reorder dynamically
    if max_shd is not None and 'SHD' in df.columns:
        df['SHD_Num'] = pd.to_numeric(df['SHD'], errors='coerce').fillna(0)

    for day in target_days:
        col_name = f'Suggested Qty (P{day})'
        df[col_name] = np.maximum(0, np.ceil((df['Daily Demand'] * day) - df['Pipeline Stock']))
        
        if max_shd is not None and 'SHD' in df.columns:
            df.loc[df['SHD_Num'] > max_shd, col_name] = 0

    if 'SHD_Num' in df.columns:
        df.drop(columns=['SHD_Num'], inplace=True)

    # Generate Output paths in the same directory as input
    base_dir = os.path.dirname(file_path)
    base_file = os.path.basename(file_path)
    
    new_name = base_file.replace("SHD", "Reorder") if "SHD" in base_file else f"Reorder_{base_file}"
    output_path = os.path.join(base_dir, new_name)
    
    summary_name = base_file.replace("SHD", "Reorder_History_Summary") if "SHD" in base_file else f"Reorder_History_Summary_{base_file}"
    summary_path = os.path.join(base_dir, summary_name)

    print(f"Saving main file with xlsxwriter to: {output_path}", flush=True)
    start_time = time.time()
    try:
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Reorder', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Reorder']
            
            header_format = workbook.add_format({'bg_color': 'black', 'font_color': 'white', 'bold': True, 'align': 'center', 'valign': 'vcenter'})
            center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
            left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter'})
            
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                
                col_len = max(df[value].astype(str).map(len).max(), len(str(value))) + 2
                col_len = min(col_len, 50)
                
                if value == 'ArticleDesc':
                    worksheet.set_column(col_num, col_num, col_len, left_format)
                else:
                    worksheet.set_column(col_num, col_num, col_len, center_format)
            
            worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)

        print(f"Completed! Main file saved in {time.time() - start_time:.2f} seconds", flush=True)
    except Exception as e:
        print(f"Error saving main file: {e}")

    print(f"Saving summary file to: {summary_path}", flush=True)
    try:
        summary_data = {
            'Metric': ['Total Lines Processed'],
            'Value': [len(df)]
        }
        for day in target_days:
            col_name = f'Suggested Qty (P{day})'
            items_to_order = (df[col_name] > 0).sum()
            total_qty_to_order = df[col_name].sum()
            summary_data['Metric'].extend([f'Items needing order (P{day})', f'Total Qty to order (P{day})'])
            summary_data['Value'].extend([items_to_order, total_qty_to_order])
            
        df_summary = pd.DataFrame(summary_data)
        
        with pd.ExcelWriter(summary_path, engine='xlsxwriter') as writer:
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Summary']
            header_format = workbook.add_format({'bg_color': 'black', 'font_color': 'white', 'bold': True})
            worksheet.set_column(0, 0, 35)
            worksheet.set_column(1, 1, 15)
            for col_num, value in enumerate(df_summary.columns.values):
                worksheet.write(0, col_num, value, header_format)

        print(f"Summary file saved.", flush=True)
    except Exception as e:
        print(f"Error saving summary file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate suggested reorder quantities.")
    parser.add_argument("file_path", help="Path to the SHD Excel file")
    parser.add_argument("--days", nargs='+', type=int, required=True, help="List of target days for calculation (e.g., 30 60)")
    parser.add_argument("--max-shd", type=float, default=None, help="Only calculate reorder if SHD is <= this value. Otherwise 0.")
    
    args = parser.parse_args()
    process_reorder(args.file_path, args.days, args.max_shd)
