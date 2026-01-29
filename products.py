import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import random
import os

# --- MEEVYY LIVE SCRAPER ---
def scrape_meevyy_live():
    base_url = "https://meevyy.com"
    products_list = []
    page = 1
    
    print("--- Scraping Live Products from Meevyy ---")
    while True:
        url = f"{base_url}/products.json?page={page}&limit=250"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200: break
            
            items = response.json().get('products', [])
            if not items: break
            
            for item in items:
                price = float(item['variants'][0]['price']) if item.get('variants') else 0.0
                image = item['images'][0]['src'] if item.get('images') else ""
                
                products_list.append({
                    'id': int(item.get('id')),
                    'title': item.get('title'),
                    'category': item.get('product_type') or "Personalized",
                    'tags': ", ".join(item.get('tags', [])),
                    'price': price,
                    'description': BeautifulSoup(item.get('body_html', ''), 'html.parser').get_text().strip(),
                    'image_url': image,
                    'vendor': 'Meevyy',
                    'link': f"{base_url}/products/{item.get('handle')}"
                })
            page += 1
            time.sleep(1)
        except Exception as e:
            print(f"Scrape Error: {e}")
            break
    return products_list

# --- SYNTHETIC COMBINATION GENERATOR ---
def generate_additional_combinations():
    occasions = ["Birthday", "Anniversary", "Wedding", "Engagement", "Housewarming", "Diwali", "Christmas", "Rakhi", "Holi", "Eid", "Graduation", "Farewell", "Retirement", "Promotion", "New Baby", "Valentine's Day", "Proposal", "Date Night", "Just Because"]
    relationships = ["Daughter", "Son", "Mother", "Father", "Brother", "Sister", "Parents", "Grandparents", "Spouse", "Husband", "Wife", "Boyfriend", "Girlfriend", "Fiancé", "Partner", "Friend", "Bestie", "Colleague", "Boss", "Mentor", "Lawyer", "Doctor"]
    interests = ["Tech", "Gadgets", "Fashion", "Home Decor", "Travel", "Gourmet Food", "Photography", "Music", "Reading", "Sports", "Gaming", "Art", "Gardening", "Minimalist", "Luxury", "Rustic", "Retro", "Modern", "Vintage", "Quirky"]

    base_templates = [
        {"name": "Premium Photo Frame", "price": 890},
        {"name": "Luxury Gift Hamper", "price": 1990},
        {"name": "Engraved Wooden Plaque", "price": 999},
        {"name": "Personalized Jewelry", "price": 1200}
    ]

    synthetic_list = []
    prod_id = 10000 
    
    print("--- Generating Synthetic Combinations ---")
    for occ in occasions:
        for rel in relationships:
            interest = random.choice(interests)
            template = random.choice(base_templates)
            
            title = f"{template['name']} for {rel}'s {occ}"
            tags = f"{occ.lower()}, {rel.lower()}, {interest.lower()}, personalized"
            desc = f"A {interest}-themed {template['name']} for your {rel}. Perfect for their {occ}."

            synthetic_list.append({
                "id": prod_id,
                "title": title,
                "category": "Personalized",
                "tags": tags,
                "price": template['price'] + random.randint(-50, 200),
                "description": desc,
                "image_url": "https://via.placeholder.com/300",
                "vendor": "Meevyy",
                "link": "#"
            })
            prod_id += 1
    return synthetic_list

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    live_prods = scrape_meevyy_live()
    synth_prods = generate_additional_combinations()
    
    final_df = pd.DataFrame(live_prods + synth_prods)
    final_df.to_csv("optgiftai_database.csv", index=False)
    print(f"Total Database Size: {len(final_df)} products.")