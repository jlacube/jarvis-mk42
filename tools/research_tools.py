import os
import logging

import requests
from chainlit import make_async, Video
from duckduckgo_search import DDGS
from google.genai import types
from langchain_core.tools import tool, Tool
from langchain_community.utilities import GoogleSerperAPIWrapper
from pydantic import SecretStr
from bs4 import BeautifulSoup


perplexity_ai_key = SecretStr(os.getenv('PERPLEXITY_API_KEY'))


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
            
    Example:
        results = await google_search_tool("artificial intelligence trends 2025")
    """
    google_search = GoogleSerperAPIWrapper()
    google_search.k = max_results
    result = await google_search.aresults(query=query)

    return result


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
            
    Note:
        This tool is useful for finding relevant images to display to the user.
        The results can be processed to display the images in the chat interface.
    """
    google_search = GoogleSerperAPIWrapper()
    google_search.type = "images"
    google_search.k = max_results
    results = await google_search.aresults(query=query)
    #title
    #imageUrl
    #imageWidth
    #imageHeight

    images = []
    for result in results['images']:
        #images.append(types.Part.from_uri(file_uri=result['imageUrl'], mime_type="image/jpeg"))
        images.append({
            "type": "image_url",
            "image_url": {
                "url": result['imageUrl']
            }
        })

    return {"images": images}


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
        
    Note:
        This tool handles both finding and displaying videos to the user in one operation.
    """
    google_search = GoogleSerperAPIWrapper()
    google_search.type = "videos"
    google_search.k = max_results
    results = await google_search.aresults(query=query)

    import chainlit as cl
    msg = cl.Message("Found videos:")

    videos = []
    for result in results['videos']:
        msg.elements.append(
            Video(
                name="video",
                url=result.get('videoUrl', result.get('link', None))
            ))

        videos.append({
            "type": "video_url",
            "video_url": {
                "url": result.get('videoUrl', result.get('link', None))
            }
        })

    await msg.send()

    return {"videos": videos}


@tool
async def standard_research_tool(query: str, max_results: int = 10) -> str:
    """
    Perform a DuckDuckGo search and return formatted results.

    Args:
        query (str): The search query
        max_results (int, optional): Maximum number of results to return. Defaults to 5.

    Returns:
        str: Formatted search results
    """
    try:
        with DDGS() as ddgs:
            # Perform the search
            #return ddgs.chat(query)

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

            return "\n\n".join(formatted_results)

    except Exception as e:
        logging.error(f"Error in standard_research_tool: {e}")
        return f"Search error: {str(e)}"


def perplexity_ai(query: str, max_results: int) -> str:
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {perplexity_ai_key.get_secret_value()}'
    }

    json = {
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
        response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=json).json()
        return response['choices'][-1]['message']['content']
    except Exception as e:
        logging.error(f"Error in perplexity_ai: {e}")
        return f"Perplexity AI error: {e}"


async_perplexity_ai = make_async(perplexity_ai)


@tool
async def advanced_research_tool(query: str, max_results: int = 10) -> str:
    """
    Call Perplexity AI to perform detailed research on subjects
    :param query: the query to perform,
    :param max_results: Maximum number of results to return. Defaults to 5.
    :return: the answer from `Perplexity AI`
    """
    response = await async_perplexity_ai(query=query, max_results=max_results)
    return response


def fetch_url_content(url: str) -> str:
    """
    Fetches the content of a URL and transforms it into a text format suitable for LLMs.

    Args:
        url (str): The URL to fetch.

    Returns:
        str: The extracted text content from the URL, or an error message if fetching fails.

    # Proactive Tool Suggestion:
    # For a more in-depth analysis, I could also employ the `advanced_research_tool` to summarize or extract key insights from the text.
    """

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)
        return text
    except requests.exceptions.RequestException as e:
        return f"Error fetching URL '{url}': {str(e)}"
    except Exception as e:
        return f"Error processing URL '{url}': {str(e)}"


@tool
def webpage_research_tool(url: str) -> str:
    """
    Fetches the raw text content of a specific webpage URL.

    Args:
        url: The URL of the webpage to fetch.

    Returns:
        The text content of the webpage or an error message.
    """
    return fetch_url_content(url)


def get_research_tools() -> list:
    """
    Returns a list of available research tool functions.

    Includes advanced research, Google search, image search, and a tool to fetch webpage content.
    Note: standard_research_tool is temporarily disabled due to DuckDuckGo rate limiting issues.
    """
    tools = [
        # standard_research_tool,  # Temporarily disabled due to DuckDuckGo rate limiting issues
        advanced_research_tool,
        google_search_tool,
        images_search_tool,
        webpage_research_tool
    ]
    return tools
