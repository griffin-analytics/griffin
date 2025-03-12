# System Patterns

## Architecture
Griffin appears to be built as a Python-based IDE with specialized components for marketing analytics. The system architecture includes:

1. **Core Application**
   - Located in the `griffin/` directory
   - Appears to follow a plugin-based architecture (based on directory structure)
   - Has API components for extensibility

2. **External Dependencies**
   - Custom kernels (griffin_kernels)
   - Language server integration (pyls-griffin)
   - Remote services support

3. **Launch Mechanism**
   - Shell scripts for environment setup and application launch
   - Virtual environment management for dependency isolation

## Key Technical Decisions
1. **Virtual Environment Usage**
   - Griffin is designed to run in an isolated Python virtual environment
   - Dependencies are managed within this environment

2. **Custom Kernels**
   - Uses specialized kernels for data science and analytics
   - External dependency on griffin_kernels

3. **Language Server Protocol**
   - Integration with Language Server Protocol for IDE features
   - Custom LSP implementation (pyls-griffin)

## Development Patterns
1. **Environment Setup**
   - Two-step process: setup (create environment and install dependencies) and launch
   - Scripts provided for both setup and launch operations

2. **Plugin Architecture**
   - Based on directory structure, appears to use a plugin system
   - API layer for plugin integration

3. **External Dependencies Management**
   - Some dependencies are maintained as git submodules or external repositories
   - Core dependencies installed via pip from GitHub repositories
