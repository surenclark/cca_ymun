import pandas as pd

def load_data():
    positions_df = pd.read_csv('../data/temp/all_positions.csv')
    committees_df = pd.read_csv('../data/temp/committees.csv')
    countries_df = pd.read_csv('../data/temp/country_regions.csv')
    positions = {}
    for column in positions_df.columns:
        clean_values = positions_df[column].dropna().tolist()
        positions[column] = clean_values

        print(f"{column}: {len(clean_values)} values")
        print(clean_values)
        print()


load_data()