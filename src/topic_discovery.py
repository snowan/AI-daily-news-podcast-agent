import asyncio
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import time
import re # For regular expressions if needed for URL patterns

# Define the list of AI news source URLs and their specific extractor functions
NEWS_SOURCES = [
    {"url": "https://techcrunch.com/category/artificial-intelligence/", "extractor": "extract_articles_techcrunch_playwright", "source_name": "TechCrunch"},
    {"url": "https://www.theverge.com/ai-artificial-intelligence", "extractor": "extract_articles_theverge_bs", "source_name": "The Verge"},
    {"url": "https://www.technologyreview.com/artificial-intelligence", "extractor": "extract_articles_technologyreview_bs", "source_name": "MIT Technology Review"},
    {"url": "https://www.axios.com/sections/artificial-intelligence", "extractor": "extract_articles_axios_bs", "source_name": "Axios AI"},
    {"url": "https://venturebeat.com/category/ai/", "extractor": "extract_articles_venturebeat_bs", "source_name": "VentureBeat AI"},
]

# Define AI-related keywords for filtering
AI_KEYWORDS = [
    "AI", "Artificial Intelligence", "Machine Learning", "Language Model", "AGI", "ASI", "Superintelligence",
    "GPT", "LLM", "OpenAI", "DeepMind", "Anthropic", "Claude", "Gemini", "Sora", "Llama", "Mistral", "Reka",
    "neural network", "robotics", "computer vision", "NLP", "natural language processing",
    "generative AI", "GenAI", "AI model", "AI ethics", "AI regulation", "AI safety", "Responsible AI",
    "multimodal AI", "AI agent", "foundation model", "AI chip", "TPU", "GPU"
]


async def async_fetch_resources_for_source(url: str, source_name: str) -> Page | Browser | BrowserContext | str | None:
    """
    Fetches resources for a given URL using Playwright.
    For TechCrunch, it returns a tuple (page, browser, context, pw_instance) for direct DOM interaction.
    For other sources, it returns the HTML content string.
    """
    print(f"Attempting to fetch with Playwright: {url}")
    browser = None 
    context = None 
    page = None    
    pw_instance = None

    try:
        pw_instance = await async_playwright().start()
        browser = await pw_instance.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            java_script_enabled=True,
            accept_downloads=False,
            ignore_https_errors=True,
            # viewport={'width': 1920, 'height': 1080} # Setting a common viewport
        )
        page = await context.new_page()
        
        await page.goto(url, timeout=90000, wait_until='domcontentloaded')
        
        cookie_selectors = [
            'button:has-text("Accept")', 'button:has-text("Agree")', 'button:has-text("Consent")',
            'button:has-text("OK")', 'button:has-text("Allow all")', 'button[id*="cookie"]',
            'div[id*="cookieBanner"] button', '#onetrust-accept-btn-handler',
            '#cookieBanner-44101848 button' 
        ]
        
        print(f"Attempting to dismiss cookie banner for {url}...")
        for selector in cookie_selectors:
            try:
                button_locator = page.locator(selector).first
                if await button_locator.is_visible(timeout=1000):
                    await button_locator.click(timeout=2000)
                    print(f"Clicked cookie button with selector: {selector}")
                    await page.wait_for_timeout(1500) 
                    break 
            except PlaywrightTimeoutError: pass 
            except Exception as e_cookie: print(f"Error clicking cookie selector ('{selector}'): {e_cookie}")

        # General wait for dynamic content, removed specific wait for 'div.river' for TechCrunch
        print(f"{source_name}: Waiting for general page stabilization (12 seconds).")
        await page.wait_for_timeout(12000)
        
        if source_name == "TechCrunch":
            print(f"TechCrunch: Page, browser, context, pw_instance objects will be used for extraction.")
            return page, browser, context, pw_instance 
        else:
            html_content = await page.content()
            print(f"Successfully fetched HTML content from: {url} (Length: {len(html_content)})")
            await browser.close() 
            await pw_instance.stop()
            return html_content

    except PlaywrightTimeoutError as e:
        print(f"Playwright timeout error fetching URL {url}: {e.message}")
        if browser and browser.is_connected(): await browser.close()
        if pw_instance: await pw_instance.stop()
        return None
    except Exception as e:
        print(f"Playwright error fetching URL {url}: {type(e).__name__} - {e}")
        if browser and browser.is_connected(): await browser.close()
        if pw_instance: await pw_instance.stop()
        return None

