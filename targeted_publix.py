from playwright.sync_api import sync_playwright
import csv
import time
from datetime import datetime
import multiprocessing
import os
from functools import partial
import traceback
import random
import argparse

# Define the target products to find in each category
TARGET_PRODUCTS = {
    "Beef": [
        "publix lean ground beef",
        "publix bottom round roast",
        "publix beef patties",
        "usda choice beef"
    ],
    "Bread": [
        "pepperidge farm white bread",
        "publix bread 100% whole wheat",
        "publix bakery sourdough round",
        "publix bread white old fashioned enriched"
    ],
    "Butter": [
        "publix butter sweet cream unsalted",
        "publix butter salted sweet cream",
        "land o lakes butter with canola oil",
        "land o lakes salted butter"
    ],
    "Canned Beans": [
        "publix black beans",
        "publix kidney beans light red",
        "bush's best pinto beans",
        "old el paso refried beans black bean",
        "goya premium black beans",
        "goya premium pinto beans"
    ],
    "Cereal": [
        "quaker original multigrain cereal",
        "kellogg's special k",
        "cap'n crunch cereal",
        "general mills honey nut cheerios",
        "frosted flakes"
    ],
    "Chicken": [
        "publix boneless skinless chicken breast",
        "publix chicken all natural boneless skinless chicken thighs",
        "publix whole young chicken"
    ],
    "Chips": [
        "lay's potato chips classic",
        "tostitos tortilla chips original scoops party size",
        "frito lay snacks classic mix variety",
        "lay's potato chips barbecue",
        "cape cod sea salt & vinegar chips"
    ],
    "Coffee": [
        "maxwell house house blend medium roast",
        "café bustelo roast & ground coffee",
        "publix coffee espresso cafe espresso",
        "nescafé clásico dark roast instant coffee",
        "dunkin' decaf original blend ground coffee"
    ],
    "Cooking Oils": [
        "publix vegetable oil",
        "bertolli olive oil extra virgin",
        "publix canola oil",
        "publix coconut oil",
        "pam non stick butter cooking spray",
        "publix olive oil extra virgin",
        "crisco oil pure canola"
    ],
    "Deli Meats": [
        "prime fresh honey ham",
        "smithfield turkey breast",
        "publix chicken rotisserie seasoned thin sliced",
        "publix deli salami genoa sliced",
        "hormel pepperoni original"
    ],
    "Eggs": [
        "publix eggs large",
        "publix large grade a eggs",
        "eggland's best grade a large white eggs",
        "publix eggs medium",
        "eggland's best classic extra large white eggs"
    ],
    "Fresh Fruits": [
        "gala apple",
        "bananas",
        "navel oranges",
        "strawberries",
        "red seedless grapes",
        "lemon"
    ],
    "Fresh Vegetables": [
        "russet potatoes",
        "publix yellow onions",
        "publix carrots sticks",
        "romaine lettuce",
        "asparagus",
        "red onion",
        "cucumber",
        "broccoli",
        "garlic",
        "shallot",
        "greenwise organic spinach",
        "tomatoes on the vine"
    ],
    "Jams Jellies": [
        "smucker's strawberry jelly",
        "publix jelly concord grape",
        "welch's concord grape jelly",
        "smucker's jam"
    ],
    "Juice": [
        "tropicana pure premium 100% orange juice",
        "publix original orange juice",
        "welch's passion fruit",
        "mott's 100% original apple juice",
        "simply lemonade"
    ],
    "Lager": [
        "budweiser american lager beer",
        "corona extra mexican lager",
        "heineken original lager beer"
    ],
    "Light Beer": [
        "bud light platinum",
        "coors light american light lager beer",
        "miller lite american light lager beer",
        "michelob ultra superior light american lager beer"
    ],
    "Milk": [
        "publix milk whole",
        "publix milk reduced fat 2% milkfat",
        "silk soy milk original",
        "publix milk chocolate"
    ],
    "Pasta": [
        "publix spaghetti",
        "barilla whole grain spaghetti",
        "barilla penne",
        "publix pasta penne rigate",
        "publix angel hair"
    ],
    "Red Wine": [
        "josh cellars cabernet sauvignon",
        "robert mondavi private selection bourbon barrel aged cabernet sauvignon",
        "apothic red blend",
        "yellow tail merlot",
        "barefoot pinot noir"
    ],
    "Spices Seasoning": [
        "mccormick black pepper ground",
        "mccormick gourmet organic paprika",
        "publix onion powder",
        "publix paprika",
        "publix garlic powder",
        "spice islands cilantro",
        "mccormick ground cinnamon",
        "mccormick gourmet organic italian seasoning"
    ],
    "White Wine": [
        "kendall-jackson chardonnay",
        "santa margherita pinot grigio",
        "barefoot chardonnay",
        "yellow tail pinot grigio",
        "yellow tail chardonnay"
    ],
    "Cheese": [
        "kraft shredded cheese mozzarella",
        "publix cheese singles american",
        "publix cheese swiss",
        "publix cheese grated parmesan",
        "boar's head irish cheddar cheese"
    ],
    "Baby Food Drinks": [
        "gerber apples 2nd foods",
        "gerber stage 2"
    ],
    "Paper Goods": [
        "bounty full sheet paper towels",
        "charmin ultra soft toilet paper mega rolls",
        "vanity fair napkin"
    ],
    "Trash Bins Bags": [
        "publix tall kitchen garbage bags",
        "hefty trash bags",
        "glad kitchen bags"
    ]
}

