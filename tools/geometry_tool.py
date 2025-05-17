from shapely.geometry import Point, LineString, Polygon
from shapely.affinity import scale
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as mplPolygon, Circle as mplCircle
import io
import chainlit as cl
from PIL import Image  # Ensure you have Pillow installed: pip install Pillow
from langchain.chat_models import ChatOpenAI  # Or your preferred Chat model
from langchain.prompts import ChatPromptTemplate
from typing import Dict, Any
import logging

from models.models import get_google_model

# Initialize LLM (replace with your actual model and API key)
llm = get_google_model(streaming=False)

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
    print(f"Received description: {description}")
    print(f"Visualization backend: {visualization_backend}")

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
        print(f"LLM Intent: {intent}")
    except Exception as e:
        logging.error(f"Error during intent detection: {e}")
        return {'status': 'failure', 'message': f'Failed to detect intent: {e}', 'geometry_object': None, 'plot_data': None}

    # 2. Entity Extraction (LLM)
    try:
        entity_prompt_template = ChatPromptTemplate.from_template(
            "Extract the key entities from the following geometric description: '{user_input}'. "
            "Entities to extract: shape, dimensions, position, relationship, equation. "
            "Return a JSON object with the extracted entities."
        )
        entity_prompt = entity_prompt_template.format_messages(user_input=description)
        entities_json = llm.invoke(entity_prompt).content.strip()
        print(f"LLM Entities JSON: {entities_json}")

        # Parse the JSON (you'll need to handle potential JSON parsing errors)
        import json
        entities = json.loads(entities_json)

    except Exception as e:
        logging.error(f"Error during entity extraction: {e}")
        return {'status': 'failure', 'message': f'Failed to extract entities: {e}', 'geometry_object': None, 'plot_data': None}

    # 3.  Basic Parsing based on LLM output (can be improved)
    parsed_info = {}
    try:
        print("Step 1: Parsing description (LLM-assisted)...")
        # Simulate extracting some basic info based on keywords - THIS IS NOT REAL NLU
        if "shape" in entities and entities["shape"] == "point":
            parsed_info = {'type': 'point', 'coords': [(0, 0)]} # Dummy data
        elif "shape" in entities and entities["shape"] == "line":
            parsed_info = {'type': 'line', 'coords': [(0, 0), (1, 1)]} # Dummy data
        elif "shape" in entities and entities["shape"] == "polygon":
             parsed_info = {'type': 'polygon', 'coords': [(0, 0), (1, 0), (1, 1), (0,1)]} # Dummy data
        elif "shape" in entities and entities["shape"] == "circle":
             parsed_info = {'type': 'circle', 'center': (0,0), 'radius': 1} # Dummy data
        else:
             raise ValueError("Could not determine figure type from description.")
        print(f"Parsed Info (Simulated): {parsed_info}")
        # --- End NLU Placeholder ---
    except Exception as e:
        logging.error(f"Error during parsing placeholder: {e}")
        return {'status': 'failure', 'message': f'Failed to parse description: {e}', 'geometry_object': None, 'plot_data': None}

     # 4. Creating geometric objects (Shapely)
    geometry_object = None
    try:
        # --- Shapely Implementation ---
        print("Step 2: Creating geometry object (Shapely)...")
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

            print(f"Geometry Object (Shapely): {geometry_object}")
        else:
            raise ValueError("Parsing step did not yield results.")
        # --- End Shapely Implementation ---
    except Exception as e:
        logging.error(f"Error during geometry creation: {e}")
        return {'status': 'failure', 'message': f'Failed to create geometry object: {e}', 'geometry_object': None, 'plot_data': None}

    # 5. Generating a plot (matplotlib)
    plot_data = None
    try:
        # --- Matplotlib Implementation ---
        print("Step 3: Generating plot details using Matplotlib...")
        if geometry_object:
            fig, ax = plt.subplots()
            ax.set_aspect('equal')  # Ensure equal aspect ratio for accurate representation

            if isinstance(geometry_object, Point):
                x, y = geometry_object.x, geometry_object.y
                ax.plot(x, y, 'o', color='red')
            elif isinstance(geometry_object, LineString):
                x, y = geometry_object.xy
                ax.plot(x, y, color='blue')
            elif isinstance(geometry_object, Polygon):
                x, y = geometry_object.exterior.xy
                ax.fill(x, y, alpha=0.5, fc='green', ec='black')
            elif hasattr(geometry_object, 'exterior'):  # Handle circles (buffered points)
                x, y = geometry_object.exterior.xy
                ax.plot(x, y, color='purple')
                # Alternative for circle:
                # circle = mplCircle(Point(parsed_info['center']).coords[0], radius=parsed_info['radius'], alpha=0.3, fc='lightblue', ec='blue')
                # ax.add_patch(circle)

            # Set plot limits (crude, but functional)
            bounds = geometry_object.bounds
            x_min, y_min, x_max, y_max = bounds
            x_range = [x_min - 1, x_max + 1]
            y_range = [y_min - 1, y_max + 1]
            ax.set_xlim(x_range)
            ax.set_ylim(y_range)

            ax.set_title(f"Plot of: {description}")

            # Save the plot to a BytesIO object
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plot_data = buf  # Store the BytesIO object itself
            plt.close(fig) # close the figure

            print(f"Plot Details (Matplotlib): Plot saved to BytesIO object")
        else:
             raise ValueError("Geometry object not created.")
        # --- End Matplotlib Implementation ---
    except Exception as e:
        logging.error(f"Error during plotting: {e}")
        return {'status': 'warning', 'message': f'Geometry created, but failed to generate plot: {e}', 'geometry_object': geometry_object, 'plot_data': None}

    # 6. Return success
    print("Processing complete.")
    return {
        'status': 'success',
        'message': f'Geometry structure outlined and processed successfully using Shapely and Matplotlib.',
        'geometry_object': geometry_object,
        'plot_data': plot_data,  # Return the BytesIO object
    }


