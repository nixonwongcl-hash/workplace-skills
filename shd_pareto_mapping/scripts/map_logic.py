import pandas as pd
import os
import sys
import argparse

def log(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            print(msg.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding))
        except:
            print(str(msg).encode('ascii', errors='replace').decode('ascii'))
    sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser(description='Map Pareto data to SHD report.')
    parser.add_argument('--shd', required=True, help='Path to SHD Excel file')
    parser.add_argument('--pareto', required=True, help='Path to Pareto Excel file')
    parser.add_argument('--output', required=True, help='Path to output Excel file')
    args = parser.parse_args()

    shd_path = args.shd
    pareto_path = args.pareto
    output_path = args.output

    log(f"Loading Pareto: {os.path.basename(pareto_path)}")
    df_pareto = pd.read_excel(pareto_path)
    
    log(f"Loading SHD: {os.path.basename(shd_path)}")
    try:
        # Use calamine if available for speed, fallback to openpyxl
        df_shd = pd.read_excel(shd_path, engine='calamine')
    except:
        df_shd = pd.read_excel(shd_path, engine='openpyxl')

    log("Standardizing keys...")
    df_pareto['ArticleCode_key'] = df_pareto['Article Code'].astype(str).str.strip()
    df_pareto['SiteCode_key'] = df_pareto['SiteCode'].astype(str).str.strip()

    # Extract SiteCode from SHD Store column
    df_shd['SiteCode_key'] = df_shd['Store'].astype(str).str.split(' - ').str[0].str.strip()
    df_shd['ArticleCode_key'] = df_shd['ArticleCode'].astype(str).str.strip()

    log("Creating description lookup...")
    desc_lookup = df_shd[['ArticleCode_key', 'ArticleDesc']].drop_duplicates('ArticleCode_key').set_index('ArticleCode_key')['ArticleDesc']

    log("Merging Pareto data into SHD...")
    cols_to_map = ['CombinedPareto']
    # Ensure these columns exist in Pareto
    available_cols = [c for c in cols_to_map if c in df_pareto.columns]
    df_pareto_subset = df_pareto[['ArticleCode_key', 'SiteCode_key'] + available_cols]

    df_mapped_shd = df_shd.merge(
        df_pareto_subset,
        on=['ArticleCode_key', 'SiteCode_key'],
        how='left'
    )

    log("Identifying unmatched articles for Summary...")
    df_pareto_check = df_pareto.merge(
        df_shd[['ArticleCode_key', 'SiteCode_key']], 
        on=['ArticleCode_key', 'SiteCode_key'], 
        how='left', 
        indicator=True
    )
    unmatched = df_pareto_check[df_pareto_check['_merge'] == 'left_only'].copy()

    # Add Description to unmatched items
    unmatched['Article Description'] = unmatched['ArticleCode_key'].map(desc_lookup)
    unmatched['Article Description'] = unmatched['Article Description'].fillna("Not found in SHD")

    # Select columns for Summary
    summary_cols = ['Article Code', 'Article Description', 'NewListing', 'SiteCode']
    # Filter to only existing columns in Pareto
    actual_summary_cols = [c for c in summary_cols if c in unmatched.columns or c == 'Article Description']
    df_summary = unmatched[actual_summary_cols]

    # Clean up
    df_mapped_shd.drop(columns=['ArticleCode_key', 'SiteCode_key'], inplace=True)

    log(f"Saving to {output_path}...")
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        def write_sheet(df, sheet_name, left_align_cols):
            # Write data starting at row 1 (excluding headers)
            df.to_excel(writer, index=False, sheet_name=sheet_name, header=False, startrow=1)
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]
            
            # Define formats
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': False,
                'valign': 'vcenter',
                'align': 'center',
                'fg_color': '#000000',
                'font_color': '#FFFFFF',
                'border': 1
            })
            left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter'})
            center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
            
            # Write headers manually at row 0
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                
            # Enable auto-filter
            worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
            
            # Set row height for header
            worksheet.set_row(0, 24)
            
            # Alignments & autofit columns
            for col_num, col_name in enumerate(df.columns):
                fmt = left_format if col_name in left_align_cols else center_format
                
                # Find max length of cell contents
                max_len = len(str(col_name))
                for val in df[col_name]:
                    if pd.notna(val):
                        val_str = str(val)
                        if val_str.endswith('.0') and isinstance(val, (int, float)):
                            val_str = str(int(val))
                        max_len = max(max_len, len(val_str))
                
                # Set column width with padding
                worksheet.set_column(col_num, col_num, max_len + 3, fmt)

        write_sheet(df_mapped_shd, 'Mapped_SHD', ['ArticleDesc'])
        write_sheet(df_summary, 'Summary', ['Article Description'])

    log("Done!")
    log(f"Total Pareto items: {len(df_pareto)}")
    log(f"Mapped rows in SHD: {df_mapped_shd[available_cols[0]].notna().sum() if available_cols else 'N/A'}")
    log(f"Unmatched items in Summary: {len(df_summary)}")

if __name__ == "__main__":
    main()
