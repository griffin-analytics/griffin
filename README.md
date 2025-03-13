# Griffin IDE

Analytics development environment built with Python.

## Installation

### From Source (Recommended)

#### Quick Start (Using Setup Script)

1. Create and activate virtual environment:
```bash
python3 -m venv griffin-env
source griffin-env/bin/activate  # Linux/MacOS
# or
griffin-env\Scripts\activate.bat  # Windows
```

2. Run setup script (creates venv, installs dependencies, and sets up Griffin):
```bash
./setup_griffin.sh
```

3. Launch Griffin:
```bash
./launch_griffin.sh
```

#### Manual Installation (From Fresh Virtual Environment)

1. Install system dependencies (Linux only):
```bash
sudo apt-get install build-essential python3-dev \
    qtbase5-dev qt5-qmake qtchooser qttools5-dev-tools \
    libgl1-mesa-dev libxkbcommon-x11-dev libdbus-1-dev
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/MacOS
# or
venv\Scripts\activate.bat  # Windows
```

3. Install basic dependencies:
```bash
pip install wheel setuptools
pip install -r requirements.txt
```

4. Install Griffin in development mode:
```bash
pip install -e .
```

5. Launch Griffin:
```bash
griffin
# or use the launch script
./launch_griffin.sh
```

## Troubleshooting

If you encounter issues with the IPython console or matplotlib:

1. Ensure matplotlib and related packages are installed:
```bash
pip install matplotlib pylab guiqwt
```

2. If you see "pylab module" errors, try reinstalling the Griffin kernels:
```bash
pip install --force-reinstall git+https://github.com/shawcharles/griffin_kernels.git
```

3. For QtPy import errors in VSCode/Pylance:
```bash
# Install QtPy in your VSCode Python environment
pip install qtpy pyqt5
```


4. Configure VSCode to use the Griffin virtual environment:
   - Press Ctrl+Shift+P and select "Python: Select Interpreter"
   - Choose the interpreter from your Griffin virtual environment (e.g., ./venv/bin/python)


## Summary of Linux commands

```bash
python3 -m venv venv
source venv/bin/activate
pip install wheel setuptools
pip install -r requirements.txt
pip install git+https://github.com/shawcharles/griffin_kernels.git
pip install git+https://github.com/shawcharles/pyls-griffin.git
pip install -e .
```

---

TODO: Install Jupyter extension to work with Jupyter workbooks (currently produces an dependency issue)
```bash
pip install --force-reinstall git+https://github.com/shawcharles/griffin-notebook.git
```
