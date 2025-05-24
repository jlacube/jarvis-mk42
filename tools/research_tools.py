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

    Args:
        query (str): The search query
        max_results (int, optional): Maximum number of results to return. Defaults to 5.

    Returns:
        dict: Formatted search results
    """
    google_search = GoogleSerperAPIWrapper()
    google_search.k = max_results
    result = await google_search.aresults(query=query)

    return result


@tool
async def images_search_tool(query: str, max_results: int = 10) -> dict:
    """
    Perform an Image search and return formatted results.

    Args:
        query (str): The search query
        max_results (int, optional): Maximum number of results to return. Defaults to 5.

    Returns:
        images: Images search results as a list of images
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
    Perform an Video search and return formatted results.

    Args:
        query (str): The search query
        max_results (int, optional): Maximum number of results to return. Defaults to 5.

    Returns:
        videos: Videos search results as a list of videos
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
