"""
Name Cierra Britt
Date: 10/06/2025

This is for EPA Daily & Hourly PM2.5, PM10. NO2 Data: https://aqs.epa.gov/aqsweb/airdata/download_files.html#AQI

This  script reshapes cleaned air-quality data (from PM₂.₅, PM₁₀, and NO₂ CSVs) into a wide, comparison-friendly format where each pollutant occupies its own column (e.g., Pollutant A (NO₂), Pollutant B (PM₂.₅), Pollutant C (PM₁₀)).
It groups the data by location and date—using coordinates, site number, or region fields—and outputs either a single wide CSV or an Excel workbook with one sheet per location (similar to your “Philadelphia” and “Iowa” tabs).

Key Features
    - Pivot by pollutant: Converts “Pollutant Name” rows into side-by-side columns for easy comparison.
    - Automatic grouping: Groups by State, County, City, Site Num, Latitude, Longitude, and Date.
    - Value selection: Lets you choose which numeric metric (e.g., Arithmetic Mean or 1st Max Value) becomes the pollutant value.
    - Flexible column labels: Option to label columns as
        - Pollutant A (NO₂), Pollutant B (PM₂.₅) …, or
        - use the pollutant names directly (NO₂, PM₂.₅, PM₁₀).
    - Output options:
        - Export a single combined CSV file, or
        - Export an Excel workbook with one sheet per location.
    - User-friendly interface: Uses simple GUI dialogs to select input/output files, column names, and export options—no command-line input required.
        Example Output
        Date    Pollutant A (NO₂)   Pollutant B (PM₂.₅) Pollutant C (PM₁₀)  State   City    Latitude    Longitude
        2025-01-10  15.2    9.81    23.4    Maryland    Baltimore   39.290  −76.610

        MUST HAVE PANDAS AND OPENPYXL INSTALLED
        pip install openpyxl
        pip install pandas
"""
# Standard library for path building and filename manipulation
import os
# Pandas for data loading, cleaning, reshaping, and export
import pandas as pd  
# Tkinter GUI prompts
from tkinter import Tk, filedialog, simpledialog, messagebox

#------------- Initial Setup ---------------
# Helper to prompt the user to select an input CSV
def pick_file():
    # Hide the root Tk window (we only want dialogs)
    Tk().withdraw()
    # Open file picker and return the chosen path
    return filedialog.askopenfilename(
        title="Select cleaned/combined CSV",  # Dialog title
        filetypes=[("CSV files","*.csv")]  # Only show CSVs
    )

# Helper to prompt the user to select an output directory
def pick_folder():
    # Hide the root Tk window
    Tk().withdraw()
    # Return folder path
    return filedialog.askdirectory(title="Select output folder")

# Return the first existing column name from a list
def coalesce(df, candidates):
    # Iterate candidate column names
    for c in candidates:
        # If candidate exists in DataFrame
        if c in df.columns:
            return c
    # returns none if nothing matched
    return None

# Normalize column to python dates
def ensure_date(df, date_col):
    # Parse to datetime, coerce bad rows, then take date
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.date
    # Return mutated DataFrame for chaining
    return df

# Ask for a string input limited to allowed choices
def ask_choice(title, prompt, choices):
    # Get input string
    s = simpledialog.askstring(title, f"{prompt}\n\nOptions: {', '.join(choices)}")
    # If user cancelled or blank
    if not s:
        # Indicate no valid choice
        return None
    # Normalize whitespace and case
    s = s.strip().lower()
    # Check against allowed options (case-insensitive)
    if s in [c.lower() for c in choices]:
        # Return normalized selection
        return s
    # Else invalid choice
    return None

# Make a value safe to use as an Excel sheet name
def safe_sheet_name(s: str) -> str:
    # Fallback for empty/none values
    if not s:
        # Default sheet name
        return "Sheet1"
    # Ensure string
    s = (str(s)
         .replace("/", "-").replace(":", "-").replace("\\", "-")  # Replace forbidden characters
         .replace("*","-").replace("?","-").replace("[","(").replace("]",")"))  # More replacements
    return s[:31] if len(s) > 31 else s  # Excel sheet name length limit = 31