async def extract_articles_techcrunch_playwright(resource_tuple: tuple, base_url="https://techcrunch.com") -> list:
    page, browser, context, pw_instance = resource_tuple
    articles = []
    print("TechCrunch (Playwright Extractor): Using broad Playwright locators for article links.")
    try:
        if page.is_closed():
            print("TechCrunch (Playwright Extractor): Page was already closed.")
            return articles

        # Broad heuristic: Find all <a> tags whose href matches common TechCrunch article URL pattern
        # e.g., https://techcrunch.com/YYYY/MM/DD/slug/
        # This is a very general approach.
        # The .all() method is not async, it returns a list of locators.
        link_locators = page.locator(f'a[href^="{base_url}/20"]').all() 
        
        print(f"TechCrunch (Playwright Extractor): Found {len(link_locators)} potential article links matching pattern '{base_url}/20'.")

        for link_locator in link_locators: # Iterate directly over the list of locators
            url = await link_locator.get_attribute('href') # get_attribute is async
            headline = await link_locator.inner_text() # inner_text is async
            headline = headline.strip() if headline else ""
            
            # Further filter by URL structure and headline content
            if url and re.match(rf"^{base_url}/\d{{4}}/\d{{2}}/\d{{2}}/[^/]+/?$", url) and len(headline) > 25: # Min headline length
                articles.append({'headline': headline, 'url': url, 'source': f'TechCrunch'})
            # else:
                # if url and re.match(rf"^{base_url}/\d{{4}}/\d{{2}}/\d{{2}}/[^/]+/?$", url):
                #     print(f"TC - Skipped (short headline): {headline} | URL: {url}")
                # elif len(headline) > 25:
                #      print(f"TC - Skipped (URL pattern mismatch): {headline} | URL: {url}")


    except Exception as e:
        print(f"Error during Playwright extraction for TechCrunch: {type(e).__name__} - {e}")
    finally:
        print("TechCrunch (Playwright Extractor): Closing browser.")
        if browser and browser.is_connected(): await browser.close()
        if pw_instance: await pw_instance.stop()

    if not articles: print("TechCrunch (Playwright Extractor): No articles found with broad heuristic.")
    return list({article['url']: article for article in articles}.values())


def extract_articles_theverge_bs(html_content: str, base_url="https://www.theverge.com") -> list:
    articles = []
    if not html_content: return articles
    soup = BeautifulSoup(html_content, 'html.parser')
    content_area = soup.find('div', id='content') or soup
    for entry_box in content_area.select('div.c-entry-box--compact, div.duet--content-cards--content-card, div.max-w-content-block-standard, li.duet--content-cards--content-card'):
        link_tag = None; headline = None; url = None
        possible_link = entry_box.select_one('h2 a[href], h3 a[href], a[data-analytics-link="article"]')
        if possible_link:
            link_tag = possible_link; url = link_tag.get('href')
            headline_container = entry_box.select_one('h2, h3')
            headline = headline_container.get_text(strip=True) if headline_container else link_tag.get_text(strip=True)
        if headline and url and len(headline) > 10:
            if not url.startswith('http'): url = (base_url + url) if url.startswith('/') else (base_url + '/' + url)
            articles.append({'headline': headline, 'url': url, 'source': 'The Verge'})
    if not articles: print("The Verge: No articles found with primary selectors.")
    return list({article['url']: article for article in articles}.values())

