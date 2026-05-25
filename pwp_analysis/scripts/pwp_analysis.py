import pandas as pd
import os
import argparse
import xlsxwriter
from datetime import datetime

def process_pwp_data(input_file, output_root=None):
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return
        
    if output_root is None:
        output_root = os.path.dirname(input_file)
        
    timestamp = datetime.now().strftime("%d%m%Y")
    output_dir = os.path.join(output_root, f"PWP_Analysis_Results_{timestamp}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    try:
        if input_file.lower().endswith('.csv'):
            df = pd.read_csv(input_file)
        else:
            df = pd.read_excel(input_file)
    except Exception as e:
        print(f"Error reading file: {e}")
        return
        
    # Analysis logic
    site_col = 'SiteCodeName'
    name_col = 'SalesmanName'
    date_col = 'DocumentDate'
    value_col = 'PWP Receipt Count'
    
    if name_col not in df.columns or site_col not in df.columns or date_col not in df.columns:
        print(f"Error: Required columns not found. Headers: {df.columns.tolist()}")
        return
        
    df = df.dropna(subset=[name_col])
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(by=[date_col, name_col])
    
    unique_sites = df[site_col].unique()
    
    for site in unique_sites:
        if pd.isna(site):
            site_name = "Unknown_Site"
            site_df = df[df[site_col].isna()].copy()
        else:
            site_name = str(site)
            site_df = df[df[site_col] == site].copy()
            
        print(f"Processing site: {site_name}")
        if site_df.empty: continue
        
        # Unique dates in order (Date only format)
        all_dates = site_df[date_col].dt.strftime('%b %d').unique()
        
        # Pivot table
        table = site_df.pivot_table(
            index=name_col, 
            columns=site_df[date_col].dt.strftime('%b %d'), 
            values=value_col, 
            aggfunc='sum',
            fill_value=0
        )
        
        # Ensure columns are in chronological order
        table = table[list(all_dates)]
        
        # 1. Daily High Count Calculation
        high_counts = pd.Series(0, index=table.index)
        for col in table.columns:
            m = table[col].max()
            if m > 0:
                winners = table.index[table[col] == m]
                high_counts[winners] += 1
        
        # 2. UTD Total Calculation
        utd_total = table.sum(axis=1)
        
        # 3. Create Ranking DataFrame
        ranks_df = pd.DataFrame({
            'UTD Total': utd_total,
            'Daily Highs': high_counts
        }, index=table.index)
        
        # Rename columns as requested
        rank_total_col = 'Rank (Total)'
        rank_daily_col = 'Rank (Daily #1)'
        
        # Rank by UTD Total (Descending)
        ranks_df[rank_total_col] = ranks_df['UTD Total'].rank(ascending=False, method='min').astype(int)
        # Rank by Daily Highs (Descending)
        ranks_df[rank_daily_col] = ranks_df['Daily Highs'].rank(ascending=False, method='min').astype(int)
        
        # Combine all columns
        table = pd.concat([ranks_df[[rank_total_col, rank_daily_col, 'UTD Total']], table], axis=1)
        table = table.sort_values(by='UTD Total', ascending=False)
        
        # Add a TOTAL row at the bottom
        total_vals = table.sum(axis=0)
        total_vals[rank_total_col] = ""
        total_vals[rank_daily_col] = ""
        total_vals.name = 'GRAND TOTAL'
        table.loc['GRAND TOTAL'] = total_vals
        
        safe_site_name = "".join([c if c.isalnum() or c in (' ', '-', '_') else '_' for c in site_name])
        output_file = os.path.join(output_dir, f"{safe_site_name}_{timestamp}.xlsx")
        
        # Excel Creation
        writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
        table.reset_index().rename(columns={'index': 'SalesmanName'}).to_excel(writer, sheet_name='Daily Performance', index=False)
        
        summary_table = table[[rank_total_col, rank_daily_col, 'UTD Total']].copy().reset_index().rename(columns={'index': 'SalesmanName'})
        summary_table.to_excel(writer, sheet_name='UTD Summary', index=False)
        
        workbook = writer.book
        perf_sheet = writer.sheets['Daily Performance']
        summary_sheet = writer.sheets['UTD Summary']
        
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#2C3E50', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        rank_fmt = workbook.add_format({'bold': True, 'bg_color': '#EBF5FB', 'border': 1, 'align': 'center'})
        utd_fmt = workbook.add_format({'bold': True, 'bg_color': '#FFF7E6', 'border': 1, 'align': 'center'})
        normal_fmt = workbook.add_format({'border': 1, 'align': 'center'})
        top_fmt = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100', 'border': 1, 'align': 'center'})
        bottom_fmt = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'border': 1, 'align': 'center'})
        total_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'align': 'center'})
        
        num_rows = len(table)
        num_cols = len(table.columns)
        
        # Columns: 0:Name, 1:Rank (Total), 2:Rank (Daily #1), 3:UTD Total, 4+:Dates
        perf_sheet.set_column(0, 0, 35) # Salesman
        perf_sheet.set_column(1, 2, 14, rank_fmt)
        perf_sheet.set_column(3, 3, 14, utd_fmt)
        perf_sheet.set_column(4, num_cols, 10, normal_fmt)
        
        for col_num, value in enumerate(table.reset_index().columns.values):
            perf_sheet.write(0, col_num, value if value != 'index' else 'SalesmanName', header_fmt)
            
        for r_idx in range(num_rows):
            row_label = table.index[r_idx]
            is_total = (row_label == 'GRAND TOTAL')
            fmt_row = total_fmt if is_total else None
            
            perf_sheet.write(r_idx + 1, 0, row_label, fmt_row)
            perf_sheet.write(r_idx + 1, 1, table.iloc[r_idx, 0], fmt_row if fmt_row else rank_fmt)
            perf_sheet.write(r_idx + 1, 2, table.iloc[r_idx, 1], fmt_row if fmt_row else rank_fmt)
            perf_sheet.write(r_idx + 1, 3, table.iloc[r_idx, 2], fmt_row if fmt_row else utd_fmt)
            for c_idx in range(3, len(table.columns)):
                perf_sheet.write(r_idx + 1, c_idx + 1, table.iloc[r_idx, c_idx], fmt_row if fmt_row else normal_fmt)

        if num_rows > 2:
            for col_idx in range(3, num_cols):
                excel_col_idx = col_idx + 1
                col_letter = xlsxwriter.utility.xl_col_to_name(excel_col_idx)
                sales_range = f"${col_letter}$2:${col_letter}${num_rows}"
                
                perf_sheet.conditional_format(1, excel_col_idx, num_rows - 1, excel_col_idx, {
                    'type':     'formula',
                    'criteria': f'=AND({col_letter}2=MAX({sales_range}), {col_letter}2>0)',
                    'format':   top_fmt
                })
                perf_sheet.conditional_format(1, excel_col_idx, num_rows - 1, excel_col_idx, {
                    'type':     'formula',
                    'criteria': f'=OR(AND({col_letter}2=MIN({sales_range}), MAX({sales_range})>MIN({sales_range})), MAX({sales_range})=0)',
                    'format':   bottom_fmt
                })
             
        perf_sheet.freeze_panes(1, 4)
        
        summary_sheet.set_column(0, 0, 35)
        summary_sheet.set_column(1, 2, 14, rank_fmt)
        summary_sheet.set_column(3, 3, 15, utd_fmt)
        summary_sheet.write(0, 0, 'SalesmanName', header_fmt)
        summary_sheet.write(0, 1, rank_total_col, header_fmt)
        summary_sheet.write(0, 2, rank_daily_col, header_fmt)
        summary_sheet.write(0, 3, 'UTD Total', header_fmt)
        
        for r_idx in range(num_rows):
            row_label = table.index[r_idx]
            is_total = (row_label == 'GRAND TOTAL')
            fmt_row = total_fmt if is_total else None
            summary_sheet.write(r_idx + 1, 0, row_label, fmt_row)
            summary_sheet.write(r_idx + 1, 1, table.iloc[r_idx, 0], fmt_row if fmt_row else rank_fmt)
            summary_sheet.write(r_idx + 1, 2, table.iloc[r_idx, 1], fmt_row if fmt_row else rank_fmt)
            summary_sheet.write(r_idx + 1, 3, table.iloc[r_idx, 2], fmt_row if fmt_row else utd_fmt)
            
        writer.close()
    print(f"Successfully processed all sites. Results in: {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process PWP performance data.")
    parser.add_argument("input_file", type=str, help="Path to the PWP Excel file.")
    parser.add_argument("--output_root", type=str, default=None, help="Root directory for output.")
    args = parser.parse_args()
    process_pwp_data(args.input_file, args.output_root)
