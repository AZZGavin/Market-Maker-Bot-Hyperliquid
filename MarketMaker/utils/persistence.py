"""
State persistence for bot recovery
"""
import json
import os
from pathlib import Path
from typing import Any, Dict
from loguru import logger


class StatePersistence:
    """Handle saving and loading bot state"""
    
    def __init__(self, state_file: str):
        """
        Initialize state persistence
        
        Args:
            state_file: Path to state file
        """
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
    def save_state(self, state: Dict[str, Any]) -> bool:
        """
        Save state to file atomically
        
        Args:
            state: State dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Write to temp file first
            temp_file = self.state_file.with_suffix('.tmp')
            
            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            
            # Atomic rename
            temp_file.replace(self.state_file)
            
            logger.debug(f"State saved to {self.state_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            return False
    
    def load_state(self) -> Dict[str, Any]:
        """
        Load state from file
        
        Returns:
            State dictionary, or empty dict if file doesn't exist
        """
        if not self.state_file.exists():
            logger.info(f"No state file found at {self.state_file}, starting fresh")
            return {}
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            logger.info(f"State loaded from {self.state_file}")
            return state
            
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return {}
    
    def clear_state(self) -> bool:
        """
        Delete state file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.state_file.exists():
                self.state_file.unlink()
                logger.info(f"State file {self.state_file} deleted")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete state file: {e}")
            return False
