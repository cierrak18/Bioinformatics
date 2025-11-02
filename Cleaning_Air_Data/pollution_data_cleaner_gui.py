# Name Cierra Britt
# Date: 10/06/2025
# Sources: https://github.com/robertjdellinger/querying-epa-data, https://github.com/USEPA/pyaqsapi
# This is for EPA Daily & Hourly PM2.5, PM10, NO2 Data: https://aqs.epa.gov/aqsweb/airdata/download_files.html#AQI
#
# Notes about datasets (row counts/sizes as of 2025-07-31):
#   PM2.5: daily_SPEC_2025.zip — 1,780,031 Rows — 14,119 KB
#   PM10 : daily_PM10SPEC_2025.zip — 77,035 Rows — 1,005 KB
#   NO2  : daily_42602_2025.zip — 47,646 Rows — 716 KB
#
# Summary: Pollution Data Cleaner (GUI Version)
# - Python GUI tool to clean/merge/filter air quality datasets (PM2.5, PM10, NO2).
# - Guides user through prompts to choose files, frequency (daily/hourly), combining, pollutant, and filters.
# - Cleans: drops low-information columns, adds Pollutant Name and Sample ID, rounds key numeric columns.
# - Filters: by state/city/county/site/coordinates/CBSA.
# - Exports cleaned CSVs named like: daily_PM25_cleaned.csv, hourly_NO2_cleaned.csv.

import pandas as pd  # Data processing, IO, and dataframe operations
import os            # File path manipulation and basename/dirname utilities
from tkinter import Tk, filedialog, simpledialog, messagebox  # GUI dialogs for file picks and prompts
import sys           # For exiting the script early on user cancellations

# ---------- CONFIG ------------
# Columns to remove as low-information or redundant for analysis/merging
DROP_COLS = [
    'Pollutant Standard', 'Date Last Change', 'Event Type',
    'AQI', 'CBSA', 'Datum'
]
# Mapping of filter keywords to column names expected in input data
FILTER_MAP = {
    'state': 'State Name',
    'city': 'City Name',
    'county': 'County Name',
    'site': 'Site Num',
    'coordinates': ['Latitude', 'Longitude'],
    'cbsa': 'CBSA Name'
}
# For Sample ID prefixes
POLLUTANT_PREFIX = {'PM2.5': 'PM25', 'PM10': 'PM10', 'NO2': 'NO2', 'Unknown': 'UNKNOWN'}

# --------------- FILE DIALOGS ------------------
# Prompt the user to select one or more CSV files
def select_files():
    # Hide the root Tkinter window; show only dialogs
    Tk().withdraw()
    # Open multi-select file dialog
    files = filedialog.askopenfilenames(
        title="Select daily or hourly CSV file(s)", # Dialog title
        filetypes=[("CSV files", "*.csv")] # Restrict to CSV files
    )
    # Convert tuple to list for easier handling
    return list(files)

# Prompt the user to select an output folder
def choose_output_directory():
    # Hide root window
    Tk().withdraw()
    # Return selected directory path
    return filedialog.askdirectory(title="Select output folder")

# ------------ POLLUTANT FROM FILENAME (no regex) ----------------
# Heuristic to infer pollutant type from filename
def pollutant_from_filename(path: str) -> str:
    # Get lowercase filename without directories
    name = os.path.basename(path).lower()
    # Look for PM2.5 patterns
    if "pm2.5" in name or "pm25" in name or "pm2_5" in name:
        return "PM2.5"
    # Look for PM10 pattern
    if "pm10"  in name:
        return "PM10"
    # Look for NO2 pattern
    if "no2"   in name:
        return "NO2"
    return "Unknown"  # Fall back when no hint is found

def ask_pollutant_for_file(path: str) -> str:  # Ask user to specify pollutant when filename is unclear
    # Fallback prompt if filename doesn’t indicate pollutant
    msg = f"Could not detect pollutant from file name:\n\n{os.path.basename(path)}\n\nEnter one of: PM2.5, PM10, NO2"  # Instruction text
    p = simpledialog.askstring("Pollutant?", msg)  # Ask for a free-text pollutant input
    if not p: 
        return "Unknown"  # If user cancels/empties, return Unknown
    p = p.strip().upper().replace(" ", "")  # Normalize spacing/case
    if p in ("PM2.5","PM25","PM2_5"):
        return "PM2.5"
    if p == "PM10":
        return "PM10"
    if p == "NO2":
        return "NO2"
    # Anything else becomes Unknown
    return "Unknown"