def extract_item_details(deli_item, location):
    """Extract item details from a product element."""
    price = "Not found"
    for price_class in ['div.e-2feaft', 'div.e-s71gfs']:
        price_div = deli_item.locator(price_class).first
        price_span = price_div.locator('span.screen-reader-only').first
        if price_span.count() > 0:
            full_price = price_span.inner_text()
            price = full_price.split('$')[1] if '$' in full_price else full_price
            break

    grocery_div = deli_item.locator('div.e-147kl2c').first
    product_name = grocery_div.inner_text() if grocery_div.count() > 0 else "Not found"

    ozs_div = deli_item.locator('div.e-an4oxa').first
    ounces = ozs_div.inner_text() if ozs_div.count() > 0 else "Not found"

    return {
        "Location": location,
        "Product Name": product_name,
        "Price": f"${price}" if not price.startswith("$") else price,
        "Ounces": ounces
    }

def scroll_to_load_all_items(page):
    last_height = page.evaluate("document.body.scrollHeight")
    max_scroll_attempts = 5  # Reduced from 10 to improve performance
    scroll_attempts = 0
    
    while scroll_attempts < max_scroll_attempts:
        # Scroll down to bottom
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        
        # Wait to load more content
        page.wait_for_timeout(800)  # Reduced from 1000 to improve performance
        
        # Calculate new scroll height and compare with last scroll height
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            final_height = page.evaluate("document.body.scrollHeight")
            if final_height == new_height:
                break
        
        last_height = new_height
        scroll_attempts += 1
        
    # Check for "Show More" or "Load More" buttons
    try:
        load_more = page.locator("button:has-text('Load More')").first
        if load_more.count() > 0 and load_more.is_visible():
            load_more.click()
    except Exception as e:
        pass 

def navigate_with_retry(page, url, max_retries=2):  # Reduced from 3 to improve performance
    """Navigate to URL with retry logic"""
    for attempt in range(max_retries):
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(800)  # Reduced from 1000 to improve performance
            
            # Check if page loaded correctly
            if page.url.startswith(url.split("?")[0]):  
                return True
            else:
                pass
        except Exception as e:
            pass
    
    print(f"Failed to navigate to {url} after {max_retries} attempts")
    return False

def is_target_product(product_name, category):
    """Check if the product is one of our target products for this category"""
    if category not in TARGET_PRODUCTS:
        return False
        
    product_name_lower = product_name.lower()
    
    # Check if product name contains any of our target keywords for this category
    for target in TARGET_PRODUCTS[category]:
        if target in product_name_lower:
            return True
    
    return False

