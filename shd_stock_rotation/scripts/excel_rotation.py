import pandas as pd
import sys
import argparse
from datetime import datetime
import numpy as np
import os

SKILL_VERSION = '1.0.0'
from openpyxl.styles import PatternFill, Font, Alignment

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def get_safe_filename(filepath):
    """Returns the filepath or appends _v2, _v3 if the file is currently locked/open."""
    if not os.path.exists(filepath):
        return filepath
    try:
        # Try appending to see if it's locked
        with open(filepath, 'a'):
            pass
        return filepath # Not locked, we can overwrite
    except IOError:
        # Locked! Find next available version
        name, ext = os.path.splitext(filepath)
        counter = 2
        while os.path.exists(f"{name}_v{counter}{ext}"):
            try:
                with open(f"{name}_v{counter}{ext}", 'a'):
                    return f"{name}_v{counter}{ext}"
            except IOError:
                counter += 1
        return f"{name}_v{counter}{ext}"

def format_excel_sheet(worksheet, is_summary=False):
    header_fill = PatternFill(start_color="FF000000", end_color="FF000000", fill_type="solid")
    header_font = Font(color="FFFFFFFF", bold=True)
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    # Format all cells
    for col in worksheet.columns:
        max_length = 0
        column_letter = col[0].column_letter
        header_val = str(col[0].value).strip() if col[0].value else ""
        is_desc = (header_val == "ArticleDesc")

        for idx, cell in enumerate(col):
            # Calculate width
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass

            # Apply alignment
            if idx == 0 and not is_summary:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = center_align
            elif idx > 0 or is_summary:
                if is_desc:
                    cell.alignment = left_align
                else:
                    cell.alignment = center_align

        adjusted_width = min(max_length + 2, 50)
        worksheet.column_dimensions[column_letter].width = adjusted_width

    if not is_summary:
        worksheet.auto_filter.ref = worksheet.dimensions

