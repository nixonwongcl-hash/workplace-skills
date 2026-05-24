import os
import sys
import glob
import json
import pandas as pd
from datetime import datetime, timedelta

def log(msg):
    print(msg, file=sys.stderr)
    sys.stderr.flush()

def scan_files():
    cwd = r"c:\Users\USER\.gemini\antigravity\playground\azure-radiation"
    downloads = r"C:\Users\USER\Downloads"
    
    file_patterns = ["*.xlsx", "*.xlsm", "*.xls", "*.csv"]
    scanned_files = []
    
    # Gather files
    for folder in [cwd, downloads]:
        if not os.path.exists(folder):
            continue
        for pattern in file_patterns:
            for file_path in glob.glob(os.path.join(folder, pattern)):
                try:
                    mtime = os.path.getmtime(file_path)
                    mod_time = datetime.fromtimestamp(mtime)
                    # Prioritize files modified in the last 14 days
                    if datetime.now() - mod_time < timedelta(days=14):
                        scanned_files.append({
                            "path": file_path,
                            "name": os.path.basename(file_path),
                            "folder": "Downloads" if folder == downloads else "Workspace",
                            "mtime": mtime,
                            "date": mod_time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                except Exception as e:
                    log(f"Error scanning metadata for {file_path}: {e}")
                    
    # Sort by modification time descending (most recent first)
    scanned_files = sorted(scanned_files, key=lambda x: x["mtime"], reverse=True)
    return scanned_files[:15] # Limit to top 15 most recent files

def inspect_file(file_info):
    path = file_info["path"]
    ext = os.path.splitext(path)[1].lower()
    
    sheets = []
    headers = []
    
    try:
        if ext == ".csv":
            # Just read the first row to get headers fast
            df = pd.read_csv(path, nrows=0)
            headers = [str(c).strip() for c in df.columns]
            sheets = ["Default"]
        else:
            # Excel files: get sheet names first (extremely fast)
            xl = pd.ExcelFile(path)
            sheets = xl.sheet_names
            
            # Read first row of first sheet to get headers fast
            # Try to read standard header or look in first 3 rows
            df = pd.read_excel(path, sheet_name=sheets[0], nrows=2)
            headers = [str(c).strip() for c in df.columns]
            # If headers look like index numbers, check if row 1 has text
            if len(df) > 0 and all(str(c).isdigit() or "Unnamed" in str(c) for c in df.columns):
                headers = [str(c).strip() for c in df.iloc[0].values]
    except Exception as e:
        log(f"Error reading headers for {path}: {e}")
        return None
        
    return {
        "sheets": sheets,
        "headers": headers
    }

def detect_skills(file_info, inspection):
    if not inspection:
        return []
        
    sheets = [s.strip().upper() for s in inspection["sheets"]]
    headers = [h.strip().upper() for h in inspection["headers"]]
    name = file_info["name"].upper()
    
    candidates = []
    
    # 1. PWP Performance Analysis
    # Signature: SiteCodeName, SalesmanName, DocumentDate, PWP Receipt Count
    pwp_cols = {"SITECODENAME", "SALESMANNAME", "DOCUMENTDATE", "PWP RECEIPT COUNT"}
    if pwp_cols.issubset(set(headers)) or "PWP" in name:
        candidates.append({
            "skill": "pwp_analysis",
            "name": "PWP Performance Analysis",
            "confidence": "High" if pwp_cols.issubset(set(headers)) else "Medium",
            "reason": "Found PWP-specific transaction columns."
        })
        
    # 2. Match Local Supplier (Sabah Local Sourcing)
    # Signature: Tab named "POISON TO ORDER LOCALLY "
    supplier_sheets = {"POISON TO ORDER LOCALLY", "POISON TO ORDER LOCALLY "}
    if any(s in sheets for s in supplier_sheets) or "SABAH LOCAL" in name:
        candidates.append({
            "skill": "match_local_supplier",
            "name": "Match Local Supplier (Local Sourcing)",
            "confidence": "High" if any(s in sheets for s in supplier_sheets) else "Medium",
            "reason": "Found sheet tab targeting Sabah Local POISON ordering."
        })
        
    # 3. Non-Returnable Clearance
    # Signature: Headers containing 'EXPIRY', 'QTY' or 'QUANTITY', and 'ARTICLE'
    has_expiry = any("EXPIRY" in h or "EXPIRED" in h or "EXP" in h for h in headers)
    has_qty = any("QTY" in h or "QUANTITY" in h for h in headers)
    has_art = any("ARTICLE" in h or "ART" in h or "ITEM" in h for h in headers)
    if (has_expiry and has_qty and has_art) or "CLEARANCE" in name:
        candidates.append({
            "skill": "non_returnable_clearance",
            "name": "Non Returnable Clearance",
            "confidence": "High" if (has_expiry and has_qty and has_art) else "Medium",
            "reason": "Detected expiry dates, article numbers, and stock quantities."
        })
        
    # 4. Excel Pareto Mapping (Pareto Sales metrics)
    # Signature: Columns like 'CombinedPareto', 'Sales Qty', 'Sales Amt', 'SiteCode'
    pareto_cols = {"SALES QTY (PAST 3 MONTHS)", "SALES AMT (PAST 3 MONTHS)", "COMBINEDPARETO"}
    if any(c in headers for c in pareto_cols) or "PARETO" in name:
        # Avoid conflict with Reorder if it has SHD headers
        if "DAILY DEMAND" not in headers:
            candidates.append({
                "skill": "excel_pareto_mapping",
                "name": "Excel Pareto Mapping",
                "confidence": "High" if any(c in headers for c in pareto_cols) else "Medium",
                "reason": "Contains historical sales quantities and Pareto class ratings."
            })

    # 5. Master SHD File signatures
    # Used for: Reorder Calculation, Stock Rotation, and targets for Pareto Mapping / Clearance.
    shd_signature_cols = {"SOH", "STORE", "ARTICLECODE"}
    if shd_signature_cols.issubset(set(headers)) or "SHD" in name:
        # Standard SHD file
        candidates.append({
            "skill": "excel_reorder",
            "name": "Excel Reorder Calculation (Replenishment)",
            "confidence": "High" if "DAY 1 TO 30" in headers else "Medium",
            "reason": "Master Stock on Hand (SHD) file detected. Perfect for replenishment planning."
        })
        candidates.append({
            "skill": "excel_rotation",
            "name": "Excel Stock Rotation (Inter-store Transfers)",
            "confidence": "High" if "RP TYPE" in headers else "Medium",
            "reason": "Master Stock on Hand (SHD) file detected. Perfect for store rotation."
        })
        candidates.append({
            "skill": "check_article",
            "name": "Check Article (SOH Recall Report)",
            "confidence": "Medium",
            "reason": "Inventory file detected. Suitable for article stock checks/mass recalls."
        })

    return candidates

def main():
    log("Scanning directory and Downloads folder...")
    files = scan_files()
    log(f"Found {len(files)} recent files. Inspecting signatures...")
    
    results = []
    for f in files:
        inspection = inspect_file(f)
        if inspection:
            candidates = detect_skills(f, inspection)
            results.append({
                "file": f,
                "sheets": inspection["sheets"],
                "headers": inspection["headers"][:12], # Limit header output in JSON
                "matches": candidates
            })
        else:
            results.append({
                "file": f,
                "sheets": [],
                "headers": [],
                "matches": []
            })
            
    # Output clean JSON to stdout for agent parsing
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