def extract_articles_technologyreview_bs(html_content: str, base_url="https://www.technologyreview.com") -> list:
    articles = []; 
    if not html_content: return articles
    soup = BeautifulSoup(html_content, 'html.parser')
    for article_el in soup.select('article, div[class*="teaser"], div[class*="card"], li[class*="item"]'):
        link_tag = None; headline = None; url = None
        headline_el = article_el.select_one('h2[class*="title"], h3[class*="title"], p[class*="title"], span[class*="title"], a[aria-label]')
        if headline_el:
            headline = headline_el.get_text(strip=True)
            if headline_el.name == 'a' and headline_el.has_attr('href'): link_tag = headline_el
            elif headline_el.find('a', href=True): link_tag = headline_el.find('a', href=True)
            elif headline_el.parent.name == 'a' and headline_el.parent.has_attr('href'): link_tag = headline_el.parent
            if not link_tag and headline_el.name == 'a' and headline_el.has_attr('aria-label') and headline_el.has_attr('href'):
                 headline = headline_el.get('aria-label', headline); link_tag = headline_el
        if not link_tag: 
            link_tag = article_el.find('a', href=True)
            if link_tag and (not headline or len(headline) < 15): headline = link_tag.get_text(strip=True) 
        if link_tag and headline and (len(headline) < 15 or "read more" in headline.lower()):
            aria_label = link_tag.get('aria-label'); title_attr = link_tag.get('title')
            if aria_label and len(aria_label) > 15: headline = aria_label
            elif title_attr and len(title_attr) > 15: headline = title_attr
        if link_tag: url = link_tag.get('href')
        if headline and url and len(headline) > 15: 
            if not url.startswith('http'): url = (base_url + url) if url.startswith("/") else (base_url + "/" + url.lstrip('/'))
            articles.append({'headline': headline, 'url': url, 'source': 'MIT Technology Review'})
    if not articles: print("MIT Tech Review: No articles found with primary selectors.")
    return list({article['url']: article for article in articles}.values())


def extract_articles_axios_bs(html_content: str, base_url="https://www.axios.com") -> list:
    articles = []
    if not html_content: return articles
    soup = BeautifulSoup(html_content, 'html.parser')
    # Axios has a relatively clean structure, articles are often within <article> tags or specific divs
    # Look for elements with data-cy="story-card" or similar attributes
    for item in soup.select('article, div[data-cy="story-card"], div[class*="story-card"]'):
        headline = None
        url = None
        link_tag = item.select_one('a[href]')
        
        if link_tag:
            url = link_tag.get('href')
            if not url.startswith('http'):
                url = base_url + url if url.startswith('/') else base_url + '/' + url
            
            # Try to find headline within the link or a prominent heading tag
            headline_el = item.select_one('h3, h2, div[class*="title"]')
            if headline_el:
                headline = headline_el.get_text(strip=True)
            elif link_tag.get_text(strip=True): # Fallback to link text
                headline = link_tag.get_text(strip=True)
            elif link_tag.has_attr('title'): # Fallback to link title attribute
                headline = link_tag['title']

        if headline and url and len(headline) > 10: # Basic validation
            articles.append({'headline': headline, 'url': url, 'source': 'Axios AI'})
        # else:
            # if not headline: print(f"Axios: Skipping item, no headline found. URL: {url}")
            # if not url: print(f"Axios: Skipping item, no URL found. Headline: {headline}")
            # if headline and len(headline) <=10: print(f"Axios: Skipping item, headline too short. Headline: {headline}")

    if not articles: print("Axios AI: No articles found with primary selectors.")
    return list({article['url']: article for article in articles}.values())


def extract_articles_venturebeat_bs(html_content: str, base_url="https://venturebeat.com") -> list:
    articles = []
    if not html_content: return articles
    soup = BeautifulSoup(html_content, 'html.parser')
    # VentureBeat articles are typically in <article> elements or list items
    for item in soup.select('article.Article, div.ArticleListing, li.wp-block-post'):
        headline = None
        url = None
        
        link_tag = item.select_one('a[href]')
        headline_el = item.select_one('h2.Article__title, h3.Article__title, a.Article__title, .wp-block-post-title a')

        if headline_el:
            headline = headline_el.get_text(strip=True)
            if headline_el.name == 'a' and headline_el.has_attr('href'):
                url = headline_el.get('href')
            elif link_tag and not url: # if headline_el was not 'a' but we found a link_tag earlier
                 url = link_tag.get('href')

        if not url and link_tag: # If headline was found but URL is still missing, use the general link_tag
            url = link_tag.get('href')
            if not headline and link_tag.get_text(strip=True): # If headline is still missing, use link text
                headline = link_tag.get_text(strip=True)
        
        if headline and url and len(headline) > 10:
            # VentureBeat URLs are usually absolute
            if not url.startswith('http'):
                 url = base_url + url if url.startswith('/') else base_url + '/' + url
            articles.append({'headline': headline, 'url': url, 'source': 'VentureBeat AI'})
        # else:
            # if not headline: print(f"VB: Skipping item, no headline. URL: {url}")
            # if not url: print(f"VB: Skipping item, no URL. Headline: {headline}")
            # if headline and len(headline) <=10: print(f"VB: Skipping item, headline too short. Headline: {headline}")


    if not articles: print("VentureBeat AI: No articles found with primary selectors.")
    return list({article['url']: article for article in articles}.values())


