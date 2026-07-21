import pdfplumber
import re
import os
import pandas as pd
import argparse
import requests
from io import StringIO

# ─────────────────────────────────────────────
# Excel config lookup: filename keyword → sheet/column config
# Add new Excel layouts here as the skill grows.
# ─────────────────────────────────────────────
EXCEL_CONFIGS = {
    "Sabah Vaccination Program": {
        "sheet": "Master Tracking",
        "name_col": 3,
        "id_col": 4,
        "outlet_code_col": 2,
        "outlet_name_col": 13
    },
    "Patient Registration Form": {
        "sheet": "Patient List",
        "name_col": 3,
        "id_col": 4,
        "outlet_code_col": 10
    }
}

# ─────────────────────────────────────────────
# Google Sheets CSV URL config
# Keys are human-readable labels; values are dicts with url + col mappings.
# When the user provides a URL, we auto-detect by matching the URL or use defaults.
# ─────────────────────────────────────────────
GSHEET_DEFAULTS = {
    "name_col": "Name",
    "id_col": "IC/Passport",
    "outlet_code_col": "Site",
    "outlet_name_col": "Clinic"
}


def normalize_id(val):
    """Strip all non-digit characters from an ID."""
    if pd.isna(val):
        return ""
    return re.sub(r'\D', '', str(val))


def is_url(s):
    return s.startswith("http://") or s.startswith("https://")


def load_from_gsheet_url(url, col_config):
    """
    Load a Google Sheet published as CSV and return a lookup dict.
    col_config keys: name_col, id_col, outlet_code_col, outlet_name_col (all column names as strings)
    """
    # Force CSV export format if a regular Sheets URL is provided
    if "docs.google.com/spreadsheets" in url and "tqx=out:csv" not in url:
        # Extract spreadsheet ID and sheet name if present
        # Handle both edit and published URLs
        if "/edit" in url:
            sheet_id = url.split("/d/")[1].split("/")[0]
            gid = ""
            if "gid=" in url:
                gid = url.split("gid=")[1].split("&")[0].split("#")[0]
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            if gid:
                csv_url += f"&gid={gid}"
        elif "pub?gid=" in url or "pub?" in url:
            # Already a publish URL, just force csv
            csv_url = url.replace("output=html", "output=csv").replace("output=pdf", "output=csv")
            if "output=" not in csv_url:
                csv_url += "&output=csv"
        else:
            csv_url = url
    else:
        csv_url = url

    resp = requests.get(csv_url, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))

    lookup_by_id = {}
    lookup_by_name = {}

    name_col = col_config.get("name_col", GSHEET_DEFAULTS["name_col"])
    id_col = col_config.get("id_col", GSHEET_DEFAULTS["id_col"])
    outlet_code_col = col_config.get("outlet_code_col", GSHEET_DEFAULTS["outlet_code_col"])
    outlet_name_col = col_config.get("outlet_name_col", GSHEET_DEFAULTS.get("outlet_name_col", outlet_code_col))

    for _, row in df.iterrows():
        try:
            norm_id = normalize_id(row.get(id_col, ""))
            name = str(row.get(name_col, "")).strip()
            outlet_code = str(row.get(outlet_code_col, "")).strip()
            outlet_name = str(row.get(outlet_name_col, outlet_code)).strip()

            info = {
                "OutletCode": outlet_code,
                "OutletName": outlet_name,
                "NameInExcel": name,
                "Source": "Google Sheets"
            }
            if norm_id:
                lookup_by_id[norm_id] = info
            if name and name.lower() != "nan":
                lookup_by_name[name.upper()] = info
        except Exception:
            continue

    return lookup_by_id, lookup_by_name


def load_from_excel(filepath, config):
    """Load a local Excel file and return lookup dicts."""
    lookup_by_id = {}
    lookup_by_name = {}

    df = pd.read_excel(filepath, sheet_name=config["sheet"], header=None)

    for _, row in df.iterrows():
        raw_id = row[config["id_col"]]
        norm_id = normalize_id(raw_id)
        name = str(row[config["name_col"]]).strip()
        outlet_code = str(row[config["outlet_code_col"]]).strip()
        outlet_name = str(row.get(config.get("outlet_name_col", config["outlet_code_col"]), outlet_code)).strip()

        info = {
            "OutletCode": outlet_code,
            "OutletName": outlet_name,
            "NameInExcel": name,
            "Source": os.path.basename(filepath)
        }
        if norm_id:
            lookup_by_id[norm_id] = info
        if name and name.lower() != "nan":
            lookup_by_name[name.upper()] = info

    return lookup_by_id, lookup_by_name


def resolve_excel_config(filepath):
    """Auto-detect the Excel config based on filename keywords."""
    basename = os.path.basename(filepath)
    for keyword, config in EXCEL_CONFIGS.items():
        if keyword.lower() in basename.lower():
            return config
    return None


