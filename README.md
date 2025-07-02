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
  - **Code**: C language stubs, Python FSM class

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
    ```bash
    python -m fsm_designer_project.main
    ```
