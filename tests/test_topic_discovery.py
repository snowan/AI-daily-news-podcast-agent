import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio # Required for testing async functions

# Assuming src.topic_discovery is discoverable (e.g. PYTHONPATH is set or using a project structure)
# If not, you might need to adjust sys.path:
# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from src.topic_discovery import (
    filter_articles_by_keywords,
    extract_articles_theverge_bs,
    extract_articles_technologyreview_bs,
    extract_articles_axios_bs,
    extract_articles_venturebeat_bs,
    extract_articles_techcrunch_playwright, # For testing its processing logic
    NEWS_SOURCES, # To iterate and check all extractors are tested
    main # For the optional main test
)

# Sample HTML snippets for mocking (simplified for brevity)
# In a real scenario, these would be more representative of the actual site structure.

MOCK_HTML_THEVERGE = """
<div id="content">
    <div class="c-entry-box--compact">
        <h2><a href="/theverge-ai-story1">The Verge AI Story 1</a></h2>
    </div>
    <div class="duet--content-cards--content-card">
        <h3><a href="https://www.theverge.com/theverge-ai-story2">The Verge AI Story 2 External</a></h3>
    </div>
</div>
"""

MOCK_HTML_TECHREVIEW = """
<div>
    <article>
        <h3 class="title"><a href="/review-ai-story1">Tech Review AI Story 1</a></h3>
    </article>
    <div class="card">
        <p class="title"><a href="https://www.technologyreview.com/review-ai-story2">Review AI Story 2 External</a></p>
    </div>
</div>
"""

MOCK_HTML_AXIOS = """
<div>
    <div data-cy="story-card">
        <a href="/axios-ai-story1">
            <h3 class="title">Axios AI Story 1</h3>
        </a>
    </div>
    <article>
        <a href="https://www.axios.com/axios-ai-story2-external">
            <div>Axios AI Story 2 External</div>
        </a>
    </article>
</div>
"""

MOCK_HTML_VENTUREBEAT = """
<div>
    <article class="Article">
        <h2 class="Article__title"><a href="https://venturebeat.com/vb-ai-story1/">VB AI Story 1</a></h2>
    </article>
    <li class="wp-block-post">
        <a class="wp-block-post-title" href="/vb-ai-story2-relative">VB AI Story 2 Relative</a>
    </li>
</div>
"""

# For TechCrunch, we test the logic *after* Playwright has done its job.
# So we mock what the Playwright part of extract_articles_techcrunch_playwright would return.
# This is a list of mock "link_locator" objects.
class MockLinkLocator:
    def __init__(self, href, inner_text):
        self._href = href
        self._inner_text = inner_text

    async def get_attribute(self, name):
        if name == 'href':
            return self._href
        return None

    async def inner_text(self):
        return self._inner_text

MOCK_TECHCRUNCH_LOCATORS = [
    MockLinkLocator("https://techcrunch.com/2023/10/26/tc-story-1/", "TechCrunch AI Story 1 about something cool"),
    MockLinkLocator("https://techcrunch.com/2023/10/27/another-ai-breakthrough/", "Another AI Breakthrough at TechCrunch"),
    MockLinkLocator("https://techcrunch.com/events/some-event/", "Non-article link"), # Should be filtered out by regex/headline length
    MockLinkLocator("https://techcrunch.com/2023/10/28/short", "Short"), # Should be filtered out by headline length
]


