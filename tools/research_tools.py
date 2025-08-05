import logging
import re
from typing import Optional
from urllib.parse import urlparse

import requests
from chainlit import make_async, Video
from duckduckgo_search import DDGS
from google import generativeai as genai
from langchain_core.tools import tool, Tool
from langchain_community.utilities import GoogleSerperAPIWrapper
from pydantic import SecretStr, validator
from bs4 import BeautifulSoup

from config.settings import get_settings
from utils.exceptions import JarvisValidationError, JarvisAPIError, JarvisToolError
from utils.logging_config import get_logger

# Initialize logger and settings
logger = get_logger(__name__)
settings = get_settings()

# Security configurations
MAX_QUERY_LENGTH = 500
MAX_RESULTS_LIMIT = 50
ALLOWED_URL_SCHEMES = {'http', 'https'}
BLOCKED_DOMAINS = {'localhost', '127.0.0.1', '0.0.0.0', '10.', '192.168.', '172.'}

def validate_query(query: str) -> str:
    """Validate and sanitize search query"""
    if not query or not query.strip():
        raise JarvisValidationError("Query cannot be empty")
    
    query = query.strip()
    if len(query) > MAX_QUERY_LENGTH:
        raise JarvisValidationError(f"Query too long (max {MAX_QUERY_LENGTH} characters)")
    
    # Basic XSS protection
    if any(tag in query.lower() for tag in ['<script', '<iframe', 'javascript:', 'data:']):
        raise JarvisValidationError("Query contains potentially malicious content")
    
    return query

def validate_max_results(max_results: int) -> int:
    """Validate max_results parameter"""
    if not isinstance(max_results, int):
        raise JarvisValidationError("max_results must be an integer")
    
    if max_results < 1:
        raise JarvisValidationError("max_results must be at least 1")
    
    if max_results > MAX_RESULTS_LIMIT:
        logger.warning(f"max_results {max_results} exceeds limit, capping to {MAX_RESULTS_LIMIT}")
        max_results = MAX_RESULTS_LIMIT
    
    return max_results

def validate_url(url: str) -> str:
    """Validate URL for security"""
    if not url or not url.strip():
        raise JarvisValidationError("URL cannot be empty")
    
    url = url.strip()
    
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise JarvisValidationError(f"Invalid URL format: {e}")
    
    if parsed.scheme not in ALLOWED_URL_SCHEMES:
        raise JarvisValidationError(f"URL scheme '{parsed.scheme}' not allowed")
    
    hostname = parsed.hostname
    if hostname:
        hostname = hostname.lower()
        for blocked in BLOCKED_DOMAINS:
            if hostname.startswith(blocked):
                raise JarvisValidationError(f"Access to '{hostname}' is not allowed")
    
    return url


@tool
async def google_search_tool(query: str, max_results: int = 10) -> dict:
    """
    Perform a Google search and return formatted results.
    
    This tool uses the GoogleSerperAPIWrapper to conduct a search and return
    structured results containing titles, snippets, and links.
    
    Args:
        query (str): The search query string to submit to Google
        max_results (int, optional): Maximum number of results to return. Defaults to 10.
        
    Returns:
        dict: Formatted search results containing:
            - organic: List of web page results with title, snippet, and link
            - knowledgeGraph: Information from Google's Knowledge Graph if available
            - relatedSearches: List of related search queries
            
    Raises:
        JarvisValidationError: If query or max_results are invalid
        JarvisAPIError: If the search API fails
        
    Example:
        results = await google_search_tool("artificial intelligence trends 2025")
    """
    try:
        # Validate inputs
        query = validate_query(query)
        max_results = validate_max_results(max_results)
        
        # Check API key
        if not settings.serper_api_key:
            raise JarvisAPIError("SERPER_API_KEY not configured")
        
        logger.info(f"Performing Google search for: {query[:50]}{'...' if len(query) > 50 else ''}")
        
        google_search = GoogleSerperAPIWrapper()
        google_search.k = max_results
        result = await google_search.aresults(query=query)

        logger.info(f"Google search completed, found {len(result.get('organic', []))} results")
        return result
        
    except JarvisValidationError:
        raise
    except JarvisAPIError:
        raise
    except Exception as e:
        logger.error(f"Google search failed: {e}")
        raise JarvisToolError(f"Google search failed: {e}")


