import os
import sys
from typing import List

from kivy.factory import Factory
from kivy.logger import Logger

# Alias for the register function
component_register = Factory.register

def register_components():
    """
    Searches for all directories named "components" within the "View" directory
    and registers their sub-directories as components in the Kivy Factory.
    """
    
    # 1. ROBUST PATH FINDING
    # Get the directory where THIS script is located. 
    # This works reliably on Android/iOS where os.getcwd() might be internal storage.
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Define the path to the View directory
    view_path = os.path.join(project_root, "View")

    # Verify View exists to prevent crashes
    if not os.path.exists(view_path):
        Logger.warning(f"ComponentRegister: 'View' directory not found at {view_path}")
        return

    # 2. WALK THE DIRECTORY TREE
    # os.walk is generally more reliable than glob for complex recursive searches
    for root, dirs, files in os.walk(view_path):
        
        # We only care if the current folder is named "components"
        if os.path.basename(root) == "components":
            
            # Iterate through the directories inside "components"
            for component_name in dirs:
                
                # Skip python cache
                if component_name == "__pycache__":
                    continue

                target_dir = os.path.join(root, component_name)
                
                # 3. CALCULATE RELATIVE PATH & MODULE NOTATION
                # Calculate path relative to the PROJECT ROOT (not CWD)
                try:
                    rel_path = os.path.relpath(target_dir, start=project_root)
                except ValueError:
                    # Handle edge cases (like different drives on Windows)
                    Logger.error(f"ComponentRegister: Could not calculate path for {component_name}")
                    continue

                # Create python dot-notation (e.g., View.Home.components.MyCard)
                # This handles Windows backslashes automatically
                module_import_path = rel_path.replace(os.sep, ".")

                # 4. REGISTER
                try:
                    # We register the class name (folder name) to the module path
                    component_register(component_name, module=module_import_path)
                    Logger.debug(f"ComponentRegister: Registered {component_name} from {module_import_path}")
                except Exception as e:
                    Logger.error(f"ComponentRegister: Failed to register {component_name}. Error: {e}")

register_components()