class TestTopicDiscovery(unittest.TestCase):

    def test_filter_articles_by_keywords(self):
        articles = [
            {'headline': 'New AI model released', 'url': 'http://example.com/ai1'},
            {'headline': 'Tech company launches new GPU', 'url': 'http://example.com/gpu1'},
            {'headline': 'The future of machine learning', 'url': 'http://example.com/ml1'},
            {'headline': 'Space exploration news', 'url': 'http://example.com/space1'}
        ]
        keywords = ["AI", "Machine Learning", "GPU"]
        filtered = filter_articles_by_keywords(articles, keywords)
        self.assertEqual(len(filtered), 3)
        self.assertTrue(any(a['headline'] == 'New AI model released' for a in filtered))
        self.assertTrue(any(a['headline'] == 'Tech company launches new GPU' for a in filtered))
        self.assertTrue(any(a['headline'] == 'The future of machine learning' for a in filtered))
        self.assertFalse(any(a['headline'] == 'Space exploration news' for a in filtered))

    def test_extract_articles_theverge_bs(self):
        articles = extract_articles_theverge_bs(MOCK_HTML_THEVERGE, base_url="https://www.theverge.com")
        self.assertGreater(len(articles), 0, "Should extract at least one article from The Verge mock")
        for article in articles:
            self.assertIn('headline', article)
            self.assertIn('url', article)
            self.assertTrue(article['url'].startswith('http'))
            self.assertIn('The Verge', article['source'])
        self.assertTrue(any('The Verge AI Story 1' in a['headline'] for a in articles))

    def test_extract_articles_technologyreview_bs(self):
        articles = extract_articles_technologyreview_bs(MOCK_HTML_TECHREVIEW, base_url="https://www.technologyreview.com")
        self.assertGreater(len(articles), 0, "Should extract at least one article from MIT Tech Review mock")
        for article in articles:
            self.assertIn('headline', article)
            self.assertIn('url', article)
            self.assertTrue(article['url'].startswith('http'))
            self.assertIn('MIT Technology Review', article['source'])
        self.assertTrue(any('Tech Review AI Story 1' in a['headline'] for a in articles))

    def test_extract_articles_axios_bs(self):
        articles = extract_articles_axios_bs(MOCK_HTML_AXIOS, base_url="https://www.axios.com")
        self.assertGreater(len(articles), 0, "Should extract at least one article from Axios mock")
        for article in articles:
            self.assertIn('headline', article)
            self.assertIn('url', article)
            self.assertTrue(article['url'].startswith('https://www.axios.com')) # Axios URLs are absolute in mock
            self.assertIn('Axios AI', article['source'])
        self.assertTrue(any('Axios AI Story 1' in a['headline'] for a in articles))

    def test_extract_articles_venturebeat_bs(self):
        articles = extract_articles_venturebeat_bs(MOCK_HTML_VENTUREBEAT, base_url="https://venturebeat.com")
        self.assertGreater(len(articles), 0, "Should extract at least one article from VentureBeat mock")
        for article in articles:
            self.assertIn('headline', article)
            self.assertIn('url', article)
            self.assertTrue(article['url'].startswith('http'))
            self.assertIn('VentureBeat AI', article['source'])
        self.assertTrue(any('VB AI Story 1' in a['headline'] for a in articles))
        self.assertTrue(any(a['url'] == 'https://venturebeat.com/vb-ai-story2-relative' for a in articles))

    @patch('src.topic_discovery.async_playwright') # We don't want actual Playwright to run
    def test_extract_articles_techcrunch_playwright_logic(self, mock_async_playwright):
        # This test focuses on the logic *within* extract_articles_techcrunch_playwright
        # that processes the locators, not on the Playwright setup itself.

        # Mock the page and its methods that the extractor uses
        mock_page = MagicMock()
        mock_page.locator.return_value.all.return_value = MOCK_TECHCRUNCH_LOCATORS
        mock_page.is_closed.return_value = False

        mock_browser = AsyncMock() # Make it awaitable if close is called
        mock_context = AsyncMock()
        mock_pw_instance = AsyncMock() # Make it awaitable if stop is called

        # The resource_tuple is (page, browser, context, pw_instance)
        resource_tuple = (mock_page, mock_browser, mock_context, mock_pw_instance)
        
        # Run the async function
        articles = asyncio.run(extract_articles_techcrunch_playwright(resource_tuple, base_url="https://techcrunch.com"))
        
        self.assertEqual(len(articles), 2, "Should extract two valid articles from TechCrunch mock locators")
        for article in articles:
            self.assertIn('headline', article)
            self.assertIn('url', article)
            self.assertTrue(article['url'].startswith('https://techcrunch.com/2023/'))
            self.assertIn('TechCrunch', article['source'])
            self.assertNotIn('Non-article link', article['headline'])
            self.assertNotIn('Short', article['headline'])
        
        self.assertTrue(any('TechCrunch AI Story 1' in a['headline'] for a in articles))
        self.assertTrue(any('Another AI Breakthrough' in a['headline'] for a in articles))

        # Assert that browser and playwright instance were closed
        mock_browser.close.assert_called_once()
        mock_pw_instance.stop.assert_called_once()


    def test_all_news_sources_have_extractors_and_tests(self):
        # This is a meta-test to ensure we don't forget to test new extractors
        tested_extractors = [
            'extract_articles_theverge_bs',
            'extract_articles_technologyreview_bs',
            'extract_articles_axios_bs',
            'extract_articles_venturebeat_bs',
            'extract_articles_techcrunch_playwright' # Playwright version
        ]
        for source_info in NEWS_SOURCES:
            self.assertIn(source_info['extractor'], tested_extractors,
                          f"Extractor {source_info['extractor']} for {source_info['source_name']} is not in the list of tested extractors.")

    @patch('src.topic_discovery.async_fetch_resources_for_source', new_callable=AsyncMock)
    async def run_main_test(self, mock_fetch_resources):
        # Configure mock_fetch_resources to return appropriate mock HTML or tuples
        # This requires knowing the order of NEWS_SOURCES or making it more robust
        
        def side_effect_fetch(url, source_name):
            if source_name == "TechCrunch":
                # Mock the Playwright tuple: (page, browser, context, pw_instance)
                mock_page = MagicMock()
                mock_page.locator.return_value.all.return_value = MOCK_TECHCRUNCH_LOCATORS
                mock_page.is_closed.return_value = False
                # Make browser and pw_instance awaitable for close/stop
                return (mock_page, AsyncMock(), AsyncMock(), AsyncMock()) 
            elif source_name == "The Verge":
                return MOCK_HTML_THEVERGE
            elif source_name == "MIT Technology Review":
                return MOCK_HTML_TECHREVIEW
            elif source_name == "Axios AI":
                return MOCK_HTML_AXIOS
            elif source_name == "VentureBeat AI":
                return MOCK_HTML_VENTUREBEAT
            return None # Default for any other source not mocked

        mock_fetch_resources.side_effect = side_effect_fetch
        
        filtered_articles = await main() # Call the async main function

        self.assertIsInstance(filtered_articles, list)
        # Check if articles from all mocked sources are present (or at least some)
        # This depends on keywords and mock data, so be general
        self.assertGreater(len(filtered_articles), 0, "Main function should return some filtered articles with mock data")

        # Verify that fetch was called for each source
        self.assertEqual(mock_fetch_resources.call_count, len(NEWS_SOURCES))

        # Example check for one source's articles (assuming keywords match)
        # This is tricky because filtering happens *after* all extraction
        # For a more robust test, you might need to inspect the inputs to filter_articles_by_keywords
        # or construct mock data that guarantees matches with AI_KEYWORDS.
        
        # For now, just check that some articles were returned.
        # A more detailed check would involve ensuring specific mock articles pass the filter.
        # For example, if "AI" is a keyword, and a mock headline contains "AI".
        found_sources = set(article['source'] for article in filtered_articles)
        # Depending on keywords and mock data, not all sources might yield results.
        # This test is more about the flow.
        self.assertTrue(len(found_sources) > 0, "Filtered articles should come from at least one mocked source")


    def test_main_function_integration(self):
        # Run the async test method for main
        asyncio.run(self.run_main_test())


if __name__ == '__main__':
    # If you need to adjust sys.path for imports from src/, do it here or ensure PYTHONPATH is set.
    # Example:
    # import sys
    # import os
    # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
    unittest.main()