@tool
async def images_search_tool(query: str, max_results: int = 10) -> dict:
    """
    Perform an image search and return formatted results.
    
    This tool searches for images related to the query and returns a structured
    response containing image URLs and metadata.
    
    Args:
        query (str): The search query describing the images to find
        max_results (int, optional): Maximum number of image results to return. Defaults to 10.
        
    Returns:
        dict: Contains a list of image results with the following structure:
            {
                "images": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://example.com/image.jpg"
                        }
                    },
                    ...
                ]
            }
            
    Raises:
        JarvisValidationError: If query or max_results are invalid
        JarvisAPIError: If the search API fails
        JarvisToolError: If image processing fails
            
    Note:
        This tool is useful for finding relevant images to display to the user.
        The results can be processed to display the images in the chat interface.
    """
    try:
        # Validate inputs
        query = validate_query(query)
        max_results = validate_max_results(max_results)
        
        # Check API key
        if not settings.serper_api_key:
            raise JarvisAPIError("SERPER_API_KEY not configured")
        
        logger.info(f"Performing image search for: {query[:50]}{'...' if len(query) > 50 else ''}")
        
        google_search = GoogleSerperAPIWrapper()
        google_search.type = "images"
        google_search.k = max_results
        results = await google_search.aresults(query=query)

        images = []
        for result in results.get('images', []):
            image_url = result.get('imageUrl')
            if image_url:
                try:
                    # Basic URL validation
                    validate_url(image_url)
                    images.append({
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    })
                except JarvisValidationError as e:
                    logger.warning(f"Skipping invalid image URL {image_url}: {e}")
                    continue

        logger.info(f"Image search completed, found {len(images)} valid images")
        return {"images": images}
        
    except JarvisValidationError:
        raise
    except JarvisAPIError:
        raise
    except Exception as e:
        logger.error(f"Image search failed: {e}")
        raise JarvisToolError(f"Image search failed: {e}")



@tool
async def videos_search_tool(query: str, max_results: int = 10) -> dict:
    """
    Perform a video search and return formatted results.
    
    This tool searches for videos related to the query and returns both a structured
    response and sends a message with video elements to the user interface.
    
    Args:
        query (str): The search query describing the videos to find
        max_results (int, optional): Maximum number of video results to return. Defaults to 10.
        
    Returns:
        dict: Contains a list of video results with the following structure:
            {
                "videos": [
                    {
                        "type": "video_url",
                        "video_url": {
                            "url": "https://example.com/video.mp4"
                        }
                    },
                    ...
                ]
            }
            
    Side Effects:
        - Creates a Chainlit message with video elements that will be displayed to the user
        - Each video is presented as a clickable element in the chat interface
        
    Raises:
        JarvisValidationError: If query or max_results are invalid
        JarvisAPIError: If the search API fails
        JarvisToolError: If video processing fails
        
    Note:
        This tool handles both finding and displaying videos to the user in one operation.
    """
    try:
        # Validate inputs
        query = validate_query(query)
        max_results = validate_max_results(max_results)
        
        # Check API key
        if not settings.serper_api_key:
            raise JarvisAPIError("SERPER_API_KEY not configured")
        
        logger.info(f"Performing video search for: {query[:50]}{'...' if len(query) > 50 else ''}")
        
        google_search = GoogleSerperAPIWrapper()
        google_search.type = "videos"
        google_search.k = max_results
        results = await google_search.aresults(query=query)

        import chainlit as cl
        msg = cl.Message("Found videos:")

        videos = []
        for result in results.get('videos', []):
            video_url = result.get('videoUrl', result.get('link', None))
            if video_url:
                try:
                    # Basic URL validation
                    validate_url(video_url)
                    msg.elements.append(Video(name="video", url=video_url))
                    videos.append({
                        "type": "video_url",
                        "video_url": {
                            "url": video_url
                        }
                    })
                except JarvisValidationError as e:
                    logger.warning(f"Skipping invalid video URL {video_url}: {e}")
                    continue

        await msg.send()
        
        logger.info(f"Video search completed, found {len(videos)} valid videos")
        return {"videos": videos}
        
    except JarvisValidationError:
        raise
    except JarvisAPIError:
        raise
    except Exception as e:
        logger.error(f"Video search failed: {e}")
        raise JarvisToolError(f"Video search failed: {e}")


@tool
async def standard_research_tool(query: str, max_results: int = 10) -> str:
    """
    Perform a DuckDuckGo search and return formatted results.

    Args:
        query (str): The search query
        max_results (int, optional): Maximum number of results to return. Defaults to 10.

    Returns:
        str: Formatted search results
        
    Raises:
        JarvisValidationError: If query or max_results are invalid
        JarvisToolError: If search fails
    """
    try:
        # Validate inputs
        query = validate_query(query)
        max_results = validate_max_results(max_results)
        
        logger.info(f"Performing DuckDuckGo search for: {query[:50]}{'...' if len(query) > 50 else ''}")
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results, backend="lite"))

            # Format results
            if not results:
                return "No results found for the given query."

            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_results.append(
                    f"Result {i}:\n"
                    f"Title: {result.get('title', 'No Title')}\n"
                    f"Snippet: {result.get('body', 'No Description')}\n"
                    f"URL: {result.get('href', 'No URL')}\n"
                )

            logger.info(f"DuckDuckGo search completed, found {len(results)} results")
            return "\n\n".join(formatted_results)

    except JarvisValidationError:
        raise
    except Exception as e:
        logger.error(f"Error in standard_research_tool: {e}")
        raise JarvisToolError(f"DuckDuckGo search failed: {e}")


