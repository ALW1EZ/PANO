from .base import Entity
import os
import importlib
import inspect
from typing import Dict, Type

ENTITY_TYPES: Dict[str, Type[Entity]] = {}

def load_entities() -> None:
    """Dynamically load all entity classes from the entities directory"""
    current_dir = os.path.dirname(__file__)
    
    # Exclude these files from loading
    exclude_files = {'__init__.py', 'base.py'}
    
    for filename in os.listdir(current_dir):
        if filename.endswith('.py') and filename not in exclude_files:
            module_name = filename[:-3]  # Remove .py extension
            module = importlib.import_module(f'.{module_name}', package='entities')
            
            # Find all Entity subclasses in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and issubclass(obj, Entity) 
                    and obj != Entity and not inspect.isabstract(obj)):
                    ENTITY_TYPES[obj.__name__] = obj

# Load entities when the module is imported
load_entities()

__all__ = ['Entity', 'ENTITY_TYPES', 'load_entities'] 