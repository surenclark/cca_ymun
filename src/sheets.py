import os

import pandas as pd
import requests


def download_sheets(sheet_url, output_folder='test_data'):
    """
    Downloads the MUN sheets from Google Sheets
    """
    print("="*60)
    print("📥 DOWNLOADING GOOGLE SHEETS")
    print("="*60)

    # Create output folder
    os.makedirs(output_folder, exist_ok=True)

    # Clean the URL and extract document ID
    doc_id = sheet_url.split('/d/')[1].split('/')[0]

    sheets = {
        'committees': '952298514',
        'all_positions': '834022118',
        'preferences': '2142368126',
        'country_regions': '303432024'
    }

    downloaded_files = {}

    for sheet_name, gid in sheets.items():
        export_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}"

        print(f"\n  Downloading {sheet_name}...")
        try:
            response = requests.get(export_url)
            response.raise_for_status()

            output_path = os.path.join(output_folder, f"{sheet_name}.csv")
            with open(output_path, 'wb') as f:
                f.write(response.content)

            df = pd.read_csv(output_path)
            print(f"  ✅ Downloaded: {len(df)} rows, {len(df.columns)} columns")

            downloaded_files[sheet_name] = output_path

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print(f"\n✅ Downloaded {len(downloaded_files)} files to '{output_folder}/'")
    return downloaded_files
