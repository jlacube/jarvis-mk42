import pytest
import os

from tools.research_tools import google_search_tool, advanced_research_tool

@pytest.mark.asyncio
async def test_google_search_tool():
    """Test that google_search_tool returns expected search results."""
    # Skip if API key is not available
    if not os.environ.get("SERPER_API_KEY"):
        pytest.skip("SERPER_API_KEY environment variable not set")
    
    query = "Python programming language"
    results = await google_search_tool.ainvoke(query)
    
    # Check if results is a dictionary
    assert isinstance(results, dict), "Results should be a dictionary"
    
    # Check if the results contain expected keys
    assert "organic" in results, "Results should contain 'organic' key"
    
    # Check if organic results is a list with items
    assert isinstance(results["organic"], list), "Organic results should be a list"
    assert len(results["organic"]) > 0, "Organic results should not be empty"
    
    # Check if results contain Python-related content
    combined_text = ' '.join([str(item.get('title', '')) + ' ' + str(item.get('snippet', '')) 
                            for item in results["organic"]])
    assert "python" in combined_text.lower(), "Results should contain Python-related content"

@pytest.mark.asyncio
async def test_advanced_research_tool():
    """Test that advanced_research_tool returns meaningful research results."""
    # Skip if API key is not available
    if not os.environ.get("PERPLEXITY_API_KEY"):
        pytest.skip("PERPLEXITY_API_KEY environment variable not set")
    
    query = "What are the main features of Python?"
    result = await advanced_research_tool.ainvoke(query)
    
    # Check if result is a string
    assert isinstance(result, str), "Result should be a string"
    
    # Check if the result is not empty
    assert len(result) > 0, "Result should not be empty"
    
    # Check if result contains Python-related terms
    expected_terms = ["python", "language", "features"]
    assert any(term in result.lower() for term in expected_terms), f"Result should contain Python-related terms: {expected_terms}"
    
    # Check if result is reasonably long (indicative of a thorough response)
    assert len(result) > 100, "Result should be a reasonably long response"
