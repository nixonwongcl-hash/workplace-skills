import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
import os

def generate_recall_report():
    input_file = r"C:\Users\USER\Downloads\SHD 22052026.xlsx"
    output_filename = "Recall_Report_22052026.xlsx"
    workspace_dir = r"c:\Users\USER\playground\azure-radiation" # Will use current folder but let's define absolute
    output_path = os.path.join(r"c:\Users\USER\.gemini\antigravity\playground\azure-radiation", output_filename)
    downloads_path = os.path.join(r"C:\Users\USER\Downloads", output_filename)

    print(f"Reading {input_file} using calamine engine...")
    df = pd.read_excel(input_file, engine="calamine")
    print(f"Loaded {len(df)} rows.")

    target_articles = [10002187, 10002356, 10000636, 10010761]
    
    # Filter target articles
    filtered_df = df[df['ArticleCode'].isin(target_articles)].copy()
    print(f"Found {len(filtered_df)} matches before SOH filtering.")

    # Filter SOH > 0
    filtered_df = filtered_df[filtered_df['SOH'] > 0].copy()
    print(f"Found {len(filtered_df)} matches after filtering SOH > 0.")

    # Define reasons map
    reasons_map = {
        10002187: "Return to Vendor",
        10002356: "Return to Vendor",
        10000636: "Short Expiry (08/2026)",
        10010761: "Wrong Label"
    }

    # Add Reason column
    filtered_df['Reason'] = filtered_df['ArticleCode'].map(reasons_map)

    # Rename Store to 'Outlet Involved'
    filtered_df = filtered_df.rename(columns={'Store': 'Outlet Involved'})

    # Keep only the required columns in the exact order:
    # 1. ArticleCode, 2. ArticleDesc, 3. Category, 4. Reason, 5. Outlet Involved, 6. SOH
    final_cols = ['ArticleCode', 'ArticleDesc', 'Category', 'Reason', 'Outlet Involved', 'SOH']
    final_df = filtered_df[final_cols].copy()

    # Sort for neatness (by ArticleCode, then Outlet Involved)
    final_df = final_df.sort_values(by=['ArticleCode', 'Outlet Involved'])

    # Write to Excel
    print(f"Writing raw data to {output_path}...")
    final_df.to_excel(output_path, index=False)

    # Apply formatting using openpyxl
    print("Applying styling using openpyxl...")
    wb = openpyxl.load_workbook(output_path)
    ws = wb.active
    ws.title = "Recall Report"

    # Style definitions
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="000000", end_color="000000", fill_type="solid")
    
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    data_font = Font(name="Arial", size=10)

    # Apply headers formatting
    for col_idx in range(1, 7):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    # Apply body formatting
    # Headers order: ArticleCode (1), ArticleDesc (2), Category (3), Reason (4), Outlet Involved (5), SOH (6)
    for row in range(2, ws.max_row + 1):
        for col in range(1, 7):
            cell = ws.cell(row=row, column=col)
            cell.font = data_font
            
            # Formatting SOH column as integer if applicable
            if col == 6:
                cell.number_format = '#,##0'
            
            # Alignments
            if col == 2:  # ArticleDesc is left aligned
                cell.alignment = left_align
            else:  # All other columns are center aligned
                cell.alignment = center_align

    # Apply filters across all headers
    ws.auto_filter.ref = f"A1:F{ws.max_row}"

    # Auto-optimize column widths
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            val = cell.value
            if val is not None:
                max_len = max(max_len, len(str(val)))
        # Add a little extra padding for neatness
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Save to workspace
    wb.save(output_path)
    print(f"Successfully created formatted report in workspace: {output_path}")

    # Copy to Downloads folder as well so user can access it easily
    import shutil
    try:
        shutil.copy2(output_path, downloads_path)
        print(f"Successfully copied report to Downloads: {downloads_path}")
    except Exception as e:
        print(f"Failed to copy to Downloads: {e}")

if __name__ == "__main__":
    generate_recall_report()
