Data used and sourced: https://aqs.epa.gov/aqsweb/airdata/download_files.html#AQI 
What do these scripts do?
●	pollution_data_cleaner_gui.py
A point-and-click cleaner for EPA AQS daily/hourly CSVs (PM₂.₅, PM₁₀, NO₂).
○	Drops low-value columns
○	Adds a Sample ID and Pollutant Name
○	Rounds key numeric fields
○	Optional filtering (State/City/County/Site/CBSA/Coordinates)
○	Exports one cleaned CSV per file or one combined CSV for many files
●	format_by_location.py
Takes a cleaned/combined CSV (must include Pollutant Name) and reshapes it by location:
○	Optional filtering (same options as above)
○	Choose grouping field(s) (State/City/County/Site/CBSA/Coordinates/Custom)
○	Choose value column (e.g., Arithmetic Mean or 1st Max Value)
○	Output style: LONG (tidy) or WIDE (pollutants as columns)
○	Export to CSV or Excel (Excel = one sheet per group)
 
Requirements
●	Python 3.9+
●	Packages:
○	pandas (both scripts)
○	openpyxl (only needed when you export to Excel)
●	Tkinter (bundled with the official Python installers for Windows/macOS)
●	Install packages: pip install pandas openpyxl
●	macOS tip: if you don’t see file-picker dialogs, install Python from python.org (includes a Tk-enabled build).
 
1) Cleaning EPA CSVs (pollution_data_cleaner_gui.py)
Launch in Terminal
python pollution_data_cleaner_gui.py
Step-by-step
1.	“Select your pollutant data CSV file(s).”
○	Pick one or many EPA AQS CSVs (daily or hourly).
○	The tool will try to detect the pollutant from the filename (pm25, pm2.5, pm10, no2,...). If it can’t, it will ask:
“Enter one of: PM2.5, PM10, NO2”
2.	“Data Frequency” → type DAILY or HOURLY (case doesn’t matter).
3.	If you selected multiple files: “Combine Files” → Yes/No.
○	Yes: files are concatenated into one DataFrame.
○	No: each file is cleaned and exported separately.
4.	Optional Filter
When prompted:
○	Filter Type → enter exactly one of:
state, city, county, site, coordinates, or cbsa
○	Keyword → examples:
■	Maryland (state)
■	Baltimore (city)
■	Kane (county)
■	170 (site number; matches by contains)
■	39.290, -76.610 (coordinates; exact match rounded to 3 decimals)
■	Baltimore-Columbia-Towson (CBSA Name; matches by contains; can enter city)
5.	Notes:
○	Text filters use case-insensitive “contains” matching (so “York” will also match “New York”).
○	Coordinates require a comma-separated pair; matching is done at 3 decimal places.
6.	Choose output folder
○	The script writes your cleaned CSV(s) here.
What gets cleaned/added?
●	Drops: Pollutant Standard, Date Last Change, Event Type, AQI, CBSA, Datum (if present)
●	Adds:
○	Sample ID (e.g., PM25-0001, NO2-0001)
○	Pollutant Name (PM2.5, PM10, or NO2)
●	Rounds numeric columns: Arithmetic Mean, 1st Max Value, 1st Max Daily Value (if present) to 3 decimals
Output filenames
Single file export:
{daily|hourly}_{Pollutant}{...}_{originalBase}_cleaned.csv
●	Example: daily_PM25_daily_88101_2024_cleaned.csv
Combined export (when “Combine Files” = Yes):
{daily|hourly}_{PM25_PM10_NO2}_cleaned.csv
●	(pollutant codes concatenated based on what’s in the combined data)
 
2) Format by Location (format_by_location.py)
Launch in Terminal
python format_by_location.py
Step-by-step
1.	“Select cleaned/combined pollutant CSV (must contain 'Pollutant Name').”
○	Choose a CSV produced by the cleaner above.
2.	Optional filter (same options & behavior as the cleaner):
state, city, county, site, cbsa, coordinates
3.	Choose grouping (how you want rows/sheets grouped):
○	state, city, county, site, cbsa, coordinates, or custom
○	You can select multiple grouping columns (e.g., State + City).
○	The script auto-detects the Date column (Date, Date Local, Date Observed, or Date GMT) and converts it to a proper date.
4.	Pick the value column (what number represents the pollutant reading):
○	Common choices: Arithmetic Mean or 1st Max Value.
5.	Choose export style
○	LONG: one row per Sample, with columns like Sample ID, Pollutant Name, Sample Duration, Date, Value, and your chosen group columns (State/City/etc.).
○	WIDE: pivot pollutants into columns (e.g., “NO2”, “PM2.5”, “PM10”), one row per Date (and per group key).
6.	Choose output folder, then CSV or XLSX:
○	CSV → one file
○	XLSX → one workbook; one sheet per group (e.g., a sheet for each City)
Output filenames
WIDE: {inputBase}_wide_by_{group1_group2...}.{csv|xlsx}
LONG: {inputBase}_long_by_{group1_group2...}.{csv|xlsx}
 
