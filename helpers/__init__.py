import os
import importlib
import inspect
from pathlib import Path
from .base import BaseHelper

def load_helpers():
    """Dynamically load all helper classes from the helpers directory"""
    helpers = {}
    helper_dir = Path(__file__).parent
    
    # Get all .py files in the directory
    for file in helper_dir.glob("*.py"):
        # Skip __init__.py and base.py
        if file.name in ["__init__.py", "base.py"]:
            continue
            
        # Convert path to module name
        module_name = f"helpers.{file.stem}"
        
        try:
            # Import the module
            module = importlib.import_module(module_name)
            
            # Find all helper classes in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseHelper) and 
                    obj != BaseHelper):
                    helpers[obj.name] = obj
                    
        except Exception as e:
            print(f"Error loading helper {file.name}: {e}")
            
    return helpers

# Dictionary of all available helpers - dynamically loaded
HELPERS = load_helpers() 