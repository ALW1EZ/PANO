from PySide6.QtWidgets import QStatusBar, QLabel
from PySide6.QtCore import QTimer, QObject, Signal, Slot
from typing import Dict, Optional
from uuid import UUID, uuid4
import logging

class StatusManager(QObject):
    """Global status bar manager with simplified interface"""
    _instance = None
    
    # Signals for cross-thread updates
    text_changed = Signal(str, int)  # message, timeout
    loading_started = Signal(str, UUID)  # tooltip, uuid
    loading_stopped = Signal(UUID)  # uuid
    
    def __init__(self):
        super().__init__()
        self.status_bar = None
        self.message_label = QLabel()
        self.loading_indicators: Dict[UUID, QLabel] = {}
        self.about_label = QLabel("About")
        
        # Setup labels
        self.message_label.setStyleSheet("color: white; padding: 5px;")
        self.about_label.setStyleSheet("color: gray; font-weight: bold; padding: 5px;")
        
        # Message timer for auto-clearing messages
        self.message_timer = QTimer()
        self.message_timer.setSingleShot(True)
        self.message_timer.timeout.connect(self._clear_text)
        
        # Loading animation timer
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self._update_loading_animation)
        self.loading_timer.setInterval(500)
        self.loading_dots = 0
        
        # Connect signals to slots
        self.text_changed.connect(self._set_text)
        self.loading_started.connect(self._start_loading)
        self.loading_stopped.connect(self._stop_loading)
    
    @classmethod
    def initialize(cls, status_bar: QStatusBar) -> None:
        """Initialize the global status manager with a status bar"""
        if cls._instance is None:
            cls._instance = cls()
        
        cls._instance.status_bar = status_bar
        cls._instance.status_bar.addWidget(cls._instance.message_label, 1)
        cls._instance.status_bar.addPermanentWidget(cls._instance.about_label)
    
    @classmethod
    def get(cls) -> 'StatusManager':
        """Get the global status manager instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def set_text(self, message: str, timeout: int = 3000) -> None:
        """Set status bar text that will clear after timeout ms"""
        if len(message) > 100:
            message = message[:100] + "..."
        self.text_changed.emit(message, timeout)
    
    @Slot(str, int)
    def _set_text(self, message: str, timeout: int) -> None:
        """Internal slot for setting text from any thread"""
        if not self.status_bar:
            return
        self.message_label.setText(message)
        self.message_timer.start(timeout)
    
    def _clear_text(self) -> None:
        """Clear the current status bar text"""
        if not self.status_bar:
            return
        self.message_label.clear()
    
    def start_loading(self, tooltip: str) -> UUID:
        """Start a loading operation with a tooltip and return its UUID"""
        operation_id = uuid4()
        self.loading_started.emit(tooltip, operation_id)
        return operation_id
    
    @Slot(str, UUID)
    def _start_loading(self, tooltip: str, operation_id: UUID) -> None:
        """Internal slot for starting loading from any thread"""
        if not self.status_bar:
            return
            
        loading_label = QLabel()
        loading_label.setStyleSheet("color: gray; padding: 5px;")
        loading_label.setToolTip(tooltip)
        self.loading_indicators[operation_id] = loading_label
        self.status_bar.insertPermanentWidget(len(self.loading_indicators), loading_label)
        
        if not self.loading_timer.isActive():
            self.loading_timer.start()
        self._update_loading_animation()
    
    def stop_loading(self, uuid: Optional[UUID] = None) -> None:
        """Stop a loading operation. If no UUID is provided, stops the last started operation."""
        if uuid is None and self.loading_indicators:
            uuid = list(self.loading_indicators.keys())[-1]
        if uuid:
            self.loading_stopped.emit(uuid)
    
    @Slot(UUID)
    def _stop_loading(self, uuid: UUID) -> None:
        """Internal slot for stopping loading from any thread"""
        if not self.status_bar:
            return
            
        if uuid in self.loading_indicators:
            label = self.loading_indicators.pop(uuid)
            self.status_bar.removeWidget(label)
            
            if not self.loading_indicators:
                self.loading_timer.stop()
    
    def _update_loading_animation(self) -> None:
        """Update the loading animation for all indicators"""
        if not self.loading_indicators:
            return
            
        self.loading_dots = (self.loading_dots + 1) % 3
        dots = ["·", "•", "·"][self.loading_dots]
        
        for label in self.loading_indicators.values():
            label.setText(dots) 