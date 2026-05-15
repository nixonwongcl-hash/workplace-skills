import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

def main():
    if len(sys.argv) < 3:
        print("Usage: python clearance_rotation.py <clearance_file.xlsx> <shd_file.xlsx>")
        sys.exit(1)

    clearance_path = sys.argv[1]
    shd_path = sys.argv[2]
    
    cluster_1 = ['KKDG', 'KKIN', 'KKCM', 'KKGM', 'KKJP', 'KKDA', 'SAKN', 'SABF', 'SATR', 'KKLD']
    cluster_2 = ['SALD', 'SATW']
    
    print(f"Reading SHD file: {shd_path}")
    df_shd = pd.read_excel(shd_path, engine='calamine')
    
    df_shd['Store Code'] = df_shd['Store'].astype(str).str.split(' - ').str[-1].str.strip()
    df_shd['ArticleCode_Str'] = df_shd['ArticleCode'].astype(str).str.split('.').str[0].str.strip()
    
    # Pre-calculate SHD metrics for receivers
    for col in ['Day 1 to 30', 'Day 31 to 60', 'Day 61-90']:
        df_shd[col] = pd.to_numeric(df_shd[col], errors='coerce').fillna(0)
    df_shd['Daily Demand'] = (df_shd['Day 1 to 30'] + df_shd['Day 31 to 60'] + df_shd['Day 61-90']) / 90
    df_shd['SOH_Num'] = pd.to_numeric(df_shd['SOH'], errors='coerce').fillna(0)
    df_shd['SHD_Num'] = pd.to_numeric(df_shd['SHD'], errors='coerce').fillna(9999)
    df_shd['Target Qty'] = np.maximum(0, np.ceil(df_shd['Daily Demand'] * 120 - df_shd['SOH_Num']))

    # Store Poison Class info for articles
    poison_map = df_shd.drop_duplicates('ArticleCode_Str').set_index('ArticleCode_Str')['PoisonClass'].to_dict()

    # Load 9999 listing
    poison_9999_path = r"C:\Users\USER\Downloads\SABAH REGION POISON 9999.xlsx"
    print(f"Reading 9999 listing: {poison_9999_path}")
    df_9999 = pd.read_excel(poison_9999_path)
    # Standardize Article No in 9999 list
    df_9999['Art_Clean'] = df_9999['ARTICLE NO'].astype(str).str.split('.').str[0].str.strip()
    valid_9999_arts = set(df_9999['Art_Clean'].unique())

    print(f"Reading clearance file: {clearance_path}")
    xls = pd.ExcelFile(clearance_path)
    
    out_name = f"Non_Returnable_Clearance_Combined_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx"
    out_dir = r"C:\Users\USER\Downloads"
    out_path = os.path.join(out_dir, out_name)
    
    current_date = datetime(2026, 5, 1)

    with pd.ExcelWriter(out_path, engine='xlsxwriter') as writer:
        workbook = writer.book
        header_format = workbook.add_format({'bg_color': 'black', 'font_color': 'white', 'bold': True, 'align': 'center', 'valign': 'vcenter'})

        for sheet_name in xls.sheet_names:
            print(f"Processing outlet tab: {sheet_name}")
            sender_code = str(sheet_name).strip().upper()
            df_clear = pd.read_excel(xls, sheet_name=sheet_name, header=None, dtype=str)
            
            if df_clear.empty:
                continue

            # Find header row
            header_idx = -1
            for i, row in df_clear.iterrows():
                if row.astype(str).str.contains('article', case=False).any():
                    header_idx = i
                    break
                    
            if header_idx == -1:
                print(f"Skipping {sheet_name}: No article column found.")
                continue
                
            # Set header and drop above
            df_clear.columns = df_clear.iloc[header_idx].values
            df_clear = df_clear.iloc[header_idx+1:].reset_index(drop=True)

            cols = df_clear.columns.astype(str).str.lower()
            art_cols = df_clear.columns[cols.str.contains('article')]
            exp_cols = df_clear.columns[cols.str.contains('expiry')]
            qty_cols = df_clear.columns[cols.str.contains('qty') | cols.str.contains('quantity')]
            
            if len(art_cols) == 0:
                print(f"Skipping {sheet_name}: No article column found after header extraction.")
                continue
            
            art_col = art_cols[0]
            exp_col = exp_cols[0] if len(exp_cols) > 0 else None
            qty_col = qty_cols[0] if len(qty_cols) > 0 else None

            df_clear['Article No'] = df_clear[art_col].astype(str).str.split('.').str[0].str.strip()
            
            results = []
            
            for idx, row in df_clear.iterrows():
                art = row['Article No']
                qty = pd.to_numeric(row[qty_col], errors='coerce') if qty_col else 0
                if pd.isna(qty): qty = 0
                
                exp_val = row[exp_col] if exp_col else None
                is_clearance = False
                months_diff = 999
                if pd.notna(exp_val):
                    try:
                        # If pandas already converted to datetime, but possibly swapped D/M
                        if isinstance(exp_val, datetime):
                            exp_date = exp_val
                        else:
                            s_exp = str(exp_val).strip()
                            exp_date = None
                            # Prioritize DD/MM for Malaysia, then handle MM/YY and MM/YYYY
                            for fmt in ['%d/%m/%Y', '%d/%m/%y', '%m/%Y', '%m/%y', '%Y-%m-%d']:
                                try:
                                    exp_date = datetime.strptime(s_exp, fmt)
                                    break
                                except:
                                    continue
                            
                            if not exp_date:
                                # Fallback for cases like '1.7.2026' or '01.07.2026'
                                s_exp_clean = s_exp.replace('.', '/').replace('-', '/')
                                for fmt in ['%d/%m/%Y', '%d/%m/%y', '%m/%Y', '%m/%y']:
                                    try:
                                        exp_date = datetime.strptime(s_exp_clean, fmt)
                                        break
                                    except:
                                        continue

                            if not exp_date:
                                raise ValueError("Invalid date format")
                        
                        # If year is 2 digits and parsed as 19xx, fix to 20xx
                        if exp_date.year < 100:
                            exp_date = exp_date.replace(year=exp_date.year + 2000)
                        elif exp_date.year < 1900:
                             # For very weird short dates that might be parsed into the future or past
                             pass
                        
                        months_diff = (exp_date.year - current_date.year) * 12 + exp_date.month - current_date.month
                        if months_diff <= 3:
                            is_clearance = True
                        # Force back to DD/MM/YYYY string to avoid Excel regional mangling
                        row[exp_col] = exp_date.strftime('%d/%m/%Y')
                    except:
                        months_diff = 999 
                        pass 
                else:
                    months_diff = 999

                p_class = str(poison_map.get(art, 'Unknown')).upper()
                is_poison_bc = ('GROUP B' in p_class or 'GROUP C' in p_class)
                in_9999 = (art in valid_9999_arts)

                # Find potential receivers
                df_art = df_shd[(df_shd['ArticleCode_Str'] == art) & (df_shd['Store Code'] != sender_code)].copy()
                df_art = df_art[(df_art['SHD_Num'] <= 30) & (df_art['Daily Demand'] > 0)]
                
                best_receiver = None
                if not df_art.empty:
                    df_c1 = df_art[df_art['Store Code'].isin(cluster_1)]
                    df_c2 = df_art[df_art['Store Code'].isin(cluster_2)]
                    potential_pool = df_c1 if sender_code in cluster_1 else (df_c2 if not df_c2.empty else df_c1)
                    if not potential_pool.empty:
                        best_receiver = potential_pool.sort_values(by=['Daily Demand', 'SHD_Num'], ascending=[False, True]).iloc[0]

                out_row = row.to_dict()
                out_row['Status'] = '<= 3m (Clearance)' if is_clearance else '> 3m (Rotation)'
                
                rec_store = best_receiver['Store Code'] if best_receiver is not None else None
                transfer_qty = min(best_receiver['Target Qty'], qty) if best_receiver is not None else 0
                
                out_row['Suggested Receiver'] = rec_store if rec_store else 'None'
                out_row['Receiver SHD'] = best_receiver['SHD_Num'] if best_receiver is not None else 'N/A'
                out_row['Suggested Transfer Qty'] = transfer_qty

                # Remark Generation
                remark_parts = []

                # 9999 prefix for Group B/C items in 9999 list
                if is_poison_bc and in_9999:
                    remark_parts.append("[Refer to Sabah Region 9999 List]")

                # --- Clearance items (expiry <= 3 months) ---
                if is_clearance:
                    if months_diff < 1:
                        # Expiring within this month
                        if 'NON-POISON' in p_class or 'NON POISON' in p_class:
                            remark_parts.append("Continue sell under clearance price. GWP to customer.")
                        elif 'GROUP B' in p_class:
                            remark_parts.append("Continue sell under clearance price. Submit monthly write off with proof.")
                        elif 'GROUP C' in p_class:
                            remark_parts.append("DISPENSIBLE! Continue sell under clearance price, no write off allowed.")
                        else:
                            remark_parts.append("Continue sell under clearance price. GWP to customer.")
                    elif months_diff < 2:
                        # 1-2 months left
                        if 'GROUP B' in p_class:
                            remark_parts.append("Continue sell under clearance price. Submit monthly write off with proof.")
                        elif 'GROUP C' in p_class:
                            remark_parts.append("DISPENSIBLE! Continue sell under clearance price, no write off allowed.")
                        else:
                            remark_parts.append("Continue sell under clearance price. GWP to customer when nearing 1 month.")
                    else:
                        # 2-3 months left
                        if 'GROUP B' in p_class:
                            remark_parts.append("Continue sell under clearance price. Submit monthly write off with proof.")
                        elif 'GROUP C' in p_class:
                            remark_parts.append("DISPENSIBLE! Continue sell under clearance price, no write off allowed.")
                        else:
                            remark_parts.append("Continue sell under clearance price.")

                    # For ALL clearance items: if a receiver exists, always suggest them
                    if rec_store:
                        remark_parts.append(f"(Suggested receiver: {rec_store}, Qty: {int(transfer_qty)}, Contact for consent)")

                # --- Rotation items (expiry > 3 months) ---
                else:
                    if rec_store:
                        remark_parts.append(f"Rotate to {rec_store}, Qty: {int(transfer_qty)}")
                    else:
                        remark_parts.append("Continue sell under clearance price.")

                # Group C without receiver: always mark DISPENSIBLE
                if 'GROUP C' in p_class and not rec_store:
                    if "DISPENSIBLE!" not in " ".join(remark_parts):
                        remark_parts.insert(0, "DISPENSIBLE!")

                out_row['Remark'] = " ".join(remark_parts).strip()
                results.append(out_row)

            df_res = pd.DataFrame(results)
            # Ensure safe sheet name (max 31 chars)
            safe_sheet_name = str(sheet_name)[:31]
            df_res.to_excel(writer, sheet_name=safe_sheet_name, index=False)
            worksheet = writer.sheets[safe_sheet_name]
            
            for col_num, value in enumerate(df_res.columns.values):
                worksheet.write(0, col_num, value, header_format)
                col_len = max(df_res[value].astype(str).map(len).max(), len(str(value))) + 2
                worksheet.set_column(col_num, col_num, min(col_len, 50))
                
            worksheet.autofilter(0, 0, len(df_res), len(df_res.columns) - 1)

    print(f"Completed! Saved all tabs to: {out_path}")

if __name__ == '__main__':
    main()