def extract_from_pdfs(pdf_files):
    """Extract patient entries from PDF invoices."""
    all_patients = []
    pattern = re.compile(r'(\d{10,14})\s+([A-Z][A-Z\s\./\(\)\-\&\@]+?)\s+\d+\.\d+')

    for f in pdf_files:
        if not os.path.exists(f):
            print(f"  [WARN] PDF not found: {f}")
            continue
        with pdfplumber.open(f) as pdf:
            for p_idx, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    for line in text.split('\n'):
                        match = pattern.search(line)
                        if match:
                            all_patients.append({
                                'ID': match.group(1),
                                'Name': match.group(2).strip(),
                                'Source': os.path.basename(f),
                                'Page': p_idx + 1,
                                'RawLine': line
                            })
    return all_patients


def build_lookup(sources, gsheet_col_config=None):
    """
    Build a unified lookup from a mix of local Excel files and Google Sheet URLs.
    sources: list of file paths or URLs
    """
    combined_id = {}
    combined_name = {}

    for src in sources:
        if is_url(src):
            print(f"  [GSHEET] Loading: {src}")
            col_config = gsheet_col_config or {}
            id_lookup, name_lookup = load_from_gsheet_url(src, col_config)
        else:
            config = resolve_excel_config(src)
            if not config:
                print(f"  [WARN] No config found for {src}, skipping.")
                continue
            print(f"  [EXCEL] Loading: {os.path.basename(src)}")
            id_lookup, name_lookup = load_from_excel(src, config)

        combined_id.update(id_lookup)
        combined_name.update(name_lookup)

    return combined_id, combined_name


def generate_report(pdf_patients, lookup_id, lookup_name, output_path):
    """Map patients and write the Excel report."""
    results = []
    for p in pdf_patients:
        norm_id = normalize_id(p['ID'])
        info = lookup_id.get(norm_id)
        match_status = "Found"
        if not info:
            info = lookup_name.get(p['Name'].upper())
            match_status = "Found (Name Match)" if info else "MISSING IN EXCEL"

        results.append({
            **p,
            'OutletCode': info['OutletCode'] if info else "N/A",
            'OutletName': info['OutletName'] if info else "N/A",
            'MatchStatus': match_status
        })

    df = pd.DataFrame(results)
    if df.empty:
        print("No patients found in PDFs.")
        return

    df['Is_Duplicated_In_PDF'] = df.duplicated(subset=['ID'], keep=False)
    df = df.sort_values(by=['MatchStatus', 'Is_Duplicated_In_PDF'], ascending=[True, False])
    df.to_excel(output_path, index=False)

    total = len(df)
    missing = len(df[df['MatchStatus'] == 'MISSING IN EXCEL'])
    dupes = len(df[df['Is_Duplicated_In_PDF']])

    print(f"\n[OK] Report saved: {output_path}")
    print(f"   Total patients   : {total}")
    print(f"   Missing in Excel : {missing}")
    print(f"   Duplicated in PDF: {dupes}")

    if missing > 0:
        print("\n[WARN] MISSING PATIENTS:")
        print(df[df['MatchStatus'] == 'MISSING IN EXCEL'][['ID', 'Name', 'Source']].to_string(index=False))

    if dupes > 0:
        print("\n[WARN] DUPLICATED ENTRIES:")
        print(df[df['Is_Duplicated_In_PDF']][['ID', 'Name', 'Source']].to_string(index=False))


def main():
    parser = argparse.ArgumentParser(
        description="Map patients from PDF invoices to vaccination tracking sheets (Excel or Google Sheets URL)."
    )
    parser.add_argument(
        "--pdfs", nargs="+", required=True,
        help="Paths to PDF invoice files"
    )
    parser.add_argument(
        "--sources", nargs="+", required=True,
        help="Local Excel file paths OR Google Sheets CSV publish URLs (mix allowed)"
    )
    parser.add_argument(
        "--output", default="Patient_Outlet_Mapping_Report.xlsx",
        help="Output report path (default: Patient_Outlet_Mapping_Report.xlsx)"
    )

    args = parser.parse_args()

    print("[PDF] Extracting patients from PDFs...")
    patients = extract_from_pdfs(args.pdfs)
    print(f"   Found {len(patients)} patient entries.")

    print("\n[DATA] Loading tracking sources...")
    lookup_id, lookup_name = build_lookup(args.sources)
    print(f"   Loaded {len(lookup_id)} ID entries, {len(lookup_name)} name entries.")

    print("\n[MAP] Mapping patients...")
    generate_report(patients, lookup_id, lookup_name, args.output)


if __name__ == "__main__":
    main()
