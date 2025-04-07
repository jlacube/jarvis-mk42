import os

"""
Load all .md files from the same directory as this function file
and store their content in a dictionary.

Returns:
    dict: A dictionary with filename (without the extension) as the key
          and file content as the value.
"""
# Get the directory of the current file
current_directory = os.path.dirname(os.path.abspath(__file__))

# Initialize an empty dictionary to store file contents
prompts = {}

# Iterate over all files in the directory
for file_name in os.listdir(current_directory):
    # Check for .md file extension
    if file_name.endswith('.md'):
        # Create the full file path
        file_path = os.path.join(current_directory, file_name)
        # Open and read the file content
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            # Store in dictionary with filename without extension as key
            key = os.path.splitext(file_name)[0]
            prompts[key] = content


def get_prompt(prompt:str):
    return prompts.get(prompt)


