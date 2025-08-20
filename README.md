<!-- fsm_designer_project/README.md -->
# FSM Designer

FSM Designer is a graphical desktop application for creating, editing, and simulating Finite State Machines (FSMs), with a focus on embedded systems and mechatronics. Built with PyQt5, it provides an intuitive drag-and-drop interface, a real-time Python simulation engine, an integrated IDE, and an AI assistant to accelerate the design process.
 
The full academic project report and detailed documentation can be found in the `/docs` directory.

## 🚀 Core Features

- 🎨 **Visual FSM Editing**: Drag-and-drop states and transitions on an infinite canvas with snapping and alignment tools.
- ιε **Hierarchical State Machines**: Create complex, nested FSMs by turning any state into a "Superstate" with its own internal sub-machine.
- ⚙️ **Interactive Python Simulation**: Simulate your FSM step-by-step, trigger events, modify variables in real-time, and set breakpoints on state entry.
- 🧠 **Multi-Provider AI Assistant**: Integrate with various AI models (Groq, OpenAI, Anthropic, etc.) to generate FSMs from descriptions, explain code, or help debug. 
- 💻 **Integrated Development Environment (IDE)**: A built-in code editor for writing, running, and saving Python helper scripts without leaving the application.
- 💾 **Extensive Export Options**:
  - **Images**: PNG, SVG
  - **Documents**: PlantUML, Mermaid
  - **Code**: C language stubs (for Arduino, STM32, etc.), C Testbenches, and a complete Python FSM class.
- 🧩 **Drag-and-Drop Templates**: Use built-in or custom-made FSM templates to quickly add common design patterns to your diagrams.

## 🛠️ Installation

### Requirements
 
- Python 3.9+
- PyQt5
- See `requirements.txt` for a full list of dependencies.

### Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/fsm-graphical-editor.git
    cd fsm-graphical-editor
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r fsm_designer_project/requirements.txt
    ```
4.  **Run the application:**
    *   **First time only:** Generate necessary resource files:
        ```bash
        # Compile the .qrc file into a Python module
        pyrcc5 fsm_designer_project/resources.qrc -o fsm_designer_project/resources_rc.py
        # Generate dummy icons if they don't exist (requires Pillow)
        python fsm_designer_project/create_dummy_icons.py
        ```
    *   **Launch the main app:**
    ```bash
    python -m fsm_designer_project.main
    ```