def run_rotation(input_file, cluster_name, store_list, sender_coverage, receiver_coverage, category_filter, poison_class=None, receiver_overrides=None, sos_filter=None, receiver_shd_limit=None, ignore_forecast=False, aging_file=None, aged_only=False, skip_sender_stores=None, priority_receivers=None, skip_receiver_stores=None):
    input_files = [f.strip() for f in input_file.split(',')]
    df_list = []
    for f in input_files:
        print(f"Loading {f} for {cluster_name}...")
        df_list.append(pd.read_excel(f))
    df = pd.concat(df_list, ignore_index=True)

    date_str = pd.Timestamp.now().strftime("%d%m%Y")

    # Filter by category
    if category_filter.upper() != 'ALL':
        df = df[df['Category'].str.upper() == category_filter.upper()].copy()
    else:
        df = df.copy()

    # Exclude standard REHAB subcategories
    if 'SubCategory' in df.columns:
        rehab_exclusions = [
            'REHAB-HOSP BED/ACCS',
            'REHAB-L/WT WHEELCHR',
            'REHAB-COMMODE CHAIR',
            'REHAB-SP WHEELCHAIR',
            'REHAB-STD WHEELCHAIR'
        ]
        df = df[~df['SubCategory'].astype(str).str.upper().isin([s.upper() for s in rehab_exclusions])].copy()

    # Filter by PoisonClass if MEDICINE is selected and poison_class is provided
    if category_filter.upper() == 'MEDICINE' and poison_class:
        if poison_class.upper() == 'BOTH':
            df = df[df['PoisonClass'].isin(['Group B', 'Group C'])].copy()
        else:
            df = df[df['PoisonClass'].str.contains(poison_class, na=False, case=False)].copy()

    # Filter by SOS if provided
    if sos_filter:
        df = df[df['SOS'].str.contains(sos_filter, na=False, case=False)].copy()

    # Filter by stores
    store_condition = df['Store'].str.contains('|'.join(store_list), na=False, case=False)
    df = df[store_condition].copy()

    if df.empty:
        print(f"No records found for {cluster_name} and category {category_filter}")
        return

    # Aging Integration
    if aging_file:
        print(f"Merging with aging data from {aging_file}...")
        df_aging = pd.read_excel(aging_file)

        # Standardize columns for merging
        # SHD: 'ArticleCode', 'Store'
        # Aging: 'Article Code', 'SiteCodeName', 'ProvisionAmount' (column 33)

        # Ensure types match
        df['ArticleCode'] = df['ArticleCode'].astype(str).str.strip()
        df_aging['Article Code'] = df_aging['Article Code'].astype(str).str.strip()
        df['Store_Key'] = df['Store'].str.strip()
        df_aging['Store_Key'] = df_aging['SiteCodeName'].str.strip()

        # Identify the AG column (ProvisionAmount)
        ag_col = 'ProvisionAmount'
        if ag_col not in df_aging.columns:
            # Fallback to column index 32 if name differs
            ag_col = df_aging.columns[32]

        # Merge
        df = df.merge(df_aging[['Article Code', 'Store_Key', ag_col]],
                     left_on=['ArticleCode', 'Store_Key'],
                     right_on=['Article Code', 'Store_Key'],
                     how='left')

        df[ag_col] = df[ag_col].fillna(0)

        if aged_only:
            # ONLY rotate out articles where ProvisionAmount > 0 in ANY store
            aged_articles = df[df[ag_col] > 0]['ArticleCode'].unique()
            df = df[df['ArticleCode'].isin(aged_articles)].copy()
            if df.empty:
                print(f"No aged stock (ProvisionAmount > 0) detected for {cluster_name}")
                return
            print(f"Found {len(df)} records belonging to aged articles for rotation.")


    # Map overrides
    overrides_dict = {}
    if receiver_overrides:
        for item in receiver_overrides.split(','):
            if ':' in item:
                s, v = item.split(':')
                overrides_dict[s.strip()] = int(v.strip())

    # Core calculations
    df['DailyDemand'] = (df['Day 1 to 30'].fillna(0) + df['Day 31 to 60'].fillna(0) + df['Day 61-90'].fillna(0)) / 90.0

    # QtyNeeded for potential receivers
    def get_target_days(row):
        store_str = str(row['Store'])
        # Extract numeric code if exists (e.g. "1536-KKJP" -> "1536")
        store_code = store_str.split('-')[0].strip()
        if store_code in overrides_dict:
            return overrides_dict[store_code]
        if store_str in overrides_dict:
            return overrides_dict[store_str]
        return receiver_coverage

    df['TargetDays'] = df.apply(get_target_days, axis=1)
    qty_needed = (df['DailyDemand'] * df['TargetDays']) - df['SOH']

    # Apply receiver SHD limit if provided
    if receiver_shd_limit is not None:
        mask = (df['SHD'] <= receiver_shd_limit) & (qty_needed > 0)
        df['QtyNeeded'] = np.where(mask, qty_needed.apply(lambda x: int(np.floor(x))), 0)
    else:
        df['QtyNeeded'] = qty_needed.apply(lambda x: int(np.floor(x)) if x > 0 else 0)

    # Senders Logic
    def calculate_available(row):
        # Rule for Aged Stock: Rotate out entirely
        if aging_file and row.get('ProvisionAmount', 0) > 0:
            return int(max(0, row['SOH']))

        if aged_only: # If we are in aged-only mode, only those with AG>0 (handled above) should rotate
            return 0

        try:
            shd = float(row['SHD'])
        except:
            shd = 0

        soh = row['SOH']
        rp_type = str(row['RP Type']).lower()
        daily_demand = row['DailyDemand']

        if shd == 9999:
            if ignore_forecast:
                keep = 0
            else:
                keep = 1 if 'forecast' in rp_type else 0
            avail = soh - keep
            return int(max(0, avail))
        elif shd >= sender_coverage:
            keep = int(np.ceil(daily_demand * sender_coverage))
            avail = soh - keep
            return int(max(0, avail))
        return 0

    df['AvailableToDrop'] = df.apply(calculate_available, axis=1)

    transfer_records = []

    for article, group in df.groupby('ArticleCode'):
        receivers = group[group['QtyNeeded'] > 0].copy()
        senders = group[group['AvailableToDrop'] > 0].copy()

        # Prevent any sender from also acting as a receiver for the same article
        receivers = receivers[~receivers['Store'].isin(senders['Store'])].copy()

        # Apply skip_receiver_stores if provided
        if skip_receiver_stores:
            skip_rcv_list = [s.strip() for s in skip_receiver_stores.split(',')]
            receivers = receivers[~receivers['Store'].str.contains('|'.join(skip_rcv_list), na=False)].copy()

        # Apply skip_sender_stores if provided
        if skip_sender_stores:
            skip_list = [s.strip() for s in skip_sender_stores.split(',')]
            senders = senders[~senders['Store'].str.contains('|'.join(skip_list), na=False)].copy()

        receivers['IsOOS'] = receivers['OOS Indicator'].apply(lambda x: 1 if str(x).strip().upper() == 'OOS' else 0)

        # Priority receivers logic
        if priority_receivers:
            priority_list = [p.strip() for p in priority_receivers.split(',')]
            receivers['IsPriority'] = receivers['Store'].apply(lambda x: 1 if any(p in str(x) for p in priority_list) else 0)
            receivers = receivers.sort_values(by=['IsOOS', 'IsPriority', 'QtyNeeded'], ascending=[False, False, False])
        else:
            receivers = receivers.sort_values(by=['IsOOS', 'QtyNeeded'], ascending=[False, False])

        senders = senders.sort_values(by=['SHD'], ascending=False)

        if receivers.empty or senders.empty:
            continue

        receiver_idx = 0
        sender_idx = 0

        senders_list = senders.to_dict('records')
        receivers_list = receivers.to_dict('records')

        while sender_idx < len(senders_list) and receiver_idx < len(receivers_list):
            s = senders_list[sender_idx]
            r = receivers_list[receiver_idx]

            qty_can_send = s['AvailableToDrop']
            qty_needed = r['QtyNeeded']

            if qty_can_send <= 0:
                sender_idx += 1
                continue
            if qty_needed <= 0:
                receiver_idx += 1
                continue

            transfer_qty = int(min(qty_can_send, qty_needed))
            reason = "Aged Stock" if s.get('ProvisionAmount', 0) > 0 else ("Deadstock Clearance" if s['SHD'] == 9999 else "Slow Stock")

            if transfer_qty > 0:
                record = {
                    'ArticleCode': s['ArticleCode'],
                    'ArticleDesc': s['ArticleDesc'],
                    'Category': s['Category'],
                    'Reason': reason,
                    'Sender Store': s['Store'],
                    'Sender SOH': s['SOH'],
                    'Sender SHD': s['SHD'],
                    'Receiver Store': r['Store'],
                    'Receiver SOH': r['SOH'],
                    'Receiver SHD': r['SHD'],
                    'OOS': "YES" if r['IsOOS'] == 1 else "NO",
                    'Transfer Qty': transfer_qty,
                    'SOS': s['SOS'] # Capture SOS from sender for reporting
                }
                if 'SubCategory' in s:
                    record['SubCategory'] = s['SubCategory']
                transfer_records.append(record)

            senders_list[sender_idx]['AvailableToDrop'] -= transfer_qty
            receivers_list[receiver_idx]['QtyNeeded'] -= transfer_qty

            if senders_list[sender_idx]['AvailableToDrop'] <= 0:
                sender_idx += 1
            if receivers_list[receiver_idx]['QtyNeeded'] <= 0:
                receiver_idx += 1

    if len(transfer_records) == 0:
        print(f"No transfers found for {cluster_name}")
        return

    res_df = pd.DataFrame(transfer_records)

    cols_order = ['ArticleCode', 'ArticleDesc', 'Category']
    if 'SubCategory' in res_df.columns:
        cols_order.append('SubCategory')

    cols_order.extend([
         'Reason', 'Sender Store', 'Sender SOH', 'Sender SHD',
         'Receiver Store', 'Receiver SOH', 'Receiver SHD',
         'OOS', 'Transfer Qty', 'SOS'
    ])
    res_df = res_df[cols_order]

    file1_base = f"C:\\Users\\USER\\Downloads\\{cluster_name} Rotation {date_str}.xlsx"
    file1 = get_safe_filename(file1_base)

    with pd.ExcelWriter(file1, engine='openpyxl') as writer:
        res_df.to_excel(writer, index=False, sheet_name='Rotation')
        format_excel_sheet(writer.sheets['Rotation'])
    print(f"Saved {file1}")

    log_df = res_df.copy()
    log_df['Date'] = datetime.now().strftime("%Y-%m-%d")
    log_cols = ['Date', 'Sender Store', 'Receiver Store', 'ArticleCode', 'ArticleDesc', 'Transfer Qty']
    log_df = log_df[log_cols]

    total_lines = len(log_df)
    deadstock_lines = len(res_df[res_df['Reason'] == 'Deadstock Clearance'])
    oos_lines = len(res_df[res_df['OOS'] == 'YES'])

    dc_lines = len(res_df[res_df['SOS'] == 'DC'])
    dsp_lines = len(res_df[res_df['SOS'] == 'DSP'])

    summary_data = {
        'Metric': ['Total lines moved', 'Total OOS lines covered', 'Total deadstock (9999) lines moved', 'Total DC lines', 'Total DSP lines'],
        'Value': [total_lines, oos_lines, deadstock_lines, dc_lines, dsp_lines]
    }
    summary_df = pd.DataFrame(summary_data)

    # SOS Split Stats by Outlet
    def get_outlet_sos_stats(df, store_col, qty_name):
        pivot = df.groupby([store_col, 'SOS']).size().unstack(fill_value=0).reset_index()
        for col in ['DC', 'DSP']:
            if col not in pivot.columns:
                pivot[col] = 0
        pivot = pivot[[store_col, 'DC', 'DSP']]
        pivot.columns = [store_col, f'DC {qty_name}', f'DSP {qty_name}']
        pivot[f'Total {qty_name}'] = pivot[f'DC {qty_name}'] + pivot[f'DSP {qty_name}']
        return pivot

    sender_stats = get_outlet_sos_stats(res_df, 'Sender Store', 'Sent')
    receiver_stats = get_outlet_sos_stats(res_df, 'Receiver Store', 'Received')

    file2_base = f"C:\\Users\\USER\\Downloads\\{cluster_name} Rotation_History_Summary {date_str}.xlsx"
    file2 = get_safe_filename(file2_base)

    with pd.ExcelWriter(file2, engine='openpyxl') as writer:
        log_df.to_excel(writer, sheet_name='Movement Log', index=False)

        # Write to summary sheet
        summary_df.to_excel(writer, sheet_name='Summary', index=False, startrow=0, startcol=0)
        sender_stats.to_excel(writer, sheet_name='Summary', index=False, startrow=len(summary_df) + 2, startcol=0)
        receiver_stats.to_excel(writer, sheet_name='Summary', index=False, startrow=len(summary_df) + 2, startcol=len(sender_stats.columns) + 1)

        for sheet_name in writer.sheets:
            format_excel_sheet(writer.sheets[sheet_name], is_summary=(sheet_name == 'Summary'))

    print(f"Saved {file2}")

