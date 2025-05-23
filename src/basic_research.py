import asyncio
import argparse
import os
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from googlesearch import search as google_search # From googlesearch-python

# --- Configuration ---
NUM_SEARCH_RESULTS = 3 # Number of top Google search results to process
LLM_PLACEHOLDER_SUMMARY = "LLM summary would be here. The full text processed would have been logged before this placeholder."
OUTPUT_FILE_PATH = "data/research_brief.txt"

# --- Playwright Content Fetching ---
async def fetch_page_content_with_playwright(url: str) -> str | None:
    """
    Fetches HTML content from a URL using Playwright.
    Includes a generic attempt to dismiss cookie banners.
    """
    print(f"Fetching: {url}")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                java_script_enabled=True,
                accept_downloads=False,
                ignore_https_errors=True
            )
            page = await context.new_page()
            await page.goto(url, timeout=60000, wait_until='domcontentloaded') # 60s timeout

            cookie_selectors = [
                'button:has-text("Accept")', 'button:has-text("Agree")', 'button:has-text("Consent")',
                'button:has-text("OK")', 'button:has-text("Allow all")', 'button[id*="cookie"]',
                'div[id*="cookieBanner"] button', '#onetrust-accept-btn-handler'
            ]
            print(f"  Attempting to dismiss cookie banner for {url}...")
            for selector in cookie_selectors:
                try:
                    button = page.locator(selector).first
                    if await button.is_visible(timeout=1000):
                        await button.click(timeout=2000)
                        print(f"    Clicked cookie button with selector: {selector}")
                        await page.wait_for_timeout(1500)
                        break
                except PlaywrightTimeoutError: pass
                except Exception as e_cookie: print(f"    Error clicking cookie selector ('{selector}'): {e_cookie}")
            
            await page.wait_for_timeout(5000) # Wait 5s for dynamic content to settle
            content = await page.content()
            await browser.close()
            print(f"  Successfully fetched content from: {url} (Length: {len(content)})")
            return content
    except PlaywrightTimeoutError:
        print(f"  Playwright timeout error fetching URL {url}")
        return None
    except Exception as e:
        print(f"  Playwright error fetching URL {url}: {type(e).__name__} - {e}")
        return None

# --- BeautifulSoup Text Extraction ---
def extract_text_from_html(html_content: str) -> str:
    """
    Extracts main textual content from HTML using BeautifulSoup.
    Focuses on common tags like <p>, <article>, <h1>, <h2>, etc.
    """
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    
    # Get text from common content tags
    # Prioritize specific semantic tags if available (e.g., article, main)
    main_content_tags = soup.find_all(['article', 'main', 'div[class*="content"]', 'div[class*="post"]', 'div[class*="body"]'])
    
    text_parts = []
    if main_content_tags:
        for tag in main_content_tags:
            # Extract text from p, h1, h2, h3, h4, li within these main content tags
            content_elements = tag.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li'])
            for element in content_elements:
                text_parts.append(element.get_text(separator=' ', strip=True))
    else:
        # Fallback: Get text from all <p> tags in the document if no specific main content found
        print("  No specific main content tags (article, main, etc.) found. Extracting all <p> tags.")
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text_parts.append(p.get_text(separator=' ', strip=True))

    extracted_text = "\n".join(filter(None, text_parts)) # Join non-empty parts
    print(f"  Extracted ~{len(extracted_text)} characters of text.")
    return extracted_text

# --- LLM Summarization (Placeholder) ---
def summarize_text_with_llm(text_to_summarize: str, topic: str) -> str:
    """
    Placeholder function for LLM summarization.
    Logs the prompt and text, returns a dummy summary.
    """
    prompt = f"""
    Please summarize the following text, focusing on the main points relevant to the topic: "{topic}".
    Provide a concise summary of 2-3 paragraphs.

    Text to summarize:
    ---
    {text_to_summarize[:3000]}... (truncated for logging if very long)
    ---
    """
    print("\n--- LLM Summarization ---")
    print("Topic for summarization:", topic)
    print("Prompt that would be sent to LLM:")
    print(prompt)
    # In a real implementation, here you would make an API call to an LLM:
    # e.g., using OpenAI's API:
    # client = OpenAI(api_key="YOUR_API_KEY")
    # response = client.chat.completions.create(
    #     model="gpt-3.5-turbo", # Or gpt-4, etc.
    #     messages=[
    #         {"role": "system", "content": "You are a helpful assistant that summarizes text."},
    #         {"role": "user", "content": prompt_with_full_text_here} # Send the full text in the actual prompt
    #     ]
    # )
    # summary = response.choices[0].message.content
    # return summary
    
    print(f"Returning placeholder summary: '{LLM_PLACEHOLDER_SUMMARY}'")
    return LLM_PLACEHOLDER_SUMMARY

# --- Main Orchestration ---
async def research_topic(topic: str):
    """
    Orchestrates the research process for a given topic.
    """
    print(f"Starting research for topic: \"{topic}\"")

    # 1. Google Search
    print("\n--- Google Search ---")
    try:
        search_results_urls = list(google_search(topic, num_results=NUM_SEARCH_RESULTS, lang="en"))
        if not search_results_urls:
            print("No search results found from Google.")
            return
        print(f"Found {len(search_results_urls)} URLs from Google search:")
        for i, url in enumerate(search_results_urls):
            print(f"  {i+1}. {url}")
    except Exception as e:
        print(f"Error during Google search: {e}")
        return

    # 2. Fetch and Extract Text from URLs
    print("\n--- Content Fetching and Extraction ---")
    concatenated_text = ""
    for url in search_results_urls:
        html_content = await fetch_page_content_with_playwright(url)
        if html_content:
            extracted_text = extract_text_from_html(html_content)
            concatenated_text += f"\n\n--- Content from {url} ---\n{extracted_text}"
        else:
            print(f"  Could not fetch content from {url}. Skipping.")
        await asyncio.sleep(1) # Small delay between fetches

    if not concatenated_text.strip():
        print("\nNo text could be extracted from any of the URLs. Cannot proceed with summarization.")
        return

    # 3. LLM Summarization
    summary = summarize_text_with_llm(concatenated_text.strip(), topic)

    # 4. Save Summary
    print(f"\n--- Saving Summary to {OUTPUT_FILE_PATH} ---")
    try:
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(OUTPUT_FILE_PATH), exist_ok=True)
        with open(OUTPUT_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(f"Research Brief for Topic: {topic}\n\n")
            f.write(summary)
        print(f"Summary saved successfully to {OUTPUT_FILE_PATH}")
    except IOError as e:
        print(f"Error saving summary to file: {e}")

    print("\nResearch process completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform basic research on a topic and summarize it.")
    parser.add_argument("topic", type=str, help="The topic string to research (e.g., an article headline or keywords).")
    
    args = parser.parse_args()
    
    if not args.topic:
        print("Error: No topic provided. Please provide a topic as a command-line argument.")
    else:
        asyncio.run(research_topic(args.topic))