# --------------- filtering ----------------
# Mapping of logical filter types to likely column name variants
FILTER_KEYS = {
    "state":       ["State Name", "State"],
    "city":        ["City Name", "City"],
    "county":      ["County Name", "County"],
    "site":        ["Site Num", "Site Number"],
    "cbsa":        ["CBSA Name", "CBSA", "CBSA Name (2018)", "CBSA Code", "CBSA_Code"],
    "coordinates": ["Latitude", "Site Latitude", "Lat", "Longitude", "Site Longitude", "Lon", "Long"],
}

# Optionally subset the data before formatting
def filter_df(df: pd.DataFrame) -> pd.DataFrame:
    # Optional filter by state/city/county/site/CBSA/coordinates before formatting
    # Ask user whether to filter
    if not messagebox.askyesno("Filter (Optional)", "Filter by state, city, county, site, CBSA, or coordinates?"):
        # If no, return original
        return df
    
    # Which filter kind?
    ftype = ask_choice("Filter Type", "Enter a filter type", ["state","city","county","site","cbsa","coordinates"])
    # If invalid or cancelled
    if not ftype:
        messagebox.showwarning("Filter", "Invalid or empty filter type. Skipping filter.")
        # Return unfiltered data
        return df
    
    # Special flow for coordinate matching
    if ftype == "coordinates":
        # Find latitude column (first of the three candidates)
        lat_col = coalesce(df, FILTER_KEYS["coordinates"][:3])
        # Find longitude column (first of the three candidates)
        lon_col = coalesce(df, FILTER_KEYS["coordinates"][3:])
        # If either missing
        if not lat_col or not lon_col:
            # Shows error
            messagebox.showerror("Filter", "Latitude/Longitude columns not found.")
            # Returns unfiltered
            return df
        # Ask for target lat/lon text
        kw = simpledialog.askstring("Coordinates", "Enter lat, lon (e.g., 39.290, -76.610):")
        try:
            # Split on comma and trim
            lat_str, lon_str = [x.strip() for x in kw.split(",")]
            # Convert to floats
            lat, lon = float(lat_str), float(lon_str)
        # Any parsing error
        except Exception:
            # Shows error
            messagebox.showerror("Filter", "Invalid coordinates format.")
            # Returns unfiltered
            return df
        # Match by rounded lat/lon (3 dp)
        return df[(df[lat_col].round(3) == round(lat,3)) & (df[lon_col].round(3) == round(lon,3))]

    # Candidate column names for chosen filter type
    cols = FILTER_KEYS[ftype]
    # Pick the first one that exists
    col = coalesce(df, cols)
    # If none found
    if not col:
        # Shows error
        messagebox.showerror("Filter", f"Column for '{ftype}' not found in data.")
        # Returns original
        return df
    # Ask for a substring to search
    kw = simpledialog.askstring("Keyword", f"Enter {ftype} text to match (contains):")
    # If blank
    if not kw:
        # Returns original
        return df
    # Case-insensitive contains() filter
    return df[df[col].astype(str).str.contains(kw, case=False, na=False)]

# --------------- grouping / pivot ----------------
# Same idea as FILTER_KEYS, but used when choosing grouping fields
GROUP_MAP = {
    "state":  ["State Name", "State"],
    "city":   ["City Name", "City"],
    "county": ["County Name", "County"],
    "site":   ["Site Num", "Site Number"],
    "cbsa":   ["CBSA Name", "CBSA", "CBSA Name (2018)", "CBSA Code"],
    "coordinates": ["Latitude", "Site Latitude", "Lat", "Longitude", "Site Longitude", "Lon", "Long"],
}

