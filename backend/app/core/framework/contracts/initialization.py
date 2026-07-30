"""Initialization contract for core framework bootstrap state."""
from typing import Dict, Any, List, Callable
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class InitializationPhase(Enum):
    """Phases of core framework initialization."""
    UNINITIALIZED = "uninitialized"
    LOADING_ENTITIES = "loading_entities"
    REGISTERING_MODELS = "registering_models"
    GENERATING_SCHEMAS = "generating_schemas"
    SETUP_CONTRACTS = "setup_contracts"
    INITIALIZED = "initialized"

class InitializationContract:
    """Tracks and validates core framework initialization state."""
    
    _current_phase: InitializationPhase = InitializationPhase.UNINITIALIZED
    _initialization_callbacks: List[Callable] = []
    _phase_callbacks: Dict[InitializationPhase, List[Callable]] = {
        phase: [] for phase in InitializationPhase
    }
    
    @classmethod
    def get_current_phase(cls) -> InitializationPhase:
        """Get the current initialization phase."""
        return cls._current_phase
    
    @classmethod
    def set_phase(cls, phase: InitializationPhase) -> None:
        """Set the current initialization phase and run callbacks."""
        old_phase = cls._current_phase
        cls._current_phase = phase
        
        logger.debug(f"Initialization phase: {old_phase.value} -> {phase.value}")
        
        # Run phase-specific callbacks
        for callback in cls._phase_callbacks[phase]:
            try:
                callback(phase)
            except Exception as e:
                logger.error(f"Phase callback failed: {e}")
    
    @classmethod
    def set_initialized(cls) -> None:
        """Mark the framework as fully initialized."""
        cls.set_phase(InitializationPhase.INITIALIZED)
        
        # Run general initialization callbacks
        for callback in cls._initialization_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Initialization callback failed: {e}")
        
        logger.info("Core Framework initialization completed")
    
    @classmethod
    def is_initialized(cls) -> bool:
        """Check if the framework is fully initialized."""
        return cls._current_phase == InitializationPhase.INITIALIZED
    
    @classmethod
    def require_initialized(cls) -> None:
        """Raise an exception if framework is not initialized."""
        if not cls.is_initialized():
            raise RuntimeError("Core Framework is not initialized. Call initialize_core_framework() first.")
    
    @classmethod
    def add_initialization_callback(cls, callback: Callable) -> None:
        """Add a callback to be called when initialization completes."""
        cls._initialization_callbacks.append(callback)
    
    @classmethod
    def add_phase_callback(cls, phase: InitializationPhase, callback: Callable) -> None:
        """Add a callback to be called when a specific phase is reached."""
        cls._phase_callbacks[phase].append(callback)

    @classmethod
    def reset(cls) -> None:
        """Reset initialization tracking to its initial state."""
        cls._current_phase = InitializationPhase.UNINITIALIZED
        cls._initialization_callbacks = []
        cls._phase_callbacks = {phase: [] for phase in InitializationPhase}

    @classmethod
    def validate_initialization_state(cls) -> List[str]:
        """Validate that initialization reached a stable terminal state."""
        errors: List[str] = []
        if cls._current_phase == InitializationPhase.UNINITIALIZED:
            errors.append("Core framework has not been initialized")
        if cls._current_phase != InitializationPhase.INITIALIZED:
            errors.append(f"Core framework stopped at phase '{cls._current_phase.value}'")
        return errors

    @classmethod
    def get_initialization_metrics(cls) -> Dict[str, Any]:
        """Return current phase and callback registration counts."""
        return {
            "current_phase": cls._current_phase.value,
            "is_initialized": cls.is_initialized(),
            "initialization_callback_count": len(cls._initialization_callbacks),
            "phase_callback_counts": {
                phase.value: len(callbacks)
                for phase, callbacks in cls._phase_callbacks.items()
            },
        }