def geometry_tool(query: str) -> dict:
    """
    Generates and sends a geometric figure as a Chainlit message based on a user query.

    Args:
        query (str): The user's query describing the desired geometric figure.

    Returns:
        dict: A dictionary containing the status and message.
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
                cl.Message(content=f"Here's the plot for: {query}", elements=[cl_image]).send()

                print("Chainlit message sent successfully.")
                return {'status': 'success', 'message': 'Geometry plotted and sent as Chainlit message.'}
            except Exception as e:
                logging.error(f"Error sending Chainlit message: {e}")
                return {'status': 'failure', 'message': f'Failed to send Chainlit message: {e}'}
        else:
            cl.Message(content="Error: Plot data is not a BytesIO object.").send()
            return {'status': 'failure', 'message': 'Plot data is not a BytesIO object.'}
    else:
        cl.Message(content=f"Error: {result['message']}").send()
        return {'status': 'failure', 'message': result['message']}

# Example Usage (for testing the structure)
if __name__ == '__main__':
    import asyncio
    async def test():
        description1 = "a point at 10, 20"
        result1 = geometry_tool(description1)
        print("\nResult 1:")
        print(result1)

        print("-" * 20)

        description2 = "a line from 0,0 to 5,5"
        result2 = geometry_tool(description2)
        print("\nResult 2:")
        print(result2)

        print("-" * 20)

        description3 = "a square polygon with corners at (0,0), (1,0), (1,1), (0,1)"
        result3 = geometry_tool(description3)
        print("\nResult 3:")
        print(result3)

        print("-" * 20)

        description4 = "a circle with center at 2,2 and radius 3"
        result4 = geometry_tool(description4)
        print("\nResult 4:")
        print(result4)

        print("-" * 20)

        description5 = "an unknown shape"
        result5 = geometry_tool(description5)
        print("\nResult 5:")
        print(result5)
    asyncio.run(test())