# Ask user how to group; detect date/value columns; return setup
def choose_grouping(df: pd.DataFrame):
    """
    Prompt ask how to group sheets/rows: state, city, county, site, cbsa, coordinates, or custom.
    Returns updated df, detected date column, value column, and list of group columns.
    """
    # detect date & value columns
    # Try common date column names
    date_col = coalesce(df, ["Date","Date Local","Date Observed","Date GMT"])
    # If none auto-detected
    if not date_col:
        # Ask user
        date_col = simpledialog.askstring("Date Column", "Enter date column (e.g., Date or Date Local)")
        if not date_col or date_col not in df.columns:
            # Stop with a clear error
            raise ValueError("Date column not found.")
    # Normalize date column to pure dates
    df = ensure_date(df, date_col)

    # Prefer Arithmetic Mean by default
    val_col = "Arithmetic Mean" if "Arithmetic Mean" in df.columns else None
    # If not present, ask the user what numeric column to use
    if not val_col:
        val_col = simpledialog.askstring("Value Column", "Enter numeric column to pivot (e.g., Arithmetic Mean, 1st Max Value)")
        if not val_col or val_col not in df.columns:
            # Stop if missing
            raise ValueError("Value column not found.")

    # grouping choice
    choice = ask_choice(
        "Grouping",
        "Group data by which location field?",
        ["state","city","county","site","cbsa","coordinates","custom"]  # Allowed grouping modes
    )
    # If user cancelled/invalid
    if not choice:
        raise ValueError("Invalid grouping choice.")  # Stop early
    # Will hold the actual column name(s) used for grouping
    group_cols = []
    # Simple single-column groupings
    if choice in ("state","city","county","site","cbsa"):
        # Pick the first matching column for that logical field
        col = coalesce(df, GROUP_MAP[choice])
        # If not found
        if not col:
            raise ValueError(f"Could not find a column for {choice} in the data.")
        # Use that column
        group_cols = [col]
    # Group by lat/lon pair
    elif choice == "coordinates":
        lat_col = coalesce(df, GROUP_MAP["coordinates"][:3])  # Locate latitude
        lon_col = coalesce(df, GROUP_MAP["coordinates"][3:])  # Locate longitude
        if not lat_col or not lon_col:  # Validate
            raise ValueError("Latitude/Longitude columns not found for coordinates grouping.")
        # Use both
        group_cols = [lat_col, lon_col]
    # User enters arbitrary grouping columns
    elif choice == "custom":
        # Get list text
        cols = simpledialog.askstring("Custom Grouping", "Enter column names to group by, comma-separated:")
        if not cols:
            raise ValueError("No custom columns provided.")
        # Split and trim
        parts = [c.strip() for c in cols.split(",") if c.strip()]
        # Validate all exist
        missing = [c for c in parts if c not in df.columns]
        # If any missing
        if missing:
            # Stop with helpful message
            raise ValueError(f"These columns were not found: {missing}")
        # Use provided list
        group_cols = parts
    # Hand back configuration
    return df, date_col, val_col, group_cols

# ---------- Helper ----------
# Candidate column names for long-format output core fields
LONG_BASE_CANDIDATES = {
    "sample_id": ["Sample ID", "SampleID", "Sample_Id"],
    "pollutant_name": ["Pollutant Name", "Pollutant"],
    "sample_duration": ["Sample Duration", "Sample_Duration", "Duration"],
    "date": ["Date", "Date Local", "Date Observed", "Date GMT"],
    "value": ["Arithmetic Mean", "Arithmetic mean", "1st Max Value"]
}
# Return first column name from list that exists in df
def pick_first(df, names):
    # Iterate candidate names
    for n in names:
        # If present
        if n in df.columns:
            return n
    # None if none present
    return None

# Build a DataFrame
def make_long_df(df, date_col, value_col, group_cols):
    # copy to avoid modifying original
    # Work on a copy to keep caller's df unchanged
    df = df.copy()

    # Normalize date -> date
    # Standardize to a single 'Date' column
    df["Date"] = pd.to_datetime(df[date_col], errors="coerce").dt.date

    # locate base columns
    # Detect sample-id column if present
    sid_col = pick_first(df, LONG_BASE_CANDIDATES["sample_id"])
    # Detect pollutant column
    pol_col = pick_first(df, LONG_BASE_CANDIDATES["pollutant_name"])
    # Detect sample-duration column
    dur_col = pick_first(df, LONG_BASE_CANDIDATES["sample_duration"])

    # ensure numeric and rounding
    # Convert value col to numeric and round
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce").round(3)

    # Build ordered list
    # Initialize column order
    ordered = []
    # Include Sample ID if available
    if sid_col: ordered.append(sid_col)
    # Include Pollutant Name if available
    if pol_col: ordered.append(pol_col)
    # Include Sample Duration if available
    if dur_col: ordered.append(dur_col)
    # Always include Date and the chosen numeric value
    ordered += ["Date", value_col]

    # Include chosen grouping/location cols (avoid duplicates)
    # For each grouping field
    for c in group_cols:
        # Avoid duplicates and ensure exists
        if c not in ordered and c in df.columns:
            # Add to output order
            ordered.append(c)

    # keep only existing columns
    ordered = [c for c in ordered if c in df.columns]

    # final selection (Date header already set to 'Date')
    long_df = df[ordered]  # Subset DataFrame to desired columns/order
    return long_df  # Return the long-format table

