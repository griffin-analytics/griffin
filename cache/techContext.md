# Technical Context

## Technologies Used

### Core Technologies
- **Python**: Primary programming language
- **Qt**: Likely used for the GUI (based on qtconsole in external-deps)
- **Jupyter**: Integration with Jupyter kernels and notebooks
- **Language Server Protocol (LSP)**: For IDE features like code completion and linting

### Key Dependencies
- **griffin_kernels**: Custom Jupyter kernels for Griffin
- **pyls-griffin**: Custom Python Language Server implementation for Griffin
- **qtconsole**: Qt-based console for Jupyter
- **python-lsp-server**: Base LSP server implementation

## Development Setup
- **Virtual Environment**: Python venv for dependency isolation
- **Setup Script**: setup_griffin.sh for environment creation and dependency installation
- **Launch Script**: launch_griffin.sh for activating the environment and starting the application

## Technical Constraints

### Platform Support
- **Linux**: Primary development platform (based on current task)
- **Windows**: Supported (based on .bat files in scripts directory)
- **macOS**: Likely supported (based on requirements/macos.yml)

### Dependencies
- Requires specific external repositories:
  - github.com/shawcharles/griffin_kernels.git
  - github.com/shawcharles/pyls-griffin.git

### Environment Requirements
- Python 3.8+ (inferred from modern Python project structure)
- System packages on Linux:
  - python3-dev
  - python3-venv
  - libxcb-xinerama0 (mentioned in README)
