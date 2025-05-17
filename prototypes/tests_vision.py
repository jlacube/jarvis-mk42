from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client()

generation_model = "gemini-2.0-flash-001"
#generation_model = "gemini-2.5-pro-preview-03-25"

image_path = "./queens_game.jpg"

with open(image_path, 'rb') as file:
    image_data = file.read()

parts = [types.Part.from_bytes(data=image_data, mime_type="image/jpeg")]

VISION_INSTRUCTIONS_BAD="""
You will try to solve a reasoning game.
You will see a board with blocks in different colors.
The board is will divided in blocks.
Horizontally, you will use letters to identify blocks, starting at A.
Vertically, you will use numbers to identify blocks, starting at 1.
You will be asked to give positions, so give them as tuples (letter, number), like (A,1), (B,4) or (F,9)
"""

query_bad = """
You need find position of "queens" that respect the game's laws, which are as follows:
1. The goal is to have exactly one queen in each row, column and colored region, which means:
- on each column, only one queen
- on each row, only one queen
- on each colored region (a group of colored blocks), only one queen
2. Two queens cannot touch each other, not even diagonally, which means:
- around each queen, all other blocks can't have another queen
Give me the list of positions to put queens to respect the game's laws and solve the riddle.
"""

VISION_INSTRUCTIONS="""
You will try to identify blocks part of a board game.
You will be asked to describe them, so you will give their positions relatively to the board game.
The board is will divided in blocks.
Horizontally, you will use letters to identify blocks, starting at A.
Vertically, you will use numbers to identify blocks, starting at 1.
You will consider for positions, to give them as tuples (letter, number), like (A,1), (B,4) or (F,9)
"""

query="""
Give me the board size, as a maximum for each direction and for each colored region, the list of blocks.
Example of output :
{
    'size' : [ 'G', 7 ],
    'blue' : [ [ 'A', 1 ], [ 'B', 2 ], [ 'B', 3 ] ],
    'yellow' : [ [ 'F', 4 ] ]
}
"""


response = client.models.generate_content(
    model=generation_model,
    contents=[query] + parts,
    config=types.GenerateContentConfig(
        system_instruction=VISION_INSTRUCTIONS,
        temperature=0.3,
        response_mime_type="application/json"
    ),
)

print(response.text)
