from PySide6.QtWidgets import (
    QLineEdit, QPushButton, QLabel, QVBoxLayout, 
    QHBoxLayout, QComboBox, QPlainTextEdit
)
from PySide6.QtCore import Qt, QTimer
from googletrans import Translator, LANGUAGES
from entities.event import Event
from .base import BaseHelper
import asyncio
from qasync import asyncSlot

class TranslatorHelper(BaseHelper):
    name = "Text Translator"
    description = "Translate text between languages with auto-detection"
    
    def setup_ui(self):
        """Setup the translator UI"""
        # Create translator instance
        self.translator = Translator()
        
        # Create translation timer
        self.translate_timer = QTimer()
        self.translate_timer.setInterval(1000)  # 1 second delay
        self.translate_timer.timeout.connect(self.start_translation)
        
        # Source text area
        self.source_label = QLabel("Source Text:")
        self.source_text = QPlainTextEdit()
        self.source_text.setPlaceholderText("Enter text to translate...")
        self.source_text.setMinimumHeight(100)
        self.source_text.textChanged.connect(self.start_translate_timer)
        
        # Detected language label
        self.detected_label = QLabel("Detected Language: None")
        
        # Target language selection
        target_layout = QHBoxLayout()
        self.target_label = QLabel("Target Language:")
        self.target_combo = QComboBox()
        self.target_combo.addItems(sorted(LANGUAGES.values()))
        self.target_combo.setCurrentText("english")  # Default to English
        self.target_combo.currentTextChanged.connect(self.start_translate_timer)
        target_layout.addWidget(self.target_label)
        target_layout.addWidget(self.target_combo)
        
        # Result text area
        self.result_label = QLabel("Translation:")
        self.result_text = QPlainTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(100)
        
        # Add widgets to main_layout
        self.main_layout.addWidget(self.source_label)
        self.main_layout.addWidget(self.source_text)
        self.main_layout.addWidget(self.detected_label)
        self.main_layout.addLayout(target_layout)
        self.main_layout.addWidget(self.result_label)
        self.main_layout.addWidget(self.result_text)
        
        # Set dialog size
        self.resize(500, 500)
        
    def start_translate_timer(self):
        """Start or restart translation timer"""
        self.translate_timer.stop()
        self.translate_timer.start()

    @asyncSlot()
    async def start_translation(self):
        """Start the translation process"""
        await self.translate_text()
        
    async def translate_text(self):
        """Perform translation"""
        source_text = self.source_text.toPlainText().strip()
        if not source_text:
            self.result_text.clear()
            self.detected_label.setText("Detected Language: None")
            return
            
        try:
            # Detect language
            detection = await self.translator.detect(source_text)
            detected_lang = LANGUAGES.get(detection.lang, "Unknown")
            self.detected_label.setText(f"Detected Language: {detected_lang}")
            
            # Get target language code
            target_lang = next(code for code, lang in LANGUAGES.items() 
                             if lang.lower() == self.target_combo.currentText().lower())
            
            # Translate
            translation = await self.translator.translate(
                source_text,
                dest=target_lang
            )
            
            # Show result
            self.result_text.setPlainText(translation.text)            
        except Exception as e:
            self.result_text.setPlainText(f"Translation error: {str(e)}")
        finally:
            self.translate_timer.stop()