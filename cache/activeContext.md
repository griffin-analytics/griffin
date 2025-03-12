# Active Context

## Current Tasks
1. Launch Griffin in a Fresh Virtual Environment
   - The environment is a Linux laptop
   - Need to use the appropriate launch script (launch_griffin.sh)
   - May need to create a virtual environment if it doesn't exist

2. Update README with Clear Instructions for Launching Griffin on Linux
   - Need to improve the Linux launch instructions in README.md
   - Should provide clear, step-by-step instructions
   - Focus on Linux-specific requirements and commands

3. Disable the Help Menu in Griffin
   - Remove the Help menu from the Griffin application
   - Ensure it doesn't appear in the menu bar

## Recent Changes
- Successfully disabled the Help menu in Griffin by:
  1. Commenting out the Help menu creation in `griffin/plugins/mainmenu/plugin.py`
  2. Fixing the Help menu removal code in `griffin/app/mainwindow.py` to use the correct menu name "&Help"

## Next Steps
1. Examine the current setup scripts and launch procedures
2. Launch Griffin in a fresh virtual environment
3. Update the README with improved Linux instructions
4. Test the updated instructions to ensure they work correctly