def scrape_deli_items(page, location, category):
    """Enhanced scraping function that filters for target products only"""
    scroll_to_load_all_items(page)
    
    # Try multiple selectors to find products
    selectors = ['h3.e-ti75j2', 'div.e-1qh5kfx', 'div.product-item', 'li.product-item']
    
    items = None
    items_count = 0
    used_selector = ""
    
    for selector in selectors:
        items = page.locator(selector)
        items_count = items.count()
        if items_count > 0:
            used_selector = selector
            break
    
    if items_count == 0:
        return []

    deli_data = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    for i in range(items_count):
        try:
            item = items.nth(i)
            
            # If using a different selector than the original, adjust extraction logic
            if used_selector != 'h3.e-ti75j2':
                # Try to find the product name and price within this item
                name_element = item.locator('h3, .product-name, div.e-147kl2c').first
                price_element = item.locator('.product-price, div.e-2feaft, div.e-s71gfs').first
                
                product_name = name_element.inner_text() if name_element.count() > 0 else "Not found"
                price = price_element.inner_text() if price_element.count() > 0 else "Not found"
                
                # Try to find ounces information
                ozs_element = item.locator('div.e-an4oxa, .product-size').first
                ounces = ozs_element.inner_text() if ozs_element.count() > 0 else "Not found"
                
                # Only add if it's a target product
                if is_target_product(product_name, category):
                    row = [
                        location,
                        category,
                        product_name,
                        price,
                        ounces,
                        current_date
                    ]
                    deli_data.append(row)
            else:
                # Use original extraction logic
                item_details = extract_item_details(item, location)
                
                # Only add if it's a target product
                if is_target_product(item_details["Product Name"], category):
                    row = [
                        item_details["Location"],
                        category,
                        item_details["Product Name"],
                        item_details["Price"],
                        item_details["Ounces"],
                        current_date
                    ]
                    deli_data.append(row)
        except Exception as e:
            continue
    
    return deli_data

def append_to_csv(filename, data, lock=None):
    if not data:
        return
    
    if lock:
        lock.acquire()
    
    try:
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(data)
    finally:
        if lock:
            lock.release()

