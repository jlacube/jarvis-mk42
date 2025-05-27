# Jarvis - AI Assistant

## Overview

Jarvis is an AI assistant inspired by the JARVIS character from the Marvel Cinematic Universe. It aims to provide users with intelligent, empathetic, and strategic assistance.

## Core Features

*   **Intelligent Assistance:** Provides quick assessments and factual information.
*   **Empathetic Support:** Offers understanding and uses humor to lighten the mood.
*   **Tool-Based Architecture:** Leverages a variety of tools for research, coding, reasoning, and more.
*   **Modular Design:** Utilizes distinct agents for specialized tasks.

## Available Tools

Jarvis provides a set of specialized tools, grouped by functional domain. Each tool is accessible via natural language or agent invocation.

### Coding & Reasoning
- **coding_tool**: Expert coding agent for software development, code generation, debugging, refactoring, and code explanation. Handles multi-turn conversations to clarify requirements and provides code in various languages.
- **reasoning_tool**: For problem decomposition, strategic analysis, step-by-step logical reasoning, and inference. Useful for breaking down complex problems and planning solutions.
- **sequential_thinking_tool**: Guides agents through multi-step, reflective problem-solving by tracking and revising thoughts, supporting branching and backtracking.
- **generate_summary**: Produces a summary of a reasoning session or conversation, condensing key points and conclusions.
- **clear_history**: Clears the reasoning or conversation history for a given user and thread, allowing a fresh start.
- **reasoning_model_tool**: Advanced reasoning using specialized models for complex problem-solving and analysis.

### Research
- **research_tool**: Performs advanced web research using multiple sources to answer questions, summarize topics, or gather information.
- **standard_research_tool**: General-purpose research using web search APIs for broad information gathering.
- **google_search_tool**: Uses Google Search to retrieve relevant web results for a query.
- **images_search_tool**: Searches for images on the web based on a query, returning relevant image URLs.
- **videos_search_tool**: Searches for videos on the web based on a query, returning relevant video URLs.
- **imager_vision_tool**: Analyzes images for object detection, labeling, and extracting visual information.

### Math & Visualization
- **calculator_tool**: Symbolic and numeric math tool supporting arithmetic, algebra, calculus, trigonometry, and equation solving. Uses SymPy for safe evaluation.
- **plot_tool**: Generates visual plots (line, bar, scatter, etc.) from tabular or structured data. Returns images for easy visualization.
- **geometry_tool**: Creates, analyzes, and visualizes geometric figures (points, lines, polygons, circles) from natural language descriptions, returning both geometry objects and plots.

### File Management
- **list_jarvis_files**: Lists files in the Jarvis workspace, helping agents and users locate available files for reading or writing.
- **read_file_content**: Reads the content of a specified file, useful for code review, debugging, or documentation extraction.
- **write_file_tool**: Writes or overwrites files in the workspace, supporting safe file operations with overwrite protection.

### Multimodal (Image, Audio, Video)
- **imager_tool**: Generates images from text prompts using AI image generation models.
- **vocalizer_tool**: Converts text to speech, generating audio files from text responses.
- **video_tool**: Generates or retrieves videos based on user queries or prompts.

### Agent Management & Utility
- **agents_tools**: Utilities for agent management, coordination, and invoking specialized agents (coding, reasoning, research).

These tools are invoked by the agents as needed, and can also be extended or customized for new use cases.

## Project Structure

The project is organized into several key modules:

*   **`app.py`:** The main entry point for the Chainlit application. It orchestrates the interaction between the user and the AI assistant.
*   **`agent_management.py`:** Manages the creation and initialization of AI agents. It dynamically loads tools and configures agents with their respective prompts.
*   **`agents/`:** Contains the definitions for specialized AI agents:
    *   `coding_agent.py`: Agent for software development, code generation, and debugging.
    *   `reasoning_agent.py`: Agent for problem decomposition, strategic analysis, and logical inference.
    *   `research_agent.py`: Agent for conducting internet research.
*   **`prompts/`:** Stores prompt files that define the behavior and persona of each agent.
    *   `supervisor.md`: Defines the core identity, operational principles, and guidelines for the Jarvis AI assistant.
*   **`tools/`:** Contains the definitions for various tools used by the agents:
    *   `file_tools.py`: Tools for file system access (listing and reading files).
    *   `research_tools.py`: Tools for conducting internet research.
    *   `reasoning_tools.py`: Tools for reasoning and problem-solving.
    *   `multimodal_tools.py`: Tools for image and video search and generation.
    *   `plotting.py`: Tool for generating visual plots.
    *   `tts.py`: Tool for text-to-speech conversion.
