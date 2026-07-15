#!/usr/bin/env python3
"""
GDP Data Cleaner

This script processes a World Bank CSV export (GDP in USD) by:
- Skipping non-header rows
- Dropping indicator columns
- Reshaping from wide to long format
- Adding classification columns (Regions, Income Group, Institutional, Unions)
- Removing classification strings from Country Name
- Saving the cleaned data to a CSV file

Usage:
    python cleanup.py --input PATH/TO/INPUT.csv --output PATH/TO/OUTPUT.csv
"""

import argparse
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional


# ------------------------------------------------------------------
# Mapping: aggregate country codes -> classification strings
# ------------------------------------------------------------------
CODE_MAPPING = {
    'AFE': ('Africa Eastern and Southern', '', '', ''),
    'AFW': ('Africa Western and Central', '', '', ''),
    'ARB': ('Arab World', '', '', ''),
    'CEB': ('Central Europe and the Baltics', '', '', ''),
    'CSS': ('Caribbean small states', '', '', ''),
    'EAP': ('East Asia & Pacific (excluding high income)', '', '', ''),
    'EAR': ('Early-demographic dividend', '', '', ''),
    'EAS': ('East Asia & Pacific', '', '', ''),
    'ECA': ('Europe & Central Asia (excluding high income)', '', '', ''),
    'ECS': ('Europe & Central Asia', '', '', ''),
    'FCS': ('Fragile and conflict affected situations', '', '', ''),
    'HPC': ('Heavily indebted poor countries (HIPC)', '', '', ''),
    'LAC': ('Latin America & Caribbean (excluding high income)', '', '', ''),
    'LCN': ('Latin America & Caribbean', '', '', ''),
    'LDC': ('Least developed countries: UN classification', '', '', ''),
    'LTE': ('Late-demographic dividend', '', '', ''),
    'MEA': ('Middle East, North Africa, Afghanistan & Pakistan', '', '', ''),
    'MNA': ('Middle East, North Africa, Afghanistan & Pakistan (excluding high income)', '', '', ''),
    'NAC': ('North America', '', '', ''),
    'OED': ('OECD members', '', '', ''),
    'OSS': ('Other small states', '', '', ''),
    'PRE': ('Pre-demographic dividend', '', '', ''),
    'PSS': ('Pacific island small states', '', '', ''),
    'PST': ('Post-demographic dividend', '', '', ''),
    'SAS': ('South Asia', '', '', ''),
    'SSA': ('Sub-Saharan Africa (excluding high income)', '', '', ''),
    'SSF': ('Sub-Saharan Africa', '', '', ''),
    'SST': ('Small states', '', '', ''),
    'TEA': ('East Asia & Pacific (IDA & IBRD countries)', '', '', ''),
    'TEC': ('Europe & Central Asia (IDA & IBRD countries)', '', '', ''),
    'TLA': ('Latin America & the Caribbean (IDA & IBRD countries)', '', '', ''),
    'TMN': ('Middle East, North Africa, Afghanistan & Pakistan (IDA & IBRD)', '', '', ''),
    'TSA': ('South Asia (IDA & IBRD)', '', '', ''),
    'TSS': ('Sub-Saharan Africa (IDA & IBRD countries)', '', '', ''),
    'WLD': ('World', '', '', ''),
    'HIC': ('', 'High income', '', ''),
    'LIC': ('', 'Low income', '', ''),
    'LMC': ('', 'Lower middle income', '', ''),
    'LMY': ('', 'Low & middle income', '', ''),
    'MIC': ('', 'Middle income', '', ''),
    'UMC': ('', 'Upper middle income', '', ''),
    'IBD': ('', '', 'IBRD only', ''),
    'IBT': ('', '', 'IDA & IBRD total', ''),
    'IDA': ('', '', 'IDA total', ''),
    'IDB': ('', '', 'IDA blend', ''),
    'IDX': ('', '', 'IDA only', ''),
    'EMU': ('', '', '', 'Euro area'),
    'EUU': ('', '', '', 'European Union'),
}


def find_header_row(file_path: Path) -> int:
    """
    Locate the header row in the raw CSV file.

    The header row is the first line that starts with '"Country Name"'.

    Args:
        file_path: Path to the input CSV file.

    Returns:
        The 0‑based index of the header row.

    Raises:
        ValueError: If the header row cannot be found.
    """
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        for i, line in enumerate(f):
            if line.strip().startswith('"Country Name"'):
                return i
    raise ValueError("Header row starting with 'Country Name' not found.")


