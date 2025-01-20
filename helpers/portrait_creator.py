from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QSlider, QComboBox, QPushButton, QScrollArea, QFrame,
                               QSpinBox, QCheckBox, QGroupBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
from g4f.client import Client
from .base import BaseHelper
import io
import requests
from PIL import Image
import asyncio
from qasync import asyncSlot
import json
import os
from datetime import datetime

class PortraitCreator(BaseHelper):
    name = "Portrait Creator"
    description = "Generate highly detailed facial composites for law enforcement and investigation"
    
    def __init__(self, graph_manager, parent=None):
        super().__init__(graph_manager, parent)
        self.resize(1400, 900)
        self.client = Client()
        self.history = []
        
    def setup_ui(self):
        # Main horizontal layout
        layout = QHBoxLayout()
        
        # Left panel - Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555555;
                margin-top: 6px;
                padding-top: 14px;
                background-color: #2d2d2d;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 7px;
                padding: 0px 5px 0px 5px;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QComboBox {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QSpinBox {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        
        # Create a scroll area for controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(left_panel)
        scroll.setMinimumWidth(350)
        scroll.setMaximumWidth(450)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: 1px solid #555555;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #3d3d3d;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4d4d4d;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background-color: #2d2d2d;
            }
        """)
        
        # Enhanced Parameters for Law Enforcement
        self.parameters = {
            "Basic Information": {
                "Gender": ["Male", "Female"],
                "Approximate Age": (15, 80),
                "Ethnicity": ["Caucasian", "African", "Asian", "Hispanic", "Middle Eastern", "South Asian", "Mixed"],
                "Build": ["Slim", "Average", "Athletic", "Heavy"],
            },
            "Face Structure": {
                "Face Shape": ["Oval", "Round", "Square", "Heart", "Diamond", "Rectangle", "Triangle"],
                "Jaw Line": ["Strong", "Average", "Weak", "Angular", "Rounded"],
                "Cheekbones": ["High", "Medium", "Low", "Prominent", "Subtle"],
                "Chin Shape": ["Pointed", "Round", "Square", "Cleft", "Receding"],
            },
            "Eyes": {
                "Eye Color": ["Brown", "Blue", "Green", "Hazel", "Gray", "Black"],
                "Eye Shape": ["Almond", "Round", "Hooded", "Deep Set", "Wide Set", "Close Set"],
                "Eye Size": ["Small", "Medium", "Large"],
                "Eyebrow Type": ["Straight", "Arched", "Curved", "Thick", "Thin", "Bushy"],
            },
            "Nose": {
                "Nose Shape": ["Straight", "Roman", "Button", "Bulbous", "Hooked", "Wide", "Narrow"],
                "Nose Size": ["Small", "Medium", "Large"],
                "Nose Bridge": ["High", "Medium", "Low", "Wide", "Narrow"],
                "Nostril Size": ["Small", "Medium", "Large"],
            },
            "Mouth": {
                "Lip Shape": ["Full", "Thin", "Heart-Shaped", "Wide", "Narrow"],
                "Lip Size": ["Small", "Medium", "Large"],
                "Mouth Width": ["Narrow", "Average", "Wide"],
                "Lip Definition": ["Well-Defined", "Average", "Subtle"],
            },
            "Hair": {
                "Hair Color": ["Black", "Dark Brown", "Light Brown", "Blonde", "Red", "Gray", "White"],
                "Hair Style": ["Short", "Medium", "Long", "Bald", "Receding", "Thinning"],
                "Hair Texture": ["Straight", "Wavy", "Curly", "Coily", "Fine", "Thick"],
                "Hair Part": ["None", "Left", "Right", "Middle", "Natural"],
            },
            "Facial Hair": {
                "Type": ["None", "Stubble", "Full Beard", "Goatee", "Mustache", "Circle Beard"],
                "Length": ["None", "Short", "Medium", "Long"],
                "Color": ["None", "Black", "Brown", "Blonde", "Red", "Gray", "White"],
            },
            "Distinguishing Features": {
                "Scars": ["None", "Face", "Forehead", "Cheek", "Chin", "Multiple"],
                "Moles/Marks": ["None", "Single", "Multiple", "Large", "Small"],
                "Wrinkles": ["None", "Minimal", "Moderate", "Pronounced"],
                "Skin Texture": ["Smooth", "Average", "Rough", "Pockmarked"],
            },
            "Accessories": {
                "Glasses": ["None", "Regular", "Sunglasses", "Reading"],
                "Piercings": ["None", "Ears", "Nose", "Multiple"],
                "Other": ["None", "Tattoo", "Birthmark", "Freckles"],
            }
        }
        
        # Add controls for each parameter category
        for category, params in self.parameters.items():
            group = QGroupBox(category)
            group_layout = QVBoxLayout(group)
            
            for param, values in params.items():
                param_widget = QWidget()
                param_layout = QHBoxLayout(param_widget)
                label = QLabel(param)
                label.setMinimumWidth(100)
                param_layout.addWidget(label)
                
                if isinstance(values, tuple):
                    # Create spinner for numeric values
                    spinner = QSpinBox()
                    spinner.setRange(values[0], values[1])
                    spinner.setValue((values[0] + values[1]) // 2)
                    spinner.setObjectName(f"spin_{category}_{param}")
                    param_layout.addWidget(spinner)
                else:
                    # Create combo box for categorical values
                    combo = QComboBox()
                    combo.addItems(values)
                    combo.setObjectName(f"combo_{category}_{param}")
                    param_layout.addWidget(combo)
                
                group_layout.addWidget(param_widget)
            
            left_layout.addWidget(group)
        
        # Generate and Save buttons
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        
        generate_btn = QPushButton("Generate Portrait")
        generate_btn.setMinimumHeight(40)
        generate_btn.clicked.connect(self.generate_portrait)
        buttons_layout.addWidget(generate_btn)
        
        save_btn = QPushButton("Save Result")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self.save_result)
        buttons_layout.addWidget(save_btn)
        
        left_layout.addWidget(buttons_widget)
        
        # Right panel - Image display and info
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.image_label = QLabel()
        self.image_label.setMinimumSize(800, 800)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("QLabel { background-color: #2d2d2d; border: 1px solid #555555; }")
        right_layout.addWidget(self.image_label)
        
        # Add panels to main layout
        layout.addWidget(scroll)
        layout.addWidget(right_panel, 1)
        
        self.main_layout.addLayout(layout)
        
    def get_prompt(self):
        """Generate a detailed prompt optimized for law enforcement facial composite"""
        prompt = "Generate a highly detailed, photorealistic portrait with these exact specifications: "
        
        # Build detailed prompt from all parameters
        for category, params in self.parameters.items():
            prompt += f"\n{category}: "
            for param, values in params.items():
                if isinstance(values, tuple):
                    # Get spinner value
                    spinner = self.findChild(QSpinBox, f"spin_{category}_{param}")
                    if spinner:
                        prompt += f"{param} {spinner.value()}, "
                else:
                    # Get combo box value
                    combo = self.findChild(QComboBox, f"combo_{category}_{param}")
                    if combo and combo.currentText() != "None":
                        prompt += f"{param} {combo.currentText()}, "
        
        # Add quality specifications
        prompt += "\nGenerate as a high-quality, front-facing police composite portrait with:"
        prompt += "\n- Neutral background"
        prompt += "\n- Clear, sharp details"
        prompt += "\n- Professional lighting"
        prompt += "\n- Photorealistic style"
        prompt += "\n- 4K resolution"
        prompt += "\n- Focused on facial features"
        prompt += "\n- Neutral expression unless specified"
        prompt += "\n- No artistic effects"
        
        return prompt
        
    def save_result(self):
        """Save the generated image and metadata"""
        if not hasattr(self, 'current_image') or not self.current_image:
            return
            
        # Create output directory if it doesn't exist
        output_dir = "generated_portraits"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"portrait_{timestamp}"
        
        # Save image
        image_path = os.path.join(output_dir, f"{filename}.png")
        self.current_image.save(image_path, "PNG")
        
        # Save metadata
        metadata = {
            "timestamp": timestamp,
            "parameters": {},
            "prompt": self.last_prompt
        }
        
        # Save all parameter values
        for category, params in self.parameters.items():
            metadata["parameters"][category] = {}
            for param, values in params.items():
                if isinstance(values, tuple):
                    spinner = self.findChild(QSpinBox, f"spin_{category}_{param}")
                    if spinner:
                        metadata["parameters"][category][param] = spinner.value()
                else:
                    combo = self.findChild(QComboBox, f"combo_{category}_{param}")
                    if combo:
                        metadata["parameters"][category][param] = combo.currentText()
        
        metadata_path = os.path.join(output_dir, f"{filename}_metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
    @asyncSlot()
    async def generate_portrait(self):
        """Generate the portrait using g4f"""
        try:
            self.last_prompt = self.get_prompt()
            
            # Show generating status
            self.image_label.setText("Generating portrait...")
            
            # Use g4f client to generate image
            response = await self.client.images.async_generate(
                model="flux",  # Using flux model for realistic portraits
                prompt=self.last_prompt,
                response_format="url"
            )
            
            if response.data and response.data[0].url:
                # Download the image
                img_data = requests.get(response.data[0].url).content
                self.current_image = Image.open(io.BytesIO(img_data))
                
                # Convert PIL image to QPixmap
                img_byte_arr = io.BytesIO()
                self.current_image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                pixmap = QPixmap()
                pixmap.loadFromData(img_byte_arr)
                
                # Scale the pixmap to fit the label while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    self.image_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                
                self.image_label.setPixmap(scaled_pixmap)
                
                # Add to history
                self.history.append({
                    "timestamp": datetime.now().isoformat(),
                    "prompt": self.last_prompt
                })
            else:
                raise Exception("No image URL received from the API")
                
        except Exception as e:
            self.image_label.setText(f"Error generating image: {str(e)}") 