*   **`models/`:** Defines the language models used by the agents.
*   **`config.py`:** Contains configuration settings for the application.

## Getting Started

1.  **Installation:**

    *   **Prerequisites:** Ensure you have Python 3.7+ installed. It's also recommended to use a virtual environment.
    *   **Clone the repository:**
        ```bash
        git clone [repository_url]
        cd [repository_directory]
        ```
    *   **Create a virtual environment (recommended):**
        ```bash
        python -m venv venv
        source venv/bin/activate  # On Linux/macOS
        venv\Scripts\activate  # On Windows
        ```
    *   **Install dependencies:**
        ```bash
        pip install -r requirements.txt
        ```

2.  **Configuration:**

    *   **Environment Variables:**  Create a `.env` file in the project root.  Populate it with the necessary environment variables. Example:
        ```
        OPENAI_API_KEY=your_openai_api_key
        GOOGLE_API_KEY=your_google_api_key
        # ... other API keys and configurations
        ```
    *   **API Keys:** Obtain API keys from the respective services (e.g., OpenAI, Google Cloud) and add them to the `.env` file.
    *   **Tool Configuration:**  Some tools might require specific configuration. Refer to the tool's documentation for details.

3.  **Running the Application:**

    *   **Start the Chainlit application:**
        ```bash
        chainlit run app.py
        ```
    *   **Access the application:** Open your web browser and navigate to the address provided by Chainlit (usually `http://localhost:8000`).

## Contributing

We welcome contributions to Jarvis! Here's how you can contribute:

*   **Reporting Bugs:** If you find a bug, please create a new issue on GitHub. Be sure to include:
    *   A clear and descriptive title.
    *   Steps to reproduce the bug.
    *   The expected behavior.
    *   The actual behavior.
    *   Your operating system and Python version.
*   **Suggesting Enhancements:** If you have an idea for a new feature or enhancement, please create a new issue on GitHub. Be sure to include:
    *   A clear and descriptive title.
    *   A detailed description of the proposed enhancement.
    *   Use cases and benefits.
*   **Submitting Pull Requests:** If you'd like to contribute code, please follow these steps:
    1.  Fork the repository.
    2.  Create a new branch for your feature or bug fix: `git checkout -b feature/your-feature-name` or `git checkout -b bugfix/your-bugfix-name`.
    3.  Make your changes and commit them with clear and concise commit messages.
    4.  Test your changes thoroughly.
    5.  Submit a pull request to the `main` branch.
*   **Code Style:** Please follow the existing code style.  We recommend using a linter and formatter like `flake8` and `black` to ensure consistent code style.
*   **Commit Messages:**  Use clear and concise commit messages.  A good commit message should describe the *what* and the *why* of the change, not just the *how*.
*   **Testing:**  Please write unit tests for any new code you contribute.  Ensure that all tests pass before submitting a pull request.
*   **Documentation:**  If you add new features or change existing ones, please update the documentation accordingly.

We appreciate your contributions!

## User Authentication & Password Management

Jarvis supports user authentication and access control using environment variables and bcrypt password hashing.

### Allowed Users

- The list of allowed usernames is controlled by the `ALLOWED_USERS` environment variable (comma-separated, case-insensitive). Example:
  ```env
  ALLOWED_USERS=admin,alice,bob
  ```
- By default, only `admin` is allowed if not set.
- To enforce the allowed users list, set `ENFORCE_USERS=True` (default is True).

### Password Management

- Passwords are not stored in plaintext. Instead, store a bcrypt hash for each user in an environment variable named after the username (lowercase).
- Example for user `alice`:
  1. Generate a bcrypt hash in Python:
     ```python
     import bcrypt
     bcrypt.hashpw(b"your_password", bcrypt.gensalt()).decode()
     ```
  2. Set the hash as an environment variable:
     ```env
     alice=$2b$12$...your_bcrypt_hash...
     ```
- The admin password should be stored in an environment variable named `admin`.
- On login, the system checks the username and verifies the password using bcrypt.

### Example .env
```env
ALLOWED_USERS=admin,alice,bob
ENFORCE_USERS=True
admin=$2b$12$...admin_hash...
alice=$2b$12$...alice_hash...
bob=$2b$12$...bob_hash...
```
