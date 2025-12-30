import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import random
import re

# --- SELENIUM IMPORTS ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- SHARED UTILITIES ---
def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    }

def clean_html(html_text):
    if not html_text: return ""
    return BeautifulSoup(html_text, 'html.parser').get_text(separator=' ').strip()

# --- SCRAPER 1: MEEVYY (Shopify API) ---
def scrape_meevyy():
    base_url = "https://meevyy.com"
    products_list = []
    page = 1
    
    print(f"\n--- Starting MEEVYY Scrape (Auto-Pagination) ---")
    
    while True:
        # Request up to 250 items per page
        url = f"{base_url}/products.json?page={page}&limit=250"
        
        try:
            print(f"   [Meevyy] Requesting Page {page}...")
            response = requests.get(url, headers=get_headers(), timeout=10)
            
            if response.status_code != 200:
                print(f"   [Meevyy] Stopping: Status Code {response.status_code}")
                break
            
            data = response.json()
            items = data.get('products', [])
            
            # STOPPING CONDITION: If the list is empty, we are done.
            if not items:
                print("   [Meevyy] No more products found. Finished.")
                break
                
            print(f"   [Meevyy] Found {len(items)} items on page {page}")
            
            for item in items:
                # (Your existing parsing logic here)
                try:
                    price = float(item['variants'][0]['price']) if item.get('variants') else 0.0
                    image = item['images'][0]['src'] if item.get('images') else ""
                    
                    products_list.append({
                        'id': str(item.get('id')),
                        'title': item.get('title'),
                        'category': item.get('product_type') or "Personalized",
                        'tags': ", ".join(item.get('tags', [])),
                        'price': price,
                        'description': clean_html(item.get('body_html')),
                        'image_url': image,
                        'vendor': 'Meevyy',
                        'link': f"{base_url}/products/{item.get('handle')}"
                    })
                except Exception as e:
                    continue

            page += 1 # Move to next page
            time.sleep(1) # Be polite to the server
            
        except Exception as e:
            print(f"   [Meevyy] Error: {e}")
            break

    return pd.DataFrame(products_list)

# --- SCRAPER 2: MARK & GRAHAM (Selenium) ---
def scrape_markandgraham(num_pages=2):
    # Target "Gifts for Her" or a similar category
    base_url = "https://www.markandgraham.com/shop/gifts-for-her/all-gifts-for-her/"
    products_list = []
    print(f"\n--- Starting MARK & GRAHAM Scrape (Selenium) ---")

    chrome_options = Options()
    # chrome_options.add_argument("--headless") # Uncomment to hide browser
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # Mark & Graham usually shows all products on one scrollable page or pagination
        # We will iterate through pages if possible, or just scrape the first X pages
        
        # M&G Pagination format is typically not url parameter based for infinite scroll,
        # but often uses ?page=2 or similar structure on category pages.
        # Let's try standard URL pagination
        
        for page in range(1, num_pages + 1):
            # Construct URL (Adjust based on actual site behavior if needed)
            # This is a common pattern, but M&G might use infinite scroll.
            # If so, a scroll-down loop would be needed instead. 
            # For simplicity, we try direct page access assuming standard parameters or just page 1.
            
            # Note: M&G urls don't always use ?page=X cleanly. 
            # If page > 1, we might skip or try to locate the 'next' button.
            # For now, let's just scrape the main list on page 1 heavily.
            if page > 1: 
                print("   [M&G] Pagination complex; skipping subsequent pages for this demo.")
                break
                
            print(f"   [M&G] Loading page...")
            driver.get(base_url)
            
            # Wait for product grid
            try:
                # Common class for M&G products: 'product-cell' or 'product-item'
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "product-cell"))
                )
            except:
                print("   [M&G] Timeout waiting for products.")
            
            # Scroll to load lazy images
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/1.5);")
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Selectors for Mark & Graham
            cards = soup.find_all('div', class_='product-cell') # Identify product container
            
            print(f"   [M&G] Found {len(cards)} items.")

            for card in cards:
                try:
                    # Title
                    title_tag = card.find('a', class_='product-name') or card.find('div', class_='name')
                    title = title_tag.get_text().strip() if title_tag else "Unknown"
                    if title == "Unknown": continue

                    # Price
                    # M&G prices often have ranges or sale prices.
                    price = 0.0
                    price_tag = card.find('span', class_='product-price-amount') or card.find('span', class_='price-amount')
                    if price_tag:
                        raw = price_tag.get_text().replace('$', '').replace(',', '')
                        # Handle "$59 - $100" by taking the first number
                        raw = raw.split('-')[0].strip()
                        match = re.search(r'\d+\.?\d*', raw)
                        if match: price = float(match.group())

                    # Image
                    img_tag = card.find('img', class_='product-thumb')
                    image_url = ""
                    if img_tag:
                        image_url = img_tag.get('src') or img_tag.get('data-src')

                    # Link
                    link_tag = card.find('a', href=True)
                    link = link_tag['href'] if link_tag else ""
                    if link and not link.startswith('http'):
                        link = "https://www.markandgraham.com" + link
                    
                    # Generate ID
                    prod_id = str(abs(hash(title + link)))
                    
                    products_list.append({
                        'id': prod_id,
                        'title': title,
                        'category': 'Premium Personalized',
                        'tags': 'mark&graham, luxury, monogram',
                        'price': price * 83, # Convert USD to INR approx
                        'description': f"{title} - Mark & Graham Premium Gift",
                        'image_url': image_url,
                        'vendor': 'Mark & Graham',
                        'link': link
                    })
                except Exception as ex:
                    continue
                    
    except Exception as e:
        print(f"   [M&G] Error: {e}")
    finally:
        driver.quit()

    return pd.DataFrame(products_list)

# --- SCRAPER 3: IGP (Selenium) ---
def scrape_igp(num_pages=2):
    # ... (Keep your existing IGP scraper code here) ...
    # For brevity, I'm just putting a placeholder. 
    # COPY PASTE YOUR PREVIOUS IGP FUNCTION HERE if you want all 3.
    # If you only want Meevyy + M&G, you can remove this.
    return pd.DataFrame() 

# --- MAIN ---
if __name__ == "__main__":
    # 1. Scrape Meevyy
    df_meevyy = scrape_meevyy()
    
    # 2. Scrape Mark & Graham
    df_mg = scrape_markandgraham(num_pages=1)
    
    # 3. Combine
    print("\n--- Merging Data ---")
    final_df = pd.concat([df_meevyy, df_mg], ignore_index=True)
    
    if not final_df.empty:
        # Shuffle
        final_df = final_df.sample(frac=1).reset_index(drop=True)
        print(f"Saved {len(final_df)} products to 'optgiftai_database.csv'")
        print(final_df[['title', 'price', 'vendor']].head())
        final_df.to_csv("optgiftai_database.csv", index=False)
    else:
        print("No data found.")