# ------------- CLEAN + LABEL (per file) ----------------
# Clean a single file and add labels
def clean_and_label_dataframe(df: pd.DataFrame, pollutant: str) -> pd.DataFrame:
    # remove low-value cols
    # Drop known low-value columns if present
    df = df.drop(columns=[c for c in DROP_COLS if c in df.columns], errors='ignore')

    # Sample ID + Pollutant Name first
    # Determine prefix for Sample ID (e.g., PM25)
    prefix = POLLUTANT_PREFIX.get(pollutant, "UNKNOWN")
    # Insert sequential Sample IDs as first column
    df.insert(0, "Sample ID", [f"{prefix}-{i:04d}" for i in range(1, len(df)+1)])
    # Insert pollutant label as second column
    df.insert(1, "Pollutant Name", pollutant)

    # Round key numeric columns if present
    # Target metrics to standardize
    for col in ['Arithmetic Mean', '1st Max Value', '1st Max Daily Value']:
        # Only if column exists in this file
        if col in df.columns:
            # Force numeric and round to 3 decimals
            df[col] = pd.to_numeric(df[col], errors='coerce').round(3)

    # Ensure column order: Sample ID, Pollutant Name, then rest
    # Build desired column order
    cols = ["Sample ID", "Pollutant Name"] + [c for c in df.columns if c not in ("Sample ID","Pollutant Name")]
    # Reorder and return cleaned dataframe
    return df[cols]

# ----------- FILTERING -----------
# Apply a filter on the dataframe based on type and keyword
def filter_data(df, keyword_type, keyword):
    # Normalize filter type to lowercase
    kt = (keyword_type or "").strip().lower()
    # Coordinate-based filter expects "lat, lon"
    if kt == "coordinates":
        try:
            # Split input into lat/lon strings
            lat_str, lon_str = [x.strip() for x in keyword.split(",")]
            # Convert to floats
            lat, lon = float(lat_str), float(lon_str)
            # Match latitude to 3 decimal places
            # Match longitude to 3 decimal places
            return df[(df["Latitude"].round(3) == round(lat, 3)) &
                      (df["Longitude"].round(3) == round(lon, 3))]
        # Handle parsing/format errors
        except Exception:
            messagebox.showerror("Error", "Invalid coordinate format. Use: 39.290, -76.610")
            # Return unfiltered on error
            return df
    else:
        # Map the keyword type to a column name
        col = FILTER_MAP.get(kt)
        # Ensure we have a valid column
        if isinstance(col, str) and col in df.columns:
            # Case-insensitive substring match
            return df[df[col].astype(str).str.contains(keyword, case=False, na=False)]
        # If no valid column, return original dataframe unchanged
        return df

# ------------- EXPORT ---------------
# Export combined dataframe with generic name by pollutants present
def export_cleaned(df, frequency, out_dir):
    # Collect unique pollutant labels
    pollutants = df["Pollutant Name"].dropna().unique().tolist()
    # Compact label string
    pollutants_str = "_".join([p.replace(".", "").replace(" ", "") for p in pollutants]) if pollutants else "Unknown"
    # Build filename like "daily_PM25_PM10_cleaned.csv"
    filename = f"{frequency.lower()}_{pollutants_str}_cleaned.csv"
    # Full output path
    out_path = os.path.join(out_dir, filename)
    # Write CSV without index
    df.to_csv(out_path, index=False)
    # Notify user of success
    messagebox.showinfo("Success", f"✅ Exported file:\n{out_path}")

# Export per-file with more specific name
def export_cleaned_single(df, frequency, out_dir, pollutant, source_filename):
    # Local import (already imported at top; harmless but keeps function self-contained)
    import os
    # Sanitize pollutant for filename
    safe_pollutant = pollutant.replace('.', '').replace(' ', '')
    # Get source file base name
    base = os.path.splitext(os.path.basename(source_filename))[0]
    # e.g., "daily_PM25_daily_SPEC_2025_cleaned.csv"
    filename = f"{frequency.lower()}_{safe_pollutant}_{base}_cleaned.csv"
    # Full output path
    out_path = os.path.join(out_dir, filename)
    # Write CSV
    df.to_csv(out_path, index=False)
    # Print to console for debugging/logging
    print(f"✅ Exported: {out_path}")

