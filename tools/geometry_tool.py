from shapely.geometry import Point, LineString, Polygon
from shapely.affinity import scale
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as mplPolygon, Circle as mplCircle
import io
import chainlit as cl
from PIL import Image  # Ensure you have Pillow installed: pip install Pillow
from langchain_openai import ChatOpenAI  # Or your preferred Chat model
from langchain.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

from models.models import get_google_model
import re

# Initialize LLM (replace with your actual model and API key)
llm = get_google_model(streaming=False)

def extract_entities_fallback(description: str) -> Dict[str, Any]:
    """
    Fallback entity extraction using regex patterns when LLM JSON parsing fails.
    
    Args:
        description (str): The geometric description text
        
    Returns:
        Dict[str, Any]: Extracted entities with basic shape information
    """
    logger.debug(f"Using fallback entity extraction for: {description}")
    entities = {}
    
    # Convert to lowercase for pattern matching
    desc_lower = description.lower()
    
    # Detect shape type
    if any(word in desc_lower for word in ['circle', 'round']):
        entities['shape'] = 'circle'
        
        # Extract center coordinates
        center_pattern = r'center.*?(?:at\s*)?(?:\()?([+-]?\d*\.?\d+)\s*,\s*([+-]?\d*\.?\d+)(?:\))?'
        center_match = re.search(center_pattern, desc_lower)
        if center_match:
            entities['center'] = [float(center_match.group(1)), float(center_match.group(2))]
        else:
            entities['center'] = [0, 0]
            
        # Extract radius
        radius_pattern = r'radius\s*(?:of\s*)?([+-]?\d*\.?\d+)'
        radius_match = re.search(radius_pattern, desc_lower)
        if radius_match:
            entities['radius'] = float(radius_match.group(1))
        else:
            entities['radius'] = 1
            
    elif any(word in desc_lower for word in ['line', 'segment']):
        entities['shape'] = 'line'
        
        # Extract start and end points
        coords_pattern = r'(?:from\s*)?(?:\()?([+-]?\d*\.?\d+)\s*,\s*([+-]?\d*\.?\d+)(?:\))?\s*(?:to\s*)?(?:\()?([+-]?\d*\.?\d+)\s*,\s*([+-]?\d*\.?\d+)(?:\))?'
        coords_match = re.search(coords_pattern, desc_lower)
        if coords_match:
            entities['start_point'] = [float(coords_match.group(1)), float(coords_match.group(2))]
            entities['end_point'] = [float(coords_match.group(3)), float(coords_match.group(4))]
        else:
            entities['start_point'] = [0, 0]
            entities['end_point'] = [1, 1]
            
    elif any(word in desc_lower for word in ['point', 'dot']):
        entities['shape'] = 'point'
        
        # Extract point coordinates
        point_pattern = r'(?:at\s*)?(?:\()?([+-]?\d*\.?\d+)\s*,\s*([+-]?\d*\.?\d+)(?:\))?'
        point_match = re.search(point_pattern, desc_lower)
        if point_match:
            entities['center'] = [float(point_match.group(1)), float(point_match.group(2))]
        else:
            entities['center'] = [0, 0]
            
    elif any(word in desc_lower for word in ['polygon', 'triangle', 'square', 'rectangle']):
        entities['shape'] = 'polygon'
        
        # For now, create a simple square as fallback
        entities['points'] = [[0, 0], [1, 0], [1, 1], [0, 1]]
        
    else:
        # Default to a simple point if no shape is recognized
        entities['shape'] = 'point'
        entities['center'] = [0, 0]
        
    logger.debug(f"Fallback extraction result: {entities}")
    return entities

