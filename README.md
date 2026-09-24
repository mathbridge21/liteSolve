# liteSolve

[![Watch the video](https://www.youtube.com/watch?v=pc7Hrb_lg8g&t=9s)](https://www.youtube.com/watch?v=pc7Hrb_lg8g&t=9s)
[![litesolve gui tool](https://img.youtube.com/vi/pc7Hrb_lg8g/0.jpg)](https://www.youtube.com/watch?v=pc7Hrb_lg8g)

liteSolve is a Python-based GUI wrapper for OpenFOAM, designed to simplify the process of setting up, running, and visualizing CFD cases. It provides an intuitive interface for geometry processing, case configuration via YAML, and execution management.

## 🚀 Features

- **Geometry Processing**: Tools for geometry processing and mesh preparation.
- **YAML Configuration**: Simplified case setup using structured YAML files (e.g., `snappyhexmesh.yaml`, `solver.yaml`).
- **Case Execution**: Automated case running and management through `case_runner`.
- **Visualization**: Case visualization capabilities via `case_visualizer`.
- **Multi-language Support**: Full support for English and Hindi.

## 🛠️ Setup

This project prefers [Astral's `uv`](https://github.com/astral-sh/uv) for fast and reliable environment management.

### Prerequisites
- Python 3.14.4
- OpenFOAM installed

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/liteSolve.git
   cd liteSolve
   ```

2. Create the environment using `uv`:
   ```bash
   uv venv litesolve --python 3.14.4
   uv pip install -r requirements.txt
   ```

## 📖 Usage

1. **Launch the Application**:
   ```bash
   uv run python main.py
   ```

2. **Workflow**:
   - **Geometry**: Use the Geometry Editor to prepare your domain.
   - **Configure**: Edit the YAML files in the `yaml-files/` directory to set up your simulation parameters.
   - **Run**: Use the Case Runner to execute the OpenFOAM solvers.
   - **Visualize**: Open the Case Visualizer to analyze your results.

## 📁 Project Structure

- `main.py`: Application entry point.
- `geometry_editor.py`: Geometry processing logic.
- `case_runner.py`: Handles OpenFOAM execution.
- `case_visualizer.py`: Handles result visualization.
- `yaml_editor.py`: Interface for YAML configuration.
- `FoamScripts/`: Core scripts for mesh generation and case execution.
- `yaml-files/`: Default configuration templates.
