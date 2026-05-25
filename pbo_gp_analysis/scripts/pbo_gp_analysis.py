import pandas as pd
import numpy as np
import os
import argparse
import sys
from datetime import datetime

# Ensure UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def get_safe_filename(filepath):
    if not os.path.exists(filepath):
        return filepath
    name, ext = os.path.splitext(filepath)
    counter = 2
    while os.path.exists(f"{name}_v{counter}{ext}"):
        counter += 1
    return f"{name}_v{counter}{ext}"

def run_pbo_gp_analysis(input_file, output_file=None):
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Loading raw data from: {input_file}")
        
        # Read raw CSV
        df = pd.read_csv(input_file)
        df.columns = df.columns.str.strip()
        
        # Validate critical columns
        required_cols = ['PenetrationTracker', 'ArticleCode', 'ArticleName', 'BO_Type', 'Qty (1S)', 'SalesAmt', 'GrossProfit', 'GP %']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' is missing from the input file.")
                
        # Ensure numeric formatting
        cols_to_fix = ['Qty (1S)', 'SalesAmt', 'GrossProfit', 'GP %']
        for col in cols_to_fix:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Grouping data by main category and article...")
        # Group by Category and Article
        grouped = df.groupby(['PenetrationTracker', 'ArticleCode']).agg({
            'ArticleName': 'first',
            'BO_Type': 'first',
            'GP %': 'max',
            'SalesAmt': 'sum',
            'Qty (1S)': 'sum'
        }).reset_index()
        
        # Calculate Metrics
        grouped['Unit_Selling_Price'] = np.where(grouped['Qty (1S)'] > 0, grouped['SalesAmt'] / grouped['Qty (1S)'], 0)
        grouped['GP_by_SalesAmt'] = grouped['GP %'] * grouped['Unit_Selling_Price']
        
        # Identify Brand Outlet (BO) / Own Brand vs Non-BO
        bo_types = ['BO SEMI', 'BO FULL', 'BO MASS', 'Own Brand']
        grouped['is_bo'] = grouped['BO_Type'].isin(bo_types)
        
        # Find the winners for each category
        categories = grouped['PenetrationTracker'].unique()
        excel_data = []
        
        def get_best(subset, column):
            # Prioritize BO brands first
            bo_subset = subset[subset['is_bo']]
            if not bo_subset.empty:
                return bo_subset.loc[bo_subset[column].idxmax()]
            else:
                # Fallback to non-BO brands
                non_bo_subset = subset[~subset['is_bo']]
                if not non_bo_subset.empty:
                    return non_bo_subset.loc[non_bo_subset[column].idxmax()]
                return None

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Running margin optimization logic across {len(categories)} categories...")
        for cat in categories:
            cat_df = grouped[grouped['PenetrationTracker'] == cat]
            if cat_df.empty: continue
            
            # Winner 1: GP %
            w1 = get_best(cat_df, 'GP %')
            if w1 is not None:
                excel_data.append({
                    'Main Category': cat, 
                    'Rank Type': 'Highest GP%', 
                    'Article Code': w1['ArticleCode'], 
                    'Article Description': w1['ArticleName'], 
                    'BO Type': w1['BO_Type'], 
                    'Value': w1['GP %'], 
                    'is_percent': True
                })
            
            # Winner 2: GP by SalesAmt
            w2 = get_best(cat_df, 'GP_by_SalesAmt')
            if w2 is not None:
                excel_data.append({
                    'Main Category': cat, 
                    'Rank Type': 'Highest GP by SalesAmt', 
                    'Article Code': w2['ArticleCode'], 
                    'Article Description': w2['ArticleName'], 
                    'BO Type': w2['BO_Type'], 
                    'Value': w2['GP_by_SalesAmt'], 
                    'is_percent': False
                })
            
            # Winner 3: Selling Price
            w3 = get_best(cat_df, 'Unit_Selling_Price')
            if w3 is not None:
                excel_data.append({
                    'Main Category': cat, 
                    'Rank Type': 'Highest Selling Price', 
                    'Article Code': w3['ArticleCode'], 
                    'Article Description': w3['ArticleName'], 
                    'BO Type': w3['BO_Type'], 
                    'Value': w3['Unit_Selling_Price'], 
                    'is_percent': False
                })
            
        result_df = pd.DataFrame(excel_data)
        
        # Output Setup
        if not output_file:
            date_str = datetime.now().strftime("%d%m%Y")
            output_file = rf"C:\Users\USER\Downloads\Penetration_Pivot_Analysis_Results_{date_str}.xlsx"
            
        output_file = get_safe_filename(output_file)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Writing structured rankings ({len(result_df)} rows) to: {output_file}")
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            result_df.drop(columns=['is_percent']).to_excel(writer, index=False, sheet_name='Rankings')
            
            workbook = writer.book
            worksheet = writer.sheets['Rankings']
            
            # Formatting definitions
            header_format = workbook.add_format({'bold': True, 'bg_color': '#2C3E50', 'font_color': 'white', 'border': 1, 'align': 'center'})
            bg_alt = workbook.add_format({'bg_color': '#F2F4F4', 'border': 1})
            bg_white = workbook.add_format({'bg_color': '#FFFFFF', 'border': 1})
            pct_format_alt = workbook.add_format({'num_format': '0.00%', 'bg_color': '#F2F4F4', 'border': 1})
            pct_format_white = workbook.add_format({'num_format': '0.00%', 'bg_color': '#FFFFFF', 'border': 1})
            num_format_alt = workbook.add_format({'num_format': '#,##0.00', 'bg_color': '#F2F4F4', 'border': 1})
            num_format_white = workbook.add_format({'num_format': '#,##0.00', 'bg_color': '#FFFFFF', 'border': 1})
            
            # Write custom headers
            for col_num, value in enumerate(result_df.columns[:-1]): # Exclude is_percent
                worksheet.write(0, col_num, value, header_format)
                
            # Apply rows styling
            row_idx = 1
            cat_count = 0
            for i, row in result_df.iterrows():
                # Alternate color grouping by category (3 rows per category)
                if i % 3 == 0:
                    cat_count += 1
                
                fmt = bg_alt if cat_count % 2 == 0 else bg_white
                
                # Write standard columns
                worksheet.write(row_idx, 0, row['Main Category'], fmt)
                worksheet.write(row_idx, 1, row['Rank Type'], fmt)
                worksheet.write(row_idx, 2, row['Article Code'], fmt)
                worksheet.write(row_idx, 3, row['Article Description'], fmt)
                worksheet.write(row_idx, 4, row['BO Type'], fmt)
                
                # Write formatted Value column
                val = row['Value']
                if row['is_percent']:
                    v_fmt = pct_format_alt if cat_count % 2 == 0 else pct_format_white
                else:
                    v_fmt = num_format_alt if cat_count % 2 == 0 else num_format_white
                
                worksheet.write(row_idx, 5, val, v_fmt)
                row_idx += 1
                
            # Set columns dimensions
            worksheet.set_column('A:A', 35)
            worksheet.set_column('B:B', 30)
            worksheet.set_column('C:C', 15)
            worksheet.set_column('D:D', 55)
            worksheet.set_column('E:E', 15)
            worksheet.set_column('F:F', 15)
            
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Analysis completed successfully! Saved to {output_file}")
        return output_file
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Analysis failed! Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PBO GP % Margin Penetration Analysis")
    parser.add_argument('--input', '-i', required=True, help="Path to the raw Penetration Pivot CSV table.")
    parser.add_argument('--output', '-o', type=str, default=None, help="Custom output path for the Excel rankings sheet.")
    args = parser.parse_args()
    
    run_pbo_gp_analysis(args.input, args.output)