def filter_articles_by_keywords(articles: list, keywords: list) -> list:
    filtered_articles = []
    for article in articles:
        headline_lower = article['headline'].lower()
        if any(keyword.lower() in headline_lower for keyword in keywords):
            filtered_articles.append(article)
    return filtered_articles

async def main():
    all_extracted_articles = []
    print("Starting AI News Discovery Process with Playwright...")
    print(f"AI Keywords for filtering: {', '.join(AI_KEYWORDS)}\n")

    for source_info in NEWS_SOURCES:
        source_url = source_info["url"]
        extractor_func_name = source_info["extractor"]
        source_name = source_info["source_name"]
        extractor_func = globals().get(extractor_func_name)

        if not extractor_func:
            print(f"Warning: Extractor function '{extractor_func_name}' not found for {source_url}. Skipping.")
            continue

        print(f"Fetching and parsing articles from: {source_name} ({source_url})")
        
        resource_or_tuple = await async_fetch_resources_for_source(source_url, source_name)

        if resource_or_tuple:
            extracted_articles = []
            parsed_source_url_match = re.match(r"^(https?://[^/]+)", source_url)
            base_url = parsed_source_url_match.group(1) if parsed_source_url_match else source_url

            if source_name == "TechCrunch" and isinstance(resource_or_tuple, tuple) and len(resource_or_tuple) == 4: 
                extracted_articles = await extractor_func(resource_or_tuple, base_url=base_url)
            elif isinstance(resource_or_tuple, str): 
                extracted_articles = extractor_func(resource_or_tuple, base_url=base_url)
            elif source_name == "TechCrunch" and resource_or_tuple is None:
                 print(f"Fetching resources for TechCrunch failed, extractor will be skipped.")
            else:
                print(f"Unexpected resource type or structure for {source_name}: {type(resource_or_tuple)}")
                if source_name == "TechCrunch" and isinstance(resource_or_tuple, tuple): 
                     _, browser, _, pw_instance = resource_or_tuple 
                     if browser and browser.is_connected(): await browser.close()
                     if pw_instance: await pw_instance.stop()
            
            if extracted_articles: 
                print(f"Found {len(extracted_articles)} potential articles from {source_name}.")
                all_extracted_articles.extend(extracted_articles)
            else: 
                print(f"No articles extracted by '{extractor_func_name}' for {source_name} (after calling extractor).")
        else:
            print(f"Could not fetch resources for {source_name} using Playwright (returned None).")
        print("-" * 30)
        await asyncio.sleep(0.5)

    if not all_extracted_articles:
        print("\nNo articles were extracted from any source.")
        return [] # Return empty list

    print(f"\nTotal potential articles extracted (before keyword filtering): {len(all_extracted_articles)}")
    filtered_ai_articles = filter_articles_by_keywords(all_extracted_articles, AI_KEYWORDS)
    
    if filtered_ai_articles:
        print(f"\n=== Found {len(filtered_ai_articles)} AI-Related News Articles (after keyword filtering) ===")
        filtered_ai_articles.sort(key=lambda x: x['source']) # Sort for consistent output
        for article in filtered_ai_articles:
            print(f"Headline: {article['headline']}")
            print(f"URL: {article['url']}")
            print(f"Source: {article['source']}")
            print("---")
    else:
        print("\nNo AI-related articles found matching keywords from the extracted content.")
    
    return filtered_ai_articles

if __name__ == "__main__":
    # To run the main function and see output:
    # articles = asyncio.run(main())
    # if articles:
    #     print(f"\nMain function returned {len(articles)} filtered articles.")
    # else:
    #     print("\nMain function returned no articles.")
    pass # Keep the main execution block clean for module usage