# ---------- WIDE label helper ----------
# Build display labels for pollutant columns
def label_style_map(pollutants, use_abc=True):
    abc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # Letters for Pollutant A/B/C labeling
    out = {}  # Mapping original_name -> label
    for i, p in enumerate(sorted(pollutants)):  # Sort pollutants for consistent order and enumerate
        out[p] = (f"Pollutant {abc[i]} ({p})" if use_abc else p)  # Either "Pollutant A (NO2)" or "NO2"
    return out  # Return rename map

# ----------------- main -----------------
def main():  # Entry point for interactive workflow
    messagebox.showinfo("Wide/Long by Location", "Select cleaned/combined pollutant CSV (must contain 'Pollutant Name').")  # Intro notice
    in_file = pick_file()  # Ask user for input CSV path
    if not in_file:  # If nothing selected
        messagebox.showwarning("No file", "No input selected.")  # Warn and exit
        return  # Stop

    try:
        df = pd.read_csv(in_file, low_memory=False)  # Read CSV into DataFrame (disable low_memory to avoid mixed dtypes)
    except Exception as e:  # Catch read errors
        messagebox.showerror("Read error", f"Could not read file:\n{e}")  # Show error details
        return  # Stop

    if "Pollutant Name" not in df.columns:  # Validate required field produced by upstream cleaner
        messagebox.showerror("Missing", "Input must include 'Pollutant Name' (from your cleaner).")  # Show guidance
        return  # Stop

    # optional pre-filter
    df = filter_df(df)  # Let user subset by location if desired

    # choose grouping + detect date/value columns
    try:
        df, date_col, val_col, group_cols = choose_grouping(df)  # Configure grouping and key columns
    except Exception as e:  # Any setup error
        messagebox.showerror("Setup error", str(e))  # Show message to user
        return  # Stop

    # export style
    style = simpledialog.askstring(
        "Export Style",
        "Type 'LONG' for Sample ID, Pollutant Name, Sample Duration, Date, Value, Location(s)\n"
        "or 'WIDE' for pollutants as columns:"  # Explain the two output shapes
    )
    style = (style or "LONG").strip().upper()  # Default to LONG if blank; normalize case/whitespace

    out_dir = pick_folder()  # Ask for output directory
    if not out_dir:  # If user cancelled
        messagebox.showwarning("No folder", "No output folder selected.")  # Warn
        return  # Stop

    base = os.path.splitext(os.path.basename(in_file))[0]  # Base name (without extension) for output filenames

    if style == "WIDE":  # Wide/pivoted output branch
        # build wide pivot
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce").round(3)  # Ensure numeric metric and round
        index_cols = group_cols + [date_col]  # Index of pivot: chosen grouping columns + date
        wide = df.pivot_table(index=index_cols, columns="Pollutant Name", values=val_col, aggfunc="mean").reset_index()  # Pivot to wide

        label_pref = simpledialog.askstring(
            "Column Labels", "Type 'ABC' for Pollutant A/B/C (NO2) or 'NAME' for NO2/PM2.5/PM10:"  # Ask naming style
        )
        use_abc = (label_pref or "").strip().upper() != "NAME"  # Default to ABC unless explicitly "NAME"
        pol_cols = [c for c in wide.columns if c not in index_cols]  # Identify pollutant columns created by pivot
        rename_map = label_style_map(pol_cols, use_abc=use_abc)  # Build rename mapping
        wide = wide.rename(columns=rename_map)  # Apply friendly column names

        # put Date + pollutants first
        pol_named = [rename_map[p] for p in pol_cols]  # List of renamed pollutant columns in consistent order
        front = ["Date"] + pol_named if date_col == "Date" else [date_col] + pol_named  # Desired front column order
        remaining = [c for c in wide.columns if c not in front]  # Everything else (grouping fields)
        ordered_cols = [c for c in front if c in wide.columns] + remaining  # Merge order while guarding existence
        wide = wide[ordered_cols]  # Reorder columns in final table

        mode = simpledialog.askstring("Export", "Type 'CSV' for one CSV or 'XLSX' for Excel with one sheet per group:")  # Ask file type
        mode = (mode or "CSV").strip().upper()  # Default to CSV if blank

        if mode == "XLSX":  # Excel multi-sheet export
            try:
                import openpyxl  # noqa: F401  # Ensure engine is installed
            except Exception:  # If not installed
                messagebox.showwarning("Dependency", "Install openpyxl: pip install openpyxl")  # Tell user how to fix
                return  # Stop
            out_path = os.path.join(out_dir, f"{base}_wide_by_{'_'.join([c.replace(' ','_') for c in group_cols])}.xlsx")  # Build path
            with pd.ExcelWriter(out_path, engine="openpyxl") as writer:  # Create Excel writer context
                if group_cols:  # If grouping present, split into sheets by group
                    for keys, sub in wide.groupby(group_cols):  # Iterate group combinations
                        keys = keys if isinstance(keys, tuple) else (keys,)  # Normalize keys to tuple
                        sheet = "-".join([str(k) for k in keys if pd.notna(k)])  # Join keys for sheet name
                        sheet = safe_sheet_name(sheet or "Sheet1")  # Sanitize sheet name
                        sub.to_excel(writer, sheet_name=sheet, index=False)  # Write each group to its own sheet
                else:  # No grouping → single sheet
                    wide.to_excel(writer, sheet_name="All", index=False)  # Write entire table
            messagebox.showinfo("Done", f"Saved Excel workbook:\n{out_path}")  # Notify success
        else:  # CSV export path
            out_path = os.path.join(out_dir, f"{base}_wide_by_{'_'.join([c.replace(' ','_') for c in group_cols])}.csv")  # Build CSV path
            wide.to_csv(out_path, index=False)  # Write CSV
            messagebox.showinfo("Done", f"Saved CSV:\n{out_path}")  # Notify success

    else:  # LONG style branch (default)
        # LONG style
        long_df = make_long_df(df, date_col=date_col, value_col=val_col, group_cols=group_cols)  # Build long-format table

        mode = simpledialog.askstring("Export", "Type 'CSV' for one CSV or 'XLSX' for Excel with one sheet per group:")  # Ask output format
        mode = (mode or "XLSX").strip().upper()  # Default to XLSX for long

        if mode == "XLSX":  # Excel export
            try:
                import openpyxl  # noqa: F401  # Ensure Excel writer engine exists
            except Exception:  # If not installed
                messagebox.showwarning("Dependency", "Install openpyxl: pip install openpyxl")  # Instruct user
                return  # Stop
            out_path = os.path.join(out_dir, f"{base}_long_by_{'_'.join([c.replace(' ','_') for c in group_cols])}.xlsx")  # Build path
            with pd.ExcelWriter(out_path, engine="openpyxl") as writer:  # Create workbook
                if group_cols:  # If grouping is set, make one sheet per group
                    for keys, sub in long_df.groupby(group_cols):  # Iterate groups
                        keys = keys if isinstance(keys, tuple) else (keys,)  # Normalize key tuple
                        sheet = "-".join([str(k) for k in keys if pd.notna(k)])  # Combine keys for sheet name
                        sheet = safe_sheet_name(sheet or "Sheet1")  # Sanitize sheet name
                        sub.to_excel(writer, sheet_name=sheet, index=False)  # Write group to sheet
                else:  # No grouping → one sheet
                    long_df.to_excel(writer, sheet_name="All", index=False)  # Write entire table
            messagebox.showinfo("Done", f"Saved Excel workbook:\n{out_path}")  # Notify success
        else:  # CSV export
            out_path = os.path.join(out_dir, f"{base}_long_by_{'_'.join([c.replace(' ','_') for c in group_cols])}.csv")  # Build filename
            long_df.to_csv(out_path, index=False)  # Write CSV file
            messagebox.showinfo("Done", f"Saved CSV:\n{out_path}")  # Notify success


if __name__ == "__main__":  # Standard Python entry-point check
    main()  # Run the interactive workflow when executed as a script