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

def run_pbo_gp_analysis(input_file, output_file=None, enhanced_output=None):
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

        # Ensure numeric formatting — fix GP% % sign parsing, handle negatives
        df['Qty (1S)'] = pd.to_numeric(df['Qty (1S)'], errors='coerce').fillna(0).abs()
        df['SalesAmt'] = pd.to_numeric(df['SalesAmt'], errors='coerce').fillna(0)
        df['GrossProfit'] = pd.to_numeric(df['GrossProfit'], errors='coerce').fillna(0)
        df['GP %'] = pd.to_numeric(df['GP %'].astype(str).str.replace('%', '', regex=False), errors='coerce').fillna(0) / 100

        # Parse MoM trend (percentage string -> decimal)
        mom_col = 'MoM  % Qty SOB  (by tracker by site)'
        if mom_col in df.columns:
            df[mom_col] = pd.to_numeric(df[mom_col].astype(str).str.replace('%', '', regex=False), errors='coerce').fillna(0) / 100

        # Parse penetration depth (Curr month % Qty SOB)
        pen_col = 'Curr month % Qty SOB (by tracker by site)'
        if pen_col in df.columns:
            df[pen_col] = pd.to_numeric(df[pen_col].astype(str).str.replace('%', '', regex=False), errors='coerce').fillna(0) / 100

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Grouping data by main category and article...")

        # Group by Category and Article — use SUM for volume/money metrics
        grouped = df.groupby(['PenetrationTracker', 'ArticleCode']).agg({
            'ArticleName': 'first',
            'BO_Type': 'first',
            'SalesAmt': 'sum',
            'Qty (1S)': 'sum',
            'GrossProfit': 'sum',
        }).reset_index()

        # Compute weighted GP% = total GrossProfit / total SalesAmt (true article-level margin)
        grouped['Weighted_GP_Pct'] = np.where(
            grouped['SalesAmt'] > 0,
            grouped['GrossProfit'] / grouped['SalesAmt'],
            0
        )

        # Compute derived metrics
        grouped['Unit_Selling_Price'] = np.where(
            grouped['Qty (1S)'] > 0,
            grouped['SalesAmt'] / grouped['Qty (1S)'],
            0
        )
        grouped['GP_by_Unit'] = grouped['Weighted_GP_Pct'] * grouped['Unit_Selling_Price']

        # Identify Brand Outlet (BO) / Own Brand vs Non-BO
        bo_types = ['BO SEMI', 'BO FULL', 'BO MASS', 'Own Brand']
        grouped['is_bo'] = grouped['BO_Type'].isin(bo_types)

        # Compute site-level aggregations for enriched analysis
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Computing site-level metrics...")

        # Average MoM trend per article (across sites)
        if mom_col in df.columns:
            article_mom = df.groupby(['PenetrationTracker', 'ArticleCode'])[mom_col].mean().reset_index()
            article_mom.columns = ['PenetrationTracker', 'ArticleCode', 'Avg_MoM_Trend']
            grouped = grouped.merge(article_mom, on=['PenetrationTracker', 'ArticleCode'], how='left')
        else:
            grouped['Avg_MoM_Trend'] = 0

        # Average penetration depth per article
        if pen_col in df.columns:
            article_pen = df.groupby(['PenetrationTracker', 'ArticleCode'])[pen_col].mean().reset_index()
            article_pen.columns = ['PenetrationTracker', 'ArticleCode', 'Avg_Penetration']
            grouped = grouped.merge(article_pen, on=['PenetrationTracker', 'ArticleCode'], how='left')
        else:
            grouped['Avg_Penetration'] = 0

        # Count unique outlets per article
        article_sites = df.groupby(['PenetrationTracker', 'ArticleCode'])['SiteCodeName'].nunique().reset_index()
        article_sites.columns = ['PenetrationTracker', 'ArticleCode', 'Outlets_Covered']
        grouped = grouped.merge(article_sites, on=['PenetrationTracker', 'ArticleCode'], how='left')

        # Find the winners for each category (original Rankings output)
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

            # Winner 1: Weighted GP%
            w1 = get_best(cat_df, 'Weighted_GP_Pct')
            if w1 is not None:
                excel_data.append({
                    'Main Category': cat,
                    'Rank Type': 'Highest GP%',
                    'Article Code': w1['ArticleCode'],
                    'Article Description': w1['ArticleName'],
                    'BO Type': w1['BO_Type'],
                    'Value': w1['Weighted_GP_Pct'],
                    'is_percent': True
                })

            # Winner 2: GP by Unit (weighted)
            w2 = get_best(cat_df, 'GP_by_Unit')
            if w2 is not None:
                excel_data.append({
                    'Main Category': cat,
                    'Rank Type': 'Highest GP by SalesAmt',
                    'Article Code': w2['ArticleCode'],
                    'Article Description': w2['ArticleName'],
                    'BO Type': w2['BO_Type'],
                    'Value': w2['GP_by_Unit'],
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

        # --- Original Output ---
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

        # --- Enhanced Output (Sheet 2 + Sheet 3) ---
        if enhanced_output:
            enhanced_output = get_safe_filename(enhanced_output)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Writing enhanced analysis to: {enhanced_output}")

            with pd.ExcelWriter(enhanced_output, engine='xlsxwriter') as writer:
                # ===== Sheet 1: Rankings (copy from original) =====
                result_df.drop(columns=['is_percent']).to_excel(writer, index=False, sheet_name='Rankings')
                wb = writer.book
                ws = writer.sheets['Rankings']

                header_fmt = wb.add_format({'bold': True, 'bg_color': '#2C3E50', 'font_color': 'white', 'border': 1, 'align': 'center'})
                bg_alt = wb.add_format({'bg_color': '#F2F4F4', 'border': 1})
                bg_white = wb.add_format({'bg_color': '#FFFFFF', 'border': 1})
                pct_fmt_alt = wb.add_format({'num_format': '0.00%', 'bg_color': '#F2F4F4', 'border': 1})
                pct_fmt_white = wb.add_format({'num_format': '0.00%', 'bg_color': '#FFFFFF', 'border': 1})
                num_fmt_alt = wb.add_format({'num_format': '#,##0.00', 'bg_color': '#F2F4F4', 'border': 1})
                num_fmt_white = wb.add_format({'num_format': '#,##0.00', 'bg_color': '#FFFFFF', 'border': 1})

                for col_num, value in enumerate(result_df.columns[:-1]):
                    ws.write(0, col_num, value, header_fmt)

                row_idx = 1
                cat_count = 0
                for i, row in result_df.iterrows():
                    if i % 3 == 0:
                        cat_count += 1
                    fmt = bg_alt if cat_count % 2 == 0 else bg_white
                    ws.write(row_idx, 0, row['Main Category'], fmt)
                    ws.write(row_idx, 1, row['Rank Type'], fmt)
                    ws.write(row_idx, 2, row['Article Code'], fmt)
                    ws.write(row_idx, 3, row['Article Description'], fmt)
                    ws.write(row_idx, 4, row['BO Type'], fmt)
                    val = row['Value']
                    if row['is_percent']:
                        v_fmt = pct_fmt_alt if cat_count % 2 == 0 else pct_fmt_white
                    else:
                        v_fmt = num_fmt_alt if cat_count % 2 == 0 else num_fmt_white
                    ws.write(row_idx, 5, val, v_fmt)
                    row_idx += 1

                ws.set_column('A:A', 35)
                ws.set_column('B:B', 30)
                ws.set_column('C:C', 15)
                ws.set_column('D:D', 55)
                ws.set_column('E:E', 15)
                ws.set_column('F:F', 15)

                # ===== Sheet 2: Category Deep Dive =====
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Building Category Deep Dive...")

                # Compute composite score
                def safe_norm(series):
                    mn, mx = series.min(), series.max()
                    if mx == mn:
                        return 0
                    return (series - mn) / (mx - mn)

                grouped['gp_norm'] = safe_norm(grouped['Weighted_GP_Pct'])
                grouped['qty_norm'] = safe_norm(grouped['Qty (1S)'])
                grouped['mom_norm'] = safe_norm(grouped['Avg_MoM_Trend'])
                grouped['pen_norm'] = safe_norm(grouped['Avg_Penetration'])
                grouped['bo_bonus'] = np.where(grouped['is_bo'], 0.15, 0)

                grouped['Composite_Score'] = (
                    0.35 * grouped['gp_norm'] +
                    0.25 * grouped['qty_norm'] +
                    0.20 * grouped['mom_norm'] +
                    0.05 * grouped['pen_norm'] +
                    grouped['bo_bonus']
                )

                # Build deep dive table
                deep_dive = grouped.sort_values(['PenetrationTracker', 'Composite_Score'], ascending=[True, False]).copy()
                deep_dive_out = deep_dive[[
                    'PenetrationTracker', 'ArticleCode', 'ArticleName', 'BO_Type',
                    'Weighted_GP_Pct', 'Unit_Selling_Price', 'Qty (1S)', 'GrossProfit',
                    'Avg_Penetration', 'Avg_MoM_Trend', 'Composite_Score', 'Outlets_Covered'
                ]].copy()
                deep_dive_out.columns = [
                    'Main Category', 'Article Code', 'Article Description', 'BO Type',
                    'Weighted GP%', 'Unit Selling Price', 'Total Qty Sold', 'Total GP$',
                    'Avg Penetration Depth', 'Avg MoM Trend', 'Composite Score', 'Outlets Covered'
                ]
                deep_dive_out.to_excel(writer, index=False, sheet_name='Category Deep Dive')

                ws2 = writer.sheets['Category Deep Dive']
                hdr_fmt2 = wb.add_format({'bold': True, 'bg_color': '#2C3E50', 'font_color': 'white', 'border': 1, 'align': 'center'})
                alt_fmt2 = wb.add_format({'bg_color': '#F2F4F4', 'border': 1})
                white_fmt2 = wb.add_format({'bg_color': '#FFFFFF', 'border': 1})
                pct_fmt2 = wb.add_format({'num_format': '0.00%', 'bg_color': '#F2F4F4', 'border': 1})
                pct_wht2 = wb.add_format({'num_format': '0.00%', 'bg_color': '#FFFFFF', 'border': 1})
                num_fmt2 = wb.add_format({'num_format': '#,##0.00', 'bg_color': '#F2F4F4', 'border': 1})
                num_wht2 = wb.add_format({'num_format': '#,##0.00', 'bg_color': '#FFFFFF', 'border': 1})
                score_fmt2 = wb.add_format({'num_format': '0.0000', 'bg_color': '#F2F4F4', 'border': 1})
                score_wht2 = wb.add_format({'num_format': '0.0000', 'bg_color': '#FFFFFF', 'border': 1})

                dd_cols = list(deep_dive_out.columns)
                for c, val in enumerate(dd_cols):
                    ws2.write(0, c, val, hdr_fmt2)

                dd_row = 1
                prev_cat = None
                for _, r in deep_dive_out.iterrows():
                    cat = r['Main Category']
                    fmt = alt_fmt2 if prev_cat != cat else white_fmt2
                    if prev_cat != cat:
                        prev_cat = cat
                        fmt = alt_fmt2

                    ws2.write(dd_row, 0, cat, fmt)
                    ws2.write(dd_row, 1, r['Article Code'], fmt)
                    ws2.write(dd_row, 2, r['Article Description'], fmt)
                    ws2.write(dd_row, 3, r['BO Type'], fmt)
                    ws2.write(dd_row, 4, r['Weighted GP%'], pct_fmt2 if prev_cat == cat else pct_wht2)
                    ws2.write(dd_row, 5, r['Unit Selling Price'], num_fmt2 if prev_cat == cat else num_wht2)
                    ws2.write(dd_row, 6, r['Total Qty Sold'], num_fmt2 if prev_cat == cat else num_wht2)
                    ws2.write(dd_row, 7, r['Total GP$'], num_fmt2 if prev_cat == cat else num_wht2)
                    ws2.write(dd_row, 8, r['Avg Penetration Depth'], pct_fmt2 if prev_cat == cat else pct_wht2)
                    ws2.write(dd_row, 9, r['Avg MoM Trend'], pct_fmt2 if prev_cat == cat else pct_wht2)
                    ws2.write(dd_row, 10, r['Composite Score'], score_fmt2 if prev_cat == cat else score_wht2)
                    ws2.write(dd_row, 11, int(r['Outlets Covered']), fmt)
                    dd_row += 1

                ws2.set_column('A:A', 35)
                ws2.set_column('B:B', 15)
                ws2.set_column('C:C', 55)
                ws2.set_column('D:D', 15)
                ws2.set_column('E:E', 15)
                ws2.set_column('F:F', 20)
                ws2.set_column('G:G', 15)
                ws2.set_column('H:H', 15)
                ws2.set_column('I:I', 20)
                ws2.set_column('J:J', 15)
                ws2.set_column('K:K', 16)
                ws2.set_column('L:L', 16)

                # ===== Sheet 3: Outlet-Level Breakdown =====
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Building Outlet-Level Breakdown...")

                # Build outlet-level breakdown in one aggregation to avoid merge conflicts
                outlet_agg = df.groupby(['PenetrationTracker', 'ArticleCode', 'ArticleName', 'BO_Type', 'SiteCodeName']).agg({
                    'Qty (1S)': 'sum',
                    'SalesAmt': 'sum',
                    'GrossProfit': 'sum',
                    'GP %': 'first',
                }).reset_index()
                outlet_agg.columns = ['Main Category', 'Article Code', 'Article Description', 'BO Type', 'Site',
                                       'Qty Sold', 'Sales Amt', 'GP$', 'Outlet GP%']
                outlet_agg['Outlet GP%'] = pd.to_numeric(outlet_agg['Outlet GP%'], errors='coerce').fillna(0) / 100

                # Add penetration and MoM in one pass using a single groupby
                agg_dict = {}
                extra_cols = []
                if pen_col in df.columns:
                    agg_dict[pen_col] = 'first'
                    extra_cols.append('Penetration %')
                if mom_col in df.columns:
                    agg_dict[mom_col] = 'first'
                    extra_cols.append('MoM Trend')

                outlet_data = outlet_agg.copy()
                if extra_cols:
                    extra_agg = df.groupby(['PenetrationTracker', 'ArticleCode', 'ArticleName', 'BO_Type', 'SiteCodeName']).agg(agg_dict).reset_index()
                    extra_agg.columns = ['Main Category', 'Article Code', 'Article Description', 'BO Type', 'Site'] + extra_cols
                    outlet_data = outlet_data.merge(extra_agg, on=['Main Category', 'Article Code', 'Article Description', 'BO Type', 'Site'], how='left')

                outlet_data = outlet_data.sort_values(['Main Category', 'Article Code', 'Site'])
                outlet_data.to_excel(writer, index=False, sheet_name='Outlet-Level Breakdown')

                ws3 = writer.sheets['Outlet-Level Breakdown']
                hdr_fmt3 = wb.add_format({'bold': True, 'bg_color': '#2C3E50', 'font_color': 'white', 'border': 1, 'align': 'center'})
                alt_fmt3 = wb.add_format({'bg_color': '#F2F4F4', 'border': 1})
                white_fmt3 = wb.add_format({'bg_color': '#FFFFFF', 'border': 1})

                ol_cols = list(outlet_data.columns)
                for c, val in enumerate(ol_cols):
                    ws3.write(0, c, val, hdr_fmt3)

                ol_row = 1
                prev_cat = None
                for _, r in outlet_data.iterrows():
                    cat = r['Main Category']
                    fmt = alt_fmt3 if prev_cat != cat else white_fmt3
                    if prev_cat != cat:
                        prev_cat = cat
                        fmt = alt_fmt3

                    for ci, cv in enumerate(ol_cols):
                        ws3.write(ol_row, ci, r[cv], fmt)
                    ol_row += 1

                ws3.set_column('A:A', 35)
                ws3.set_column('B:B', 15)
                ws3.set_column('C:C', 55)
                ws3.set_column('D:D', 15)
                ws3.set_column('E:E', 25)
                ws3.set_column('F:F', 15)
                ws3.set_column('G:G', 15)
                ws3.set_column('H:H', 12)
                ws3.set_column('I:I', 18)
                ws3.set_column('J:J', 15)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Analysis completed successfully! Saved to {output_file}")
        if enhanced_output:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Enhanced analysis saved to: {enhanced_output}")
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
    parser.add_argument('--enhanced', '-e', type=str, default=None, help="Output path for the enhanced analysis file with Category Deep Dive and Outlet-Level Breakdown sheets.")
    args = parser.parse_args()

    run_pbo_gp_analysis(args.input, args.output, args.enhanced)
