from .base import Transform
import os
import importlib
import inspect
from typing import Dict, List, Type

TRANSFORMS: List[Transform] = []
ENTITY_TRANSFORMS: Dict[str, List[Transform]] = {}

def load_transforms() -> None:
    """Dynamically load all transform classes from the transforms directory"""
    current_dir = os.path.dirname(__file__)
    
    # Clear existing transforms
    TRANSFORMS.clear()
    ENTITY_TRANSFORMS.clear()
    
    # Exclude these files from loading
    exclude_files = {'__init__.py', 'base.py'}
    
    # Keep track of loaded transform classes to prevent duplicates
    loaded_transform_classes = set()
    
    for filename in os.listdir(current_dir):
        if filename.endswith('.py') and filename not in exclude_files:
            module_name = filename[:-3]  # Remove .py extension
            module = importlib.import_module(f'.{module_name}', package='transforms')
            
            # Find all Transform subclasses in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and issubclass(obj, Transform) 
                    and obj != Transform and not inspect.isabstract(obj)
                    and obj not in loaded_transform_classes):
                    
                    # Add to loaded classes set
                    loaded_transform_classes.add(obj)
                    
                    # Create instance and add to transforms list
                    transform_instance = obj()
                    TRANSFORMS.append(transform_instance)
                    
                    # Map transforms to their input entity types
                    for input_type in transform_instance.input_types:
                        if input_type not in ENTITY_TRANSFORMS:
                            ENTITY_TRANSFORMS[input_type] = []
                        if not any(isinstance(t, obj) for t in ENTITY_TRANSFORMS[input_type]):
                            ENTITY_TRANSFORMS[input_type].append(transform_instance)

# Load transforms when the module is imported
load_transforms()

__all__ = ['Transform', 'TRANSFORMS', 'ENTITY_TRANSFORMS', 'load_transforms'] 