# ------------- MAIN ---------------
# Orchestrates user interaction: select files, clean, filter, and export
def main():
    # Intro message
    messagebox.showinfo("Pollution Data Cleaner", "Welcome! Select your pollutant data CSV file(s).")
    # Let user choose one or more CSV files
    files = select_files()
    # If user cancelled or selected none
    if not files:
        # Warn user
        messagebox.showwarning("No Files", "No files selected. Exiting.")
        # Exit script early
        sys.exit()

    # Ask dataset frequency
    frequency = simpledialog.askstring("Data Frequency", "Is your data DAILY or HOURLY?")
    # If user cancelled
    if not frequency:
        # Warn and exit
        messagebox.showwarning("Missing Input", "No frequency entered. Exiting.")
        # Exit script
        sys.exit()
    # Normalize frequency to lowercase
    frequency = frequency.strip().lower()
    # Ask about combining files
    combine = messagebox.askyesno("Combine Files", f"You selected {len(files)} file(s). Combine them into one?")
    # list of (df, pollutant, filename) tuples to collect cleaned outputs
    frames = []
    # Process each selected file
    for f in files:
        try:
            # Read CSV; low_memory=False reduces dtype guessing warnings
            df = pd.read_csv(f, low_memory=False)
            # Infer pollutant from filename
            pollutant = pollutant_from_filename(f)
            # If inference fails
            if pollutant == "Unknown":
                # Ask user to specify pollutant
                pollutant = ask_pollutant_for_file(f)
            # Clean and label the dataframe
            cleaned = clean_and_label_dataframe(df, pollutant)

            # DEBUG: show what we loaded
            # Print status for each file
            print(f"Loaded {len(cleaned):,} rows from {os.path.basename(f)} as {pollutant}")
            # Save tuple for later combining/exporting
            frames.append((cleaned, pollutant, f))
        # Catch read/clean errors per file 
        except Exception as e:
            # Show error message
            messagebox.showerror("Error Reading File", f"Failed to read {f}.\nError: {e}")
            # continue to next file instead of exiting; you want the others
            # Skip to next file
            continue
    # If all files failed
    if not frames:
        # Warn user
        messagebox.showwarning("Nothing to export", "No files were successfully cleaned.")
        # Stop main()
        return

    # ----------- Option branching -------------
    
    # A) Single file selected (always export just that file, with optional filter)
    # Exactly one file processed successfully
    if len(frames) == 1:
        # Unpack the only frame
        df, pollutant, fname = frames[0]

        # Ask whether to filter this single file
        # Offer filter step
        if messagebox.askyesno("Filter", "Filter by state, city, county, site, coordinates, or cbsa?"):
            # Which filter type?
            kt = simpledialog.askstring("Filter Type", "Enter: state, city, county, site, coordinates, or cbsa")
            # Filter term (or coordinates)
            kw = simpledialog.askstring("Keyword", "e.g., Maryland, Baltimore, 39.290, -76.610")
            # If both provided
            if kt and kw:
                # Apply filter to the single dataframe
                df = filter_data(df, kt, kw)
        # Ask where to save
        out_dir = choose_output_directory()
        # If user cancels folder selection
        if not out_dir:
            # Warn user
            messagebox.showwarning("No Output Folder", "No output folder selected. Exiting.")
            # Stop
            return
        # Export single cleaned file
        export_cleaned_single(df, frequency, out_dir, pollutant, fname)
        # Success message
        messagebox.showinfo("Done", "✅ Cleaned and exported 1 file.")
        # Stop main()
        return

    # B) Multiple files, and user chose to combine
    if combine and len(frames) > 1:  # If combining multiple cleaned dataframes
        # Combine **only the DataFrames** from the tuples
        combined = pd.concat([df for (df, _poll, _f) in frames], ignore_index=True)  # Concatenate all cleaned frames

        # DEBUG: sanity check counts by pollutant
        try:
            print("Counts by pollutant in combined:")  # Log header
            print(combined['Pollutant Name'].value_counts(dropna=False))  # Show distribution by pollutant
        except Exception:
            pass  # If column missing/unexpected, skip debug

        # Optional combined filter
        # Offer filtering combined data
        if messagebox.askyesno("Filter", "Filter by state, city, county, site, coordinates, or cbsa?"):
            kt = simpledialog.askstring("Filter Type", "Enter: state, city, county, site, coordinates, or cbsa")  # Filter type
            kw = simpledialog.askstring("Keyword", "e.g., Maryland, Baltimore, 39.290, -76.610")  # Filter keyword/coords
            if kt and kw:  # If provided
                combined = filter_data(combined, kt, kw)  # Apply filter to combined dataframe

        out_dir = choose_output_directory()  # Ask for output folder
        if not out_dir:  # If user cancels
            messagebox.showwarning("No Output Folder", "No output folder selected. Exiting.")  # Warn
            return  # Stop
        # Export a single combined CSV
        export_cleaned(combined, frequency, out_dir)
        messagebox.showinfo("Done", "✅ Cleaning and combining completed successfully!")  # Success message
        return  # Stop main()

    # C) Multiple files, user chose NOT to combine → export each separately
    out_dir = choose_output_directory()  # Ask for a single folder for all per-file outputs
    if not out_dir:  # If cancelled
        messagebox.showwarning("No Output Folder", "No output folder selected. Exiting.")  # Warn
        return  # Stop

    # Ask once whether to filter the per-file outputs
    apply_filter = messagebox.askyesno("Filter", "Filter by state, city, county, site, coordinates, or cbsa?")  # Offer global filter
    if apply_filter:  # If yes, collect parameters once
        kt = simpledialog.askstring("Filter Type", "Enter: state, city, county, site, coordinates, or cbsa")  # Filter type
        kw = simpledialog.askstring("Keyword", "e.g., Maryland, Baltimore, 39.290, -76.610")  # Filter keyword/coords
    else:
        kt = kw = None  # Set to None to skip filtering

    count = 0  # Counter for exported files
    for (df, pollutant, fname) in frames:  # Iterate each cleaned frame
        df_out = df  # Start with unfiltered
        if apply_filter and kt and kw:  # If filter configured
            df_out = filter_data(df_out, kt, kw)  # Apply filter to this file
        export_cleaned_single(df_out, frequency, out_dir, pollutant, fname)  # Export this file
        count += 1  # Increment counter

    messagebox.showinfo("Done", f"✅ Cleaned and exported {count} file(s) separately.")  # Final success message

if __name__ == "__main__":  # Run only if executed as a script (not when imported)
    main()  # Start the GUI-driven cleaning workflow