Practical examples (copy/paste)
Filter Maryland then pivot to WIDE by City (Excel):
1.	Run cleaner → select multiple CSVs → “Combine Files” = Yes → Filter state = Maryland → save combined.
2.	Run format_by_location → pick the combined CSV → Filter (skip) → Group city → Value Arithmetic Mean → Style WIDE → Export XLSX.
Find a specific monitoring site by coordinates (3-decimal match):
●	Cleaner → Filter coordinates = 39.290, -76.610 (Baltimore downtown area) → export.
●	Then format_by_location for WIDE pivot across pollutants.
 
Troubleshooting & Notes
●	City returning “unexpected” data
Filters contain matches (case-insensitive). Searching for “York” will match New York, Yorktown, etc. Use a more specific keyword (e.g., “Baltimore City” or an exact CBSA Name), or filter by State + City in two passes (see “Multi-criteria” below).
●	Coordinates filter
Match is done at 3 decimals for both latitude and longitude. If your source data keeps more precision or is slightly off, round your target to 3 decimals or search by nearby Site/City first.
●	CBSA
Filter uses CBSA Name (not code). Partial names are OK (contains match).
●	Value column not found
When formatting to WIDE/LONG, make sure your cleaned CSV actually includes the column you pick (e.g., Arithmetic Mean). If not present, go back to the cleaner and ensure you’re using daily/hourly metric files that contain that field.
Excel export error
Install openpyxl: pip install openpyxl
●	Multi-criteria filters (current limitation)
The dialogs accept one filter type + keyword at a time. To apply multiple criteria (e.g., State = Maryland and City = Baltimore), run a two-pass process:
1.	In the cleaner, filter state = Maryland, export.
2.	Re-run the cleaner on that output and filter city = Baltimore, export again.
You can do the same before running format_by_location.py.
 
How your test cases map to the tool
●	Test Case #1
“All files combined successfully, filtering by state works, and searching by CBSA is possible… suggest multi-criteria search.”
- Matches behavior: the cleaner combines files, supports state and cbsa filters. Multi-criteria requires the two-pass approach described above.
●	Test Case #2
“Filtering by state and city works, but searching by city produced unexpected results; actually data were only PM2.5.”
- Expected. City filters are contains matches and the dataset you picked for that city only had PM₂.₅. You can confirm by checking the “Pollutant Name” counts in the combined view or by filtering for other pollutants.
●	Test Case #3
“Selected three files but could not combine or filter by city/state. Exported data confirmed Kane, Illinois, in PM2.5.”
- If “Combine Files” was No, each file exports separately. Your export still verifies County = Kane data exist (filter again on the combined file if you need one merged view).
●	Test Case #4
“Selected all 31 files, could not combine them, but filtering by city/state worked.”
- Same explanation: if you choose not to combine, the per-file filter/export path is used; filters apply and you’ll get multiple cleaned files.
●	Test Case #5
“Selected three files, combined successfully, but filtering by city/state did not work as expected; related cities were returned.”
- This is the contains behavior (e.g., searching “York” returns “New York”). Use a more specific keyword, filter on CBSA Name, or apply State + City using the two-pass method.
 
Quick reference (prompts & accepted values)
●	Cleaner – Filter Type: state | city | county | site | coordinates | cbsa
●	Cleaner – Coordinates Keyword: "lat, lon" (e.g., 39.290, -76.610)
●	Cleaner – Frequency: DAILY or HOURLY
●	Format – Grouping: state | city | county | site | cbsa | coordinates | custom
●	Format – Value Column: Arithmetic Mean or 1st Max Value (commonly)
●	Format – Style: LONG or WIDE
●	Excel export: requires openpyxl
 
Suggested workflow (most common)
1.	Clean & (optionally) filter raw daily/hourly CSVs with pollution_data_cleaner_gui.py.
2.	Format the cleaned result by location with format_by_location.py → choose WIDE for dashboards, LONG for analysis.
3.	If you need State + City or City + Site, apply filters in two passes (clean → re-clean; or clean → format).