if __name__ == "__main__":
    print(f"SHD Stock Rotation v{SKILL_VERSION}")
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--cluster', required=True)
    parser.add_argument('--stores', required=True)
    parser.add_argument('--sender_coverage', type=int, default=120)
    parser.add_argument('--receiver_coverage', type=int, default=120)
    parser.add_argument('--receiver_overrides', type=str, default=None)
    parser.add_argument('--poison_class', type=str, default=None)
    parser.add_argument('--sos', type=str, default=None)
    parser.add_argument('--receiver_shd_limit', type=int, default=30)
    parser.add_argument('--ignore_forecast', action='store_true', default=False)
    parser.add_argument('--category', required=True)
    parser.add_argument('--aging', type=str, default=None)
    parser.add_argument('--aged_only', action='store_true', default=False)
    parser.add_argument('--skip_sender_stores', type=str, default=None)
    parser.add_argument('--priority_receivers', type=str, default=None)
    parser.add_argument('--skip_receiver_stores', type=str, default=None)
    args = parser.parse_args()

    run_rotation(
        args.input,
        args.cluster,
        args.stores.split(','),
        args.sender_coverage,
        args.receiver_coverage,
        args.category,
        args.poison_class,
        args.receiver_overrides,
        args.sos,
        args.receiver_shd_limit,
        args.ignore_forecast,
        args.aging,
        args.aged_only,
        args.skip_sender_stores,
        args.priority_receivers,
        args.skip_receiver_stores
    )
