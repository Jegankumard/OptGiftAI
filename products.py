
import pandas as pd
import os

def load_local_database():
    """
    Fetches data from the local CSV file provided.
    Skips web scraping.
    """
    csv_file = "optgiftai_database.csv"
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        print(f"Successfully fetched {len(df)} items from {csv_file}")
        return df
    else:
        print(f"Error: {csv_file} not found.")
        return None

if __name__ == "__main__":
    # SKIPPING: live_prods = scrape_meevyy_live()
    # SKIPPING: synth_prods = generate_additional_combinations()
    
    print("--- Local Data Fetching Mode ---")
    data = load_local_database()
    
    if data is not None:
        print("\nFirst 5 products in database:")
        print(data[['id', 'title', 'price']].head())
        
        # Optional: Save a backup or clean the data if needed
        # data.to_csv("optgiftai_database_cleaned.csv", index=False)