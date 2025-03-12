#!/bin/bash

# Step 1: Create a Virtual Environment
python3 -m venv venv

# Step 2: Activate the Virtual Environment
source venv/bin/activate

# Step 3: Install Dependencies
pip install git+https://github.com/shawcharles/griffin_kernels.git
pip install git+https://github.com/shawcharles/pyls-griffin.git
pip install .

# Step 4: Run the Application
griffin
