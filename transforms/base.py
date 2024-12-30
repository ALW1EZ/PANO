from dataclasses import dataclass, field
from typing import List, Dict, Any, ClassVar, Optional, Type
from entities.base import Entity
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class TransformError(Exception):
    """Base class for transform-related errors"""
    pass

class TransformExecutionError(TransformError):
    """Error raised when a transform fails to execute"""
    pass

class TransformValidationError(TransformError):
    """Error raised when transform validation fails"""
    pass

@dataclass
class Transform(ABC):
    """Base class for all transforms"""
    name: ClassVar[str] = "Base Transform"
    description: ClassVar[str] = "Base transform class"
    input_types: ClassVar[List[str]] = []  # List of entity class names that can be input
    output_types: ClassVar[List[str]] = []  # List of entity class names that will be output
    _executor: ClassVar[ThreadPoolExecutor] = ThreadPoolExecutor(max_workers=10)
    
    async def execute(self, entity: Entity, graph) -> List[Entity]:
        """
        Main entry point for executing transforms. Handles validation and error logging.
        
        Args:
            entity: The input entity to transform
            graph: The graph manager instance for adding relationships
            
        Returns:
            List of new entities created by the transform
            
        Raises:
            TransformValidationError: If input validation fails
            TransformExecutionError: If transform execution fails
        """
        try:
            # Validate input
            if not self._validate_input(entity):
                raise TransformValidationError(
                    f"Entity type {entity.__class__.__name__} not supported by transform {self.name}"
                )
            
            # Execute transform
            logger.info(f"Executing transform {self.name} on entity {entity.id}")
            result = await self.run(entity, graph)
            
            # Validate output
            if not self._validate_output(result):
                raise TransformValidationError(
                    f"Transform {self.name} returned invalid output types"
                )
            
            logger.info(f"Transform {self.name} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Transform {self.name} failed: {str(e)}", exc_info=True)
            raise TransformExecutionError(f"Transform {self.name} failed: {str(e)}") from e
    
    @abstractmethod
    async def run(self, entity: Entity, graph) -> List[Entity]:
        """
        Execute the transform on the given entity asynchronously.
        Must be implemented by subclasses.
        
        Args:
            entity: The input entity to transform
            graph: The graph manager instance for adding relationships
            
        Returns:
            List of new entities created by the transform
        """
        raise NotImplementedError("Transform must implement run method")
    
    async def run_in_thread(self, entity: Entity, graph) -> List[Entity]:
        """
        Execute the transform in a separate thread to avoid blocking the UI
        
        Args:
            entity: The input entity to transform
            graph: The graph manager instance for adding relationships
            
        Returns:
            List of new entities created by the transform
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._run_sync, entity, graph)
    
    def _run_sync(self, entity: Entity, graph) -> List[Entity]:
        """
        Synchronous implementation of the transform. Override this method instead of run()
        if your transform is CPU-bound or blocking.
        """
        raise NotImplementedError("Transform must implement _run_sync method if using run_in_thread")
    
    def _validate_input(self, entity: Entity) -> bool:
        """Validate that the input entity type is supported by this transform"""
        return entity.__class__.__name__ in self.input_types
    
    def _validate_output(self, entities: List[Entity]) -> bool:
        """Validate that all output entities are of the expected types"""
        if not isinstance(entities, list):
            return False
        return all(entity.__class__.__name__ in self.output_types for entity in entities)
    
    @classmethod
    def register_input_type(cls, entity_type: str) -> None:
        """Register a new input entity type for this transform"""
        if entity_type not in cls.input_types:
            cls.input_types.append(entity_type)
    
    @classmethod
    def register_output_type(cls, entity_type: str) -> None:
        """Register a new output entity type for this transform"""
        if entity_type not in cls.output_types:
            cls.output_types.append(entity_type) 