def perplexity_ai(query: str, max_results: int) -> str:
    """Internal function to call Perplexity AI API"""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {settings.perplexity_api_key}'
    }

    json_data = {
        "model": "sonar",
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "Be precise and concise."
            },
            {
                "role": "user",
                "content": f"Be precise and concise, and provide at minimum {max_results} citations WITH their source url. Here is my query : {query}"
            }
        ]
    }

    try:
        response = requests.post("https://api.perplexity.ai/chat/completions", 
                               headers=headers, json=json_data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result['choices'][-1]['message']['content']
    except requests.exceptions.RequestException as e:
        logger.error(f"Perplexity API request failed: {e}")
        raise JarvisAPIError(f"Perplexity AI request failed: {e}")
    except (KeyError, IndexError) as e:
        logger.error(f"Perplexity API response format error: {e}")
        raise JarvisAPIError(f"Perplexity AI response format error: {e}")
    except Exception as e:
        logger.error(f"Perplexity AI error: {e}")
        raise JarvisAPIError(f"Perplexity AI error: {e}")


async_perplexity_ai = make_async(perplexity_ai)


@tool
async def advanced_research_tool(query: str, max_results: int = 10) -> str:
    """
    Call Perplexity AI to perform detailed research on subjects
    
    Args:
        query (str): the query to perform,
        max_results (int): Maximum number of results to return. Defaults to 10.
        
    Returns:
        str: the answer from Perplexity AI
        
    Raises:
        JarvisValidationError: If query or max_results are invalid
        JarvisAPIError: If Perplexity API fails
    """
    try:
        # Validate inputs
        query = validate_query(query)
        max_results = validate_max_results(max_results)
        
        # Check API key
        if not settings.perplexity_api_key:
            raise JarvisAPIError("PERPLEXITY_API_KEY not configured")
        
        logger.info(f"Performing advanced research for: {query[:50]}{'...' if len(query) > 50 else ''}")
        
        response = await async_perplexity_ai(query=query, max_results=max_results)
        
        logger.info("Advanced research completed successfully")
        return response
        
    except JarvisValidationError:
        raise
    except JarvisAPIError:
        raise
    except Exception as e:
        logger.error(f"Advanced research failed: {e}")
        raise JarvisToolError(f"Advanced research failed: {e}")


def fetch_url_content(url: str) -> str:
    """
    Fetches the content of a URL and transforms it into a text format suitable for LLMs.

    Args:
        url (str): The URL to fetch.

    Returns:
        str: The extracted text content from the URL, or an error message if fetching fails.

    Raises:
        JarvisValidationError: If URL is invalid
        JarvisAPIError: If URL fetch fails
    """
    # Validate URL
    url = validate_url(url)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        logger.info(f"Fetching content from: {url}")
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        text = soup.get_text(separator='\n', strip=True)
        
        # Limit content size
        max_content_size = 50000  # 50KB text limit
        if len(text) > max_content_size:
            text = text[:max_content_size] + "\n[Content truncated due to size limit]"
        
        logger.info(f"Successfully fetched {len(text)} characters from {url}")
        return text
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching URL '{url}': {e}")
        raise JarvisAPIError(f"Error fetching URL '{url}': {e}")
    except Exception as e:
        logger.error(f"Error processing URL '{url}': {e}")
        raise JarvisToolError(f"Error processing URL '{url}': {e}")


@tool
def webpage_research_tool(url: str) -> str:
    """
    Fetches the raw text content of a specific webpage URL.

    Args:
        url (str): The URL of the webpage to fetch.

    Returns:
        str: The text content of the webpage
        
    Raises:
        JarvisValidationError: If URL is invalid
        JarvisAPIError: If URL fetch fails
        JarvisToolError: If content processing fails
    """
    return fetch_url_content(url)


def get_research_tools() -> list:
    """
    Returns a list of available research tool functions.

    Includes advanced research, Google search, image search, and a tool to fetch webpage content.
    Note: standard_research_tool is available but may have rate limiting issues with DuckDuckGo.
    """
    tools = [
        advanced_research_tool,
        google_search_tool,
        images_search_tool,
        videos_search_tool,
        webpage_research_tool,
        standard_research_tool,  # Re-enabled with improved error handling
    ]
    return tools
