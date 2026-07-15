#!/usr/bin/env python3
"""
clean_cdc_data.py

Remove redundant 'All causes' and 'United States' rows from CDC mortality data.
These rows represent pre‑aggregated totals; removing them avoids double‑counting
when summing deaths manually.

USAGE:
    1. Set the INPUT_FILE variable below to the full path of your CSV file.
    2. Run: python clean_cdc_data.py
    3. The cleaned file will appear in the current directory as cleaned_<filename>.
"""

import pandas as pd
import os

# ================== USER CONFIGURATION ==================
# Paste the full path to your input CSV file here.
INPUT_FILE = ""   # <-- CHANGE THIS
# ========================================================

def main():
    # Check if the input file exists
    if not os.path.isfile(INPUT_FILE):
        print(f"Error: Input file not found at '{INPUT_FILE}'")
        print("Please set the INPUT_FILE variable to a valid path.")
        return

    # Read the CSV
    df = pd.read_csv(INPUT_FILE)

    # Strip whitespace from string columns for consistent filtering
    df['State'] = df['State'].str.strip()
    df['Cause Name'] = df['Cause Name'].str.strip()
    df['113 Cause Name'] = df['113 Cause Name'].str.strip()

    # Conditions to drop:
    # 1. State is 'United States'
    is_us = df['State'] == 'United States'

    # 2. Either cause column equals 'All causes' (case‑insensitive)
    #    Use parentheses around each comparison to avoid precedence issues.
    is_all_causes = (df['Cause Name'].str.lower() == 'all causes') | \
                    (df['113 Cause Name'].str.lower() == 'all causes')

    # Keep rows that are neither US totals nor All‑cause totals
    cleaned_df = df[~(is_us | is_all_causes)]

    # Build output path: current directory + 'cleaned_' + original filename
    base_name = os.path.basename(INPUT_FILE)
    output_path = os.path.join(os.getcwd(), f"cleaned_{base_name}")

    # Save the cleaned data
    cleaned_df.to_csv(output_path, index=False)

    removed = len(df) - len(cleaned_df)
    print(f"Removed {removed} rows.")
    print(f"Cleaned data saved to: {output_path}")

if __name__ == "__main__":
    main()