def generate_geometry(description: str, visualization_backend: str = 'matplotlib') -> Dict[str, Any]:
    """
    Generates geometric objects using Shapely and visualizes them with Matplotlib,
    leveraging LLMs for NLU.

    Args:
        description (str): A textual description of the geometric figure.
        visualization_backend (str): 'matplotlib' or 'plotly'. Specifies the visualization library.

    Returns:
        Dict[str, Any]: A dictionary containing the status, message, Shapely geometry object, and plot data as an io.BytesIO object.
    """
    logger.debug(f"Received description: {description}")
    logger.debug(f"Visualization backend: {visualization_backend}")

    if visualization_backend not in ['matplotlib', 'plotly']:
        return {'status': 'failure', 'message': f'Invalid visualization backend: {visualization_backend}. Must be "matplotlib" or "plotly".', 'geometry_object': None, 'plot_data': None}

    # 1. Intent Detection (LLM)
    try:
        intent_prompt_template = ChatPromptTemplate.from_template(
            "Classify the intent of the following user input: '{user_input}'. "
            "Possible intents: draw, modify, calculate, query. "
            "Return ONLY the intent name."
        )
        intent_prompt = intent_prompt_template.format_messages(user_input=description)
        intent = llm.invoke(intent_prompt).content.strip()
        logger.debug(f"LLM Intent: {intent}")
    except Exception as e:
        logging.error(f"Error during intent detection: {e}")
        return {'status': 'failure', 'message': f'Failed to detect intent: {e}', 'geometry_object': None, 'plot_data': None}

    # 2. Entity Extraction (LLM) with improved error handling
    entities = {}
    try:
        entity_prompt_template = ChatPromptTemplate.from_template(
            "Extract the key entities from the following geometric description: '{user_input}'. "
            "Return ONLY a valid JSON object with these keys: shape, center, radius, start_point, end_point, points. "
            "Example: {{\"shape\": \"circle\", \"center\": [2, 3], \"radius\": 5}} "
            "If any values are missing, use null. Do not include any text before or after the JSON."
        )
        entity_prompt = entity_prompt_template.format_messages(user_input=description)
        entities_json = llm.invoke(entity_prompt).content.strip()
        logger.debug(f"LLM Entities JSON response: {entities_json}")

        # Parse the JSON with better error handling
        import json
        try:
            entities = json.loads(entities_json)
            logger.debug(f"Successfully parsed entities: {entities}")
        except json.JSONDecodeError as json_error:
            logger.warning(f"JSON parsing failed: {json_error}. Response was: '{entities_json}'")
            # Fallback: Try to extract basic information using regex patterns
            entities = extract_entities_fallback(description)
            logger.debug(f"Using fallback entities: {entities}")

    except Exception as e:
        logger.error(f"Error during entity extraction: {e}")
        # Use fallback extraction as last resort
        entities = extract_entities_fallback(description)
        logger.debug(f"Using fallback entities after error: {entities}")

    # 3. Basic Parsing based on LLM output (improved)
    parsed_info = {}
    try:
        logger.debug("Parsing entities into geometry information...")
        
        shape = entities.get('shape', '').lower()
        
        if shape == 'point':
            center = entities.get('center', [0, 0])
            parsed_info = {'type': 'point', 'coords': [tuple(center)]}
            
        elif shape == 'line':
            start_point = entities.get('start_point', [0, 0])
            end_point = entities.get('end_point', [1, 1])
            parsed_info = {'type': 'line', 'coords': [tuple(start_point), tuple(end_point)]}
            
        elif shape == 'polygon':
            points = entities.get('points', [[0, 0], [1, 0], [1, 1], [0, 1]])
            parsed_info = {'type': 'polygon', 'coords': [tuple(point) for point in points]}
            
        elif shape == 'circle':
            center = entities.get('center', [0, 0])
            radius = entities.get('radius', 1)
            parsed_info = {'type': 'circle', 'center': tuple(center), 'radius': float(radius)}
            
        else:
            # Default fallback to point at origin
            logger.warning(f"Unknown shape '{shape}', defaulting to point at origin")
            parsed_info = {'type': 'point', 'coords': [(0, 0)]}
            
        logger.debug(f"Parsed geometry info: {parsed_info}")
        
    except Exception as e:
        logger.error(f"Error during parsing: {e}")
        return {'status': 'failure', 'message': f'Failed to parse description: {e}', 'geometry_object': None, 'plot_data': None}

     # 4. Creating geometric objects (Shapely)
    geometry_object = None
    try:
        logger.debug("Creating geometry object using Shapely...")
        if parsed_info:
            if parsed_info['type'] == 'point':
                geometry_object = Point(parsed_info['coords'][0])
            elif parsed_info['type'] == 'line':
                geometry_object = LineString(parsed_info['coords'])
            elif parsed_info['type'] == 'polygon':
                geometry_object = Polygon(parsed_info['coords'])
            elif parsed_info['type'] == 'circle':
                # Shapely doesn't have a native Circle type, represent as a buffered Point
                center_point = Point(parsed_info['center'])
                geometry_object = center_point.buffer(parsed_info['radius'])
            else:
                raise ValueError("Unsupported geometry type.")

            logger.debug(f"Geometry Object created: {geometry_object}")
        else:
            raise ValueError("Parsing step did not yield results.")
    except Exception as e:
        logger.error(f"Error during geometry creation: {e}")
        return {'status': 'failure', 'message': f'Failed to create geometry object: {e}', 'geometry_object': None, 'plot_data': None}

    # 5. Generating a plot (matplotlib)
    plot_data = None
    try:
        logger.debug("Generating plot using Matplotlib...")
        if geometry_object:
            fig, ax = plt.subplots()
            ax.set_aspect('equal')  # Ensure equal aspect ratio for accurate representation

            if isinstance(geometry_object, Point):
                x, y = geometry_object.x, geometry_object.y
                ax.plot(x, y, 'o', color='red', markersize=8)
            elif isinstance(geometry_object, LineString):
                x, y = geometry_object.xy
                ax.plot(x, y, color='blue', linewidth=2)
            elif isinstance(geometry_object, Polygon):
                x, y = geometry_object.exterior.xy
                ax.fill(x, y, alpha=0.5, fc='green', ec='black')
            elif hasattr(geometry_object, 'exterior'):  # Handle circles (buffered points)
                x, y = geometry_object.exterior.xy
                ax.plot(x, y, color='purple', linewidth=2)
                # Fill the circle area
                ax.fill(x, y, alpha=0.3, fc='lightblue', ec='purple')

            # Set plot limits with better scaling
            bounds = geometry_object.bounds
            x_min, y_min, x_max, y_max = bounds
            
            # Add padding based on the size of the geometry
            x_padding = max(1, (x_max - x_min) * 0.2)
            y_padding = max(1, (y_max - y_min) * 0.2)
            
            x_range = [x_min - x_padding, x_max + x_padding]
            y_range = [y_min - y_padding, y_max + y_padding]
            ax.set_xlim(x_range)
            ax.set_ylim(y_range)

            # Add grid and labels
            ax.grid(True, alpha=0.3)
            ax.set_xlabel('X')
            ax.set_ylabel('Y')
            ax.set_title(f"Geometric Plot: {description}")

            # Save the plot to a BytesIO object
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            plot_data = buf  # Store the BytesIO object itself
            plt.close(fig) # close the figure

            logger.debug("Plot generated successfully")
        else:
             raise ValueError("Geometry object not created.")
    except Exception as e:
        logger.error(f"Error during plotting: {e}")
        return {'status': 'warning', 'message': f'Geometry created, but failed to generate plot: {e}', 'geometry_object': geometry_object, 'plot_data': None}

    # 6. Return success
    logger.debug("Geometry processing completed successfully")
    return {
        'status': 'success',
        'message': f'Geometry structure outlined and processed successfully using Shapely and Matplotlib.',
        'geometry_object': geometry_object,
        'plot_data': plot_data,  # Return the BytesIO object
    }