def load_raw_data(file_path: Path) -> pd.DataFrame:
    """
    Load the raw CSV, skipping rows before the header, and drop indicator columns.

    Args:
        file_path: Path to the input CSV file.

    Returns:
        A DataFrame containing the raw data (wide format) without indicator columns.
    """
    header_idx = find_header_row(file_path)
    df = pd.read_csv(file_path, skiprows=header_idx, encoding='utf-8-sig')

    # Drop any columns whose name contains "indicator" (case‑insensitive)
    cols_to_drop = [col for col in df.columns if 'indicator' in col.lower()]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    if df.empty:
        raise ValueError("Loaded DataFrame is empty.")
    return df


def melt_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reshape the DataFrame from wide (years as columns) to long format.

    Keeps 'Country Name' and 'Country Code' as identifiers, converts
    year columns to numeric, and drops rows with missing GDP.

    Args:
        df: Raw DataFrame in wide format.

    Returns:
        Melted DataFrame with columns: Country Name, Country Code, Year, GDP (USD).
    """
    id_vars = ['Country Name', 'Country Code']
    year_cols = [col for col in df.columns if col not in id_vars]

    melted = df.melt(id_vars=id_vars, var_name='Year', value_name='GDP (USD)')

    # Convert Year to integer
    melted['Year'] = pd.to_numeric(melted['Year'], errors='coerce').astype('Int64')

    # Drop rows where GDP is missing or invalid
    melted['GDP (USD)'] = pd.to_numeric(melted['GDP (USD)'], errors='coerce')
    melted = melted.dropna(subset=['GDP (USD)'])

    if melted.empty:
        raise ValueError("Melted DataFrame is empty after dropping missing GDP values.")
    return melted


def add_classifications(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add four classification columns based on the Country Code.

    The columns added are: Regions, Income Group, Institutional, Unions.

    Args:
        df: DataFrame with a 'Country Code' column.

    Returns:
        The DataFrame with the new classification columns added.
    """
    # Initialize empty columns
    for col in ['Regions', 'Income Group', 'Institutional', 'Unions']:
        df[col] = ''

    # Fill based on mapping
    for code, (reg, inc, inst, uni) in CODE_MAPPING.items():
        mask = df['Country Code'] == code
        df.loc[mask, 'Regions'] = reg
        df.loc[mask, 'Income Group'] = inc
        df.loc[mask, 'Institutional'] = inst
        df.loc[mask, 'Unions'] = uni

    return df


def clean_country_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove classification strings from the 'Country Name' column.

    The classification strings (Regions, Income Group, Institutional, Unions)
    are removed from the country name if they appear as substrings.

    Args:
        df: DataFrame containing the four classification columns.

    Returns:
        The DataFrame with cleaned 'Country Name' column.
    """
    def _clean_name(row: pd.Series) -> str:
        name = row['Country Name']
        for col in ['Regions', 'Income Group', 'Institutional', 'Unions']:
            val = row[col]
            if val and val != '':
                name = name.replace(val, '')
        return name.strip()

    df['Country Name'] = df.apply(_clean_name, axis=1)
    return df


def process_data(input_path: Path) -> pd.DataFrame:
    """
    Run the entire cleaning pipeline.

    Args:
        input_path: Path to the raw CSV file.

    Returns:
        The final cleaned DataFrame.
    """
    raw_df = load_raw_data(input_path)
    melted_df = melt_data(raw_df)
    classified_df = add_classifications(melted_df)
    cleaned_df = clean_country_names(classified_df)

    # Sort by Country Code and Year (descending)
    cleaned_df = cleaned_df.sort_values(['Country Code', 'Year'], ascending=[True, False])

    # Define the output column order
    output_columns = [
        'Country Name', 'Country Code', 'Year', 'GDP (USD)',
        'Regions', 'Income Group', 'Institutional', 'Unions'
    ]
    return cleaned_df[output_columns]


def save_data(df: pd.DataFrame, output_path: Path) -> None:
    """
    Save the cleaned DataFrame to a CSV file.

    Args:
        df: DataFrame to save.
        output_path: Destination file path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')


def main() -> None:
    """Parse command‑line arguments and run the cleaning pipeline."""
    parser = argparse.ArgumentParser(
        description="Clean World Bank GDP CSV data."
    )
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help="Path to the raw CSV file (e.g., data/API_NY.GDP.MKTP.CD_DS2_en_csv_v2_2.csv)."
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('outputs/cleaned_up.csv'),
        help="Path where the cleaned CSV will be saved (default: outputs/cleaned_up.csv)."
    )
    args = parser.parse_args()

    # Validate input file existence
    if not args.input.is_file():
        raise FileNotFoundError(f"Input file not found: {args.input}")

    try:
        cleaned_df = process_data(args.input)
        save_data(cleaned_df, args.output)
        print(f"Cleaned data saved to {args.output}")
    except Exception as e:
        print(f"Error during processing: {e}")
        raise


if __name__ == "__main__":
    main()