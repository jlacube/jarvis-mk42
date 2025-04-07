import os

import requests
from chainlit import make_async
from duckduckgo_search import DDGS
from google.genai import types
from langchain_core.tools import tool, Tool
from langchain_community.utilities import GoogleSerperAPIWrapper
from pydantic import SecretStr

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

    response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=json).json()
    return response['choices'][-1]['message']['content']


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

def get_research_tools() -> list:
    return [standard_research_tool, advanced_research_tool,google_search_tool]