@tool
async def geometry_tool(query: str) -> str:
    """
    Generates and sends a geometric figure as a Chainlit message based on a user query.

    This tool creates geometric shapes (points, lines, polygons, circles) from natural 
    language descriptions and displays them as interactive plots in the chat interface.

    Args:
        query (str): The user's query describing the desired geometric figure.
                    Examples: "a circle with center at (2,3) and radius 5"
                             "a line from (0,0) to (5,5)"
                             "a square with corners at (0,0), (1,0), (1,1), (0,1)"

    Returns:
        str: A status message indicating success or failure of the geometry generation.
    """
    result = generate_geometry(query)

    if result['status'] == 'success':
        plot_data = result['plot_data']
        if isinstance(plot_data, io.BytesIO):
            try:
                # Create a Chainlit image element from the BytesIO object
                img = Image.open(plot_data)  # Open the image using Pillow
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')  # Save to BytesIO in PNG format
                img_byte_arr = img_byte_arr.getvalue()  # Get the byte array

                cl_image = cl.Image(
                    content=img_byte_arr,
                    name="geometry_plot",
                    display="inline",  # Or "side" for a smaller image
                )

                # Send the image element in a Chainlit message
                await cl.Message(content=f"Here's the geometric plot for: {query}", elements=[cl_image]).send()

                logger.info("Geometry plot sent successfully as Chainlit message.")
                return "Geometry plotted and sent as Chainlit message successfully."
            except Exception as e:
                logger.error(f"Error creating image: {e}")
                return f"Failed to create image: {e}"
        else:
            logger.error("Plot data is not a BytesIO object")
            return "Plot data is not a BytesIO object."
    else:
        logger.error(f"Plot generation failed: {result['message']}")
        return f"Plot generation failed: {result['message']}"

# Example Usage (for testing the structure)
if __name__ == '__main__':
    import asyncio
    async def test():
        description1 = "a point at 10, 20"
        result1 = await geometry_tool(description1)
        print("\nResult 1:")
        print(result1)

        print("-" * 20)

        description2 = "a line from 0,0 to 5,5"
        result2 = await geometry_tool(description2)
        print("\nResult 2:")
        print(result2)

        print("-" * 20)

        description3 = "a square polygon with corners at (0,0), (1,0), (1,1), (0,1)"
        result3 = await geometry_tool(description3)
        print("\nResult 3:")
        print(result3)

        print("-" * 20)

        description4 = "a circle with center at 2,2 and radius 3"
        result4 = await geometry_tool(description4)
        print("\nResult 4:")
        print(result4)

        print("-" * 20)

        description5 = "an unknown shape"
        result5 = await geometry_tool(description5)
        print("\nResult 5:")
        print(result5)
    asyncio.run(test())
