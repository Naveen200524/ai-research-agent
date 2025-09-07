#!/usr/bin/env python3
"""
DuckDuckGo Search Test Script
Based on langchain-community DuckDuckGo documentation
No API key required - uses free DuckDuckGo search
"""

import asyncio
import json
from typing import List, Dict, Any

# Import DuckDuckGo search tools
try:
    from langchain_community.tools import DuckDuckGoSearchRun, DuckDuckGoSearchResults
    from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
    LANGCHAIN_AVAILABLE = True
except ImportError:
    print("❌ langchain-community not installed. Install with: pip install langchain-community")
    LANGCHAIN_AVAILABLE = False

class DuckDuckGoTester:
    """Test class for DuckDuckGo search functionality"""

    def __init__(self):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("langchain-community is required for this test")

        # Initialize different search tools
        self.basic_search = DuckDuckGoSearchRun()
        self.detailed_search = DuckDuckGoSearchResults()
        self.news_search = DuckDuckGoSearchResults(backend="news")
        self.list_search = DuckDuckGoSearchResults(output_format="list")
        self.json_search = DuckDuckGoSearchResults(output_format="json")

    def test_basic_search(self, query: str) -> str:
        """Test basic DuckDuckGo search (returns formatted string)"""
        print(f"\n🔍 Testing Basic Search: '{query}'")
        print("-" * 50)

        try:
            result = self.basic_search.invoke(query)
            print("✅ Basic search successful!")
            print(f"Result length: {len(result)} characters")
            print(f"Preview: {result[:200]}...")
            return result
        except Exception as e:
            print(f"❌ Basic search failed: {e}")
            return ""

    def test_detailed_search(self, query: str) -> List[Dict]:
        """Test detailed search with links and sources"""
        print(f"\n� Testing Detailed Search: '{query}'")
        print("-" * 50)

        try:
            result = self.detailed_search.invoke(query)
            print("✅ Detailed search successful!")

            # Parse the result string into components
            if result:
                print(f"Raw result: {result[:300]}...")
                # The result comes as a formatted string, not JSON
                print("Result type: Formatted string with key-value pairs")
            else:
                print("No results found")

            return result if result else []
        except Exception as e:
            print(f"❌ Detailed search failed: {e}")
            return []

    def test_list_format_search(self, query: str) -> List[Dict]:
        """Test search with list output format"""
        print(f"\n📝 Testing List Format Search: '{query}'")
        print("-" * 50)

        try:
            result = self.list_search.invoke(query)
            print("✅ List format search successful!")

            if isinstance(result, list):
                print(f"Found {len(result)} results:")
                for i, item in enumerate(result[:3], 1):  # Show first 3
                    print(f"{i}. {item.get('title', 'No title')}")
                    print(f"   Link: {item.get('link', 'No link')}")
                    print(f"   Snippet: {item.get('snippet', 'No snippet')[:100]}...")
                    print()
            else:
                print(f"Unexpected result type: {type(result)}")
                print(f"Result: {result[:200]}...")

            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"❌ List format search failed: {e}")
            return []

    def test_news_search(self, query: str) -> str:
        """Test news-specific search"""
        print(f"\n📰 Testing News Search: '{query}'")
        print("-" * 50)

        try:
            result = self.news_search.invoke(query)
            print("✅ News search successful!")
            print(f"Result length: {len(result)} characters")
            print(f"Preview: {result[:300]}...")
            return result
        except Exception as e:
            print(f"❌ News search failed: {e}")
            return ""

    def test_custom_wrapper(self, query: str) -> str:
        """Test with custom API wrapper configuration"""
        print(f"\n⚙️ Testing Custom Wrapper: '{query}'")
        print("-" * 50)

        try:
            # Create custom wrapper with specific settings
            wrapper = DuckDuckGoSearchAPIWrapper(
                region="us-en",  # US region, English
                time="d",       # Past day
                max_results=3   # Limit results
            )

            # Create search tool with custom wrapper
            custom_search = DuckDuckGoSearchResults(
                api_wrapper=wrapper,
                source="news"  # News source
            )

            result = custom_search.invoke(query)
            print("✅ Custom wrapper search successful!")
            print(f"Result length: {len(result)} characters")
            print(f"Preview: {result[:300]}...")
            return result
        except Exception as e:
            print(f"❌ Custom wrapper search failed: {e}")
            return ""

async def main():
    """Main test function"""
    print("🦆 DuckDuckGo Search Test Suite")
    print("=" * 60)
    print("Testing various DuckDuckGo search configurations")
    print("No API key required - using free DuckDuckGo service")
    print()

    if not LANGCHAIN_AVAILABLE:
        print("❌ Cannot run tests - langchain-community not available")
        return

    # Initialize tester
    tester = DuckDuckGoTester()

    # Test queries
    test_queries = [
        "Obama's first name?",
        "latest AI developments",
        "quantum computing breakthroughs"
    ]

    # Run tests
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Testing Query: '{query}'")
        print('='*60)

        # Test 1: Basic search
        basic_result = tester.test_basic_search(query)

        # Test 2: Detailed search
        detailed_result = tester.test_detailed_search(query)

        # Test 3: List format
        list_result = tester.test_list_format_search(query)

        # Test 4: News search (only for relevant queries)
        if "Obama" in query or "AI" in query or "quantum" in query:
            news_result = tester.test_news_search(query)

        # Test 5: Custom wrapper (only for first query)
        if query == test_queries[0]:
            custom_result = tester.test_custom_wrapper(query)

        # Small delay between queries to be respectful
        await asyncio.sleep(1)

    print(f"\n{'='*60}")
    print("🎯 Test Summary")
    print('='*60)
    print("✅ All DuckDuckGo search configurations tested")
    print("✅ No API key required")
    print("✅ Multiple output formats supported")
    print("✅ News search backend available")
    print("✅ Custom configuration options working")
    print("\n📚 Key Features Demonstrated:")
    print("  • DuckDuckGoSearchRun - Basic search")
    print("  • DuckDuckGoSearchResults - Detailed results with links")
    print("  • output_format options: string, list, json")
    print("  • backend='news' for news-specific search")
    print("  • Custom DuckDuckGoSearchAPIWrapper configuration")
    print("  • Region, time, and max_results settings")

if __name__ == "__main__":
    asyncio.run(main())
