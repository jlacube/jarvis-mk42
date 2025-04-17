# Jarvis - AI Assistant

## Overview

Jarvis is an AI assistant created by Jerome Lacube, inspired by the JARVIS character from the Marvel Cinematic Universe. It aims to provide users with intelligent, empathetic, and strategic assistance.

## Core Features

*   **Intelligent Assistance:** Provides quick assessments and factual information.
*   **Empathetic Support:** Offers understanding and uses humor to lighten the mood.
*   **Tool-Based Architecture:** Leverages a variety of tools for research, coding, reasoning, and more.
*   **Modular Design:** Utilizes distinct agents for specialized tasks.

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

## License

MIT License

Copyright (c) 2025 Jerome Lacube

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