def process_location(location_data, urls, output_file, lock, headless=True):
    """Process a single location in its own process"""
    location, worker_id = location_data
    
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)
            context = browser.new_context(
                permissions=["geolocation"],
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            
            # Start at storefront with retry logic
            if not navigate_with_retry(page, "https://delivery.publix.com/store/publix/storefront"):
                browser.close()
                return

            # Handle Confirm button
            try:
                continue_button = page.get_by_role("button", name="Confirm")
                if continue_button.is_visible():
                    continue_button.click()
                else:
                    pass
            except Exception as e:
                print(f"Error with Confirm button for {location}: {e}")

            # Change location
            try:
                # Try multiple selectors for the location button
                location_button_selectors = ["button.e-1v873ap", "button.e-4jnww6"]
                zip_button = None
                
                for selector in location_button_selectors:
                    zip_button = page.locator(selector).first
                    if zip_button.count() > 0 and zip_button.is_visible(timeout=1000):
                        zip_button.click()
                        break
                
                if not zip_button or zip_button.count() == 0:
                    browser.close()
                    return

                address_input = page.locator("input#streetAddress").first
                
                if address_input.count() > 0:
                    address_input.click()
                    address_input.fill("")
                    time.sleep(0.3)  # Reduced from 0.5 to improve performance
                    address_input.fill(location)
                    page.wait_for_timeout(800)  # Reduced from 1000 to improve performance

                    # Try to find suggestions
                    suggestion = page.locator("ul#address-suggestion-list li[role='option']").first
                    if suggestion.is_visible():
                        suggestion.click()
                        page.wait_for_timeout(800)  # Reduced from 1000 to improve performance
                    else:
                        print(f"Worker {worker_id}: No suggestions found for {location}, pressing Enter")
                        address_input.press("Enter")
                        page.wait_for_timeout(800)  # Reduced from 1000 to improve performance
                    
                    # Try multiple approaches to find and click the save button
                    save_found = False
                    
                    # Approach 1: Try the exact selector from the HTML you provided
                    save_button = page.locator("button.e-129sec0:has(span:text('Save Address'))").first
                    if save_button.count() > 0 and save_button.is_visible(timeout=1000):
                        save_button.click()
                        save_found = True
                    
                    # Approach 2: Try specific selectors
                    if not save_found:
                        save_button_selectors = [
                            "button.e-129sec0", 
                            "button.e-y9ioae", 
                            "button:has-text('Save Address')",
                            "button[type='submit']"
                        ]
                        
                        for selector in save_button_selectors:
                            save_button = page.locator(selector).first
                            if save_button.count() > 0 and save_button.is_visible(timeout=1000):
                                save_button.click()
                                save_found = True
                                break
                    
                    # Approach 3: If no specific selector worked, try to find any visible button
                    if not save_found:
                        buttons = page.locator("button").all()
                        for button in buttons:
                            try:
                                if button.is_visible():
                                    button_text = button.inner_text()
                                    if any(keyword in button_text.lower() for keyword in ["save", "done", "confirm", "submit", "address"]):
                                        button.click()
                                        save_found = True
                                        break
                            except:
                                continue
                    
                    # Wait for page to update with new location
                    page.wait_for_timeout(1500)  # Reduced from 2000 to improve performance
                else:
                    browser.close()
                    return
            except Exception as e:
                browser.close()
                return

            # Scrape URLs
            all_data = []
            for url_info in urls:
                url = url_info["url"]
                category = url_info["category"]
                
                # Skip categories that aren't in our target list
                if category not in TARGET_PRODUCTS:
                    continue
                
                try:
                    # Use retry navigation
                    if not navigate_with_retry(page, url):
                        continue
                    
                    # Add small random delay to avoid detection
                    time.sleep(random.uniform(0.5, 1.5))  # Reduced from 1-3 to improve performance
                    
                    # Check for confirm button again after navigation
                    try:
                        continue_button = page.get_by_role("button", name="Confirm")
                        if continue_button.is_visible():
                            continue_button.click()
                            page.wait_for_timeout(800)  # Reduced from 1000 to improve performance
                    except:
                        pass
                    
                    deli_data = scrape_deli_items(page, location, category)
                    all_data.extend(deli_data)
                except Exception as e:
                    continue
            
            # Save data for this location
            if all_data:
                append_to_csv(output_file, all_data, lock)
                print(f"Worker {worker_id}: Added {len(all_data)} products for {location}")
            else:
                print(f"Worker {worker_id}: No target products found for {location}")
            
            browser.close()
            print(f"Worker {worker_id}: Completed processing location: {location}")
    
    except Exception as e:
        print(traceback.format_exc())

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape Publix product data')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode (slower, more verbose)')
    parser.add_argument('--workers', type=int, default=1, help='Number of worker processes (1 = auto)')
    args = parser.parse_args()
    
    # Use headless mode unless in debug mode
    headless = not args.debug
    
    # Read locations from CSV
    locations = []
    try:
        with open('publix_locations.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                locations.append(row['location'])
        print(f"Total locations to process: {len(locations)}")
    except Exception as e:
        print(f"Error reading publix_locations.csv: {e}")
        return

    # Filtered URLs with categories matching our target products
    urls = [
        {"url": "https://delivery.publix.com/store/publix/collections/n-beef-17864", "category": "Beef"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-bread-15280", "category": "Bread"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-butter-51263", "category": "Butter"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-canned-beans-78884", "category": "Canned Beans"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-cereal-20111", "category": "Cereal"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-chicken-59213", "category": "Chicken"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-chips-55178", "category": "Chips"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-coffee-36369", "category": "Coffee"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-cooking-oils-4131", "category": "Cooking Oils"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-deli-meats-63527", "category": "Deli Meats"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-eggs-83685", "category": "Eggs"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-fresh-fruits-91006", "category": "Fresh Fruits"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-fresh-vegetables-3995", "category": "Fresh Vegetables"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-jams-jellies-32363", "category": "Jams Jellies"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-juice-50886", "category": "Juice"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-lager-72005", "category": "Lager"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-light-beer-20466", "category": "Light Beer"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-milk-22980", "category": "Milk"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-pasta-49998", "category": "Pasta"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-red-wine-5727", "category": "Red Wine"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-spices-seasoning-33818", "category": "Spices Seasoning"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-white-wine-76269", "category": "White Wine"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-cheese-10478", "category": "Cheese"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-baby-food-drinks-22413", "category": "Baby Food Drinks"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-paper-goods-28545", "category": "Paper Goods"},
        {"url": "https://delivery.publix.com/store/publix/collections/n-trash-bins-bags-84758", "category": "Trash Bins Bags"}
    ]

    # Set up output file
    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = f"publix_targeted_data_{timestamp}.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Location', 'Category', 'Product Name', 'Price', 'Ounces', 'Date'])

    # Create a lock for file access
    manager = multiprocessing.Manager()
    lock = manager.Lock()

    # Determine number of processes
    if args.workers > 0:
        num_processes = args.workers
    else:
        # Use more workers by default
        num_processes = min(multiprocessing.cpu_count() * 2, len(locations))
    
    print(f"Using {num_processes} worker processes to search for targeted products")
    
    # Create a pool of workers
    with multiprocessing.Pool(processes=num_processes) as pool:
        # Create tasks with location and worker_id
        tasks = []
        for i, location in enumerate(locations):
            tasks.append(((location, i+1), urls, output_file, lock, headless))
        
        # Execute tasks in parallel
        pool.starmap(process_location, tasks)

if __name__ == "__main__":
    main()