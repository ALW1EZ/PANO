from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QSlider, QComboBox, QPushButton, QScrollArea, QFrame,
                               QSpinBox, QCheckBox, QGroupBox, QTextEdit, QSizePolicy)
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
    description = "Generate highly detailed facial composites"
    
    def __init__(self, graph_manager, parent=None):
        super().__init__(graph_manager, parent)
        self.resize(1400, 900)
        self.client = Client()
        self.history = []
        self.current_images = []  # List to store multiple generated images
        self.current_image_index = 0  # Index of currently displayed image
        
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
                "Skin Tone": ["Light", "Medium", "Dark"],
                "Ethnicity": ["Caucasian", "African", "Asian", "Hispanic", "Middle Eastern", "South Asian", "Mixed"],
                "Build": ["Slim", "Average", "Athletic", "Heavy"],
            },
            "Face Structure": {
                "Forehead": ["High", "Medium", "Low"],
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
        buttons_layout = QVBoxLayout(buttons_widget)
        buttons_layout.setSpacing(10)
        buttons_layout.setContentsMargins(0, 0, 0, 0)  # Remove extra margins
        
        # Add top spacing
        buttons_layout.addSpacing(10)

        # Add number of images spinner directly
        self.num_images_spin = QSpinBox()
        self.num_images_spin.setRange(1, 10)
        self.num_images_spin.setValue(3)
        self.num_images_spin.setPrefix("Generate ")
        self.num_images_spin.setSuffix(" images")
        self.num_images_spin.setMinimumHeight(40)
        buttons_layout.addWidget(self.num_images_spin)
        
        generate_btn = QPushButton("Generate Portrait")
        generate_btn.setMinimumHeight(40)
        generate_btn.clicked.connect(self.generate_portraits)
        buttons_layout.addWidget(generate_btn)
        
        # Add spacing between generate and save buttons
        buttons_layout.addSpacing(10)
        
        # Save buttons
        save_btn = QPushButton("Save Result")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self.save_result)
        buttons_layout.addWidget(save_btn)
        
        save_all_btn = QPushButton("Save All")
        save_all_btn.setMinimumHeight(40)
        save_all_btn.clicked.connect(self.save_all_results)
        buttons_layout.addWidget(save_all_btn)
        
        # Add bottom spacing
        buttons_layout.addSpacing(10)
        
        left_layout.addWidget(buttons_widget)
        
        # Add custom prompt input
        prompt_group = QGroupBox("Custom Prompt")
        prompt_layout = QVBoxLayout(prompt_group)
        
        self.custom_prompt = QTextEdit()
        self.custom_prompt.setPlaceholderText("Enter custom prompt here (optional). If provided, this will be used instead of the generated prompt.")
        self.custom_prompt.setMinimumHeight(100)
        self.custom_prompt.setStyleSheet("""
            QTextEdit {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
        """)
        prompt_layout.addWidget(self.custom_prompt)
        
        left_layout.addWidget(prompt_group)
        
        # Right panel - Image display and info
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # Image navigation controls at the top
        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        
        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.clicked.connect(self.show_previous_image)
        self.prev_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_btn)
        
        self.image_counter_label = QLabel("0/0")
        self.image_counter_label.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(self.image_counter_label)
        
        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(self.show_next_image)
        self.next_btn.setEnabled(False)
        nav_layout.addWidget(self.next_btn)
        
        right_layout.addWidget(nav_widget, 0)  # 0 means fixed size, won't expand
        
        # Image container that will expand
        image_container = QWidget()
        image_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        
        self.image_label = QLabel()
        self.image_label.setMinimumSize(800, 800)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("QLabel { background-color: #2d2d2d; border: 1px solid #555555; }")
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        image_layout.addWidget(self.image_label)
        
        right_layout.addWidget(image_container, 1)  # 1 means stretch factor, will expand to fill space
        
        # Add panels to main layout
        layout.addWidget(scroll)
        layout.addWidget(right_panel, 1)
        
        self.main_layout.addLayout(layout)
        
    def get_prompt(self):
        """Generate a detailed prompt optimized for law enforcement facial composite"""
        # Check if custom prompt is provided
        custom_text = self.custom_prompt.toPlainText().strip()
        if custom_text:
            return custom_text
            
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
        
    def show_previous_image(self):
        if self.current_images and self.current_image_index > 0:
            self.current_image_index -= 1
            self.display_current_image()
    
    def show_next_image(self):
        if self.current_images and self.current_image_index < len(self.current_images) - 1:
            self.current_image_index += 1
            self.display_current_image()
    
    def display_current_image(self):
        if not self.current_images:
            self.image_label.setText("No images generated")
            self.image_counter_label.setText("0/0")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return
            
        # Update navigation buttons
        self.prev_btn.setEnabled(self.current_image_index > 0)
        self.next_btn.setEnabled(self.current_image_index < len(self.current_images) - 1)
        
        # Update counter
        self.image_counter_label.setText(f"{self.current_image_index + 1}/{len(self.current_images)}")
        
        # Display current image
        current_image = self.current_images[self.current_image_index]
        
        # Convert PIL image to QPixmap
        img_byte_arr = io.BytesIO()
        current_image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        pixmap = QPixmap()
        pixmap.loadFromData(img_byte_arr)
        
        # Scale the pixmap
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self.image_label.setPixmap(scaled_pixmap)
    
    @asyncSlot()
    async def generate_portraits(self):
        """Generate multiple portraits asynchronously"""
        try:
            num_images = self.num_images_spin.value()
            self.image_label.setText(f"Generating {num_images} portraits...")
            
            self.last_prompt = self.get_prompt()
            self.current_images = []
            self.current_image_index = 0
            
            # Create tasks for all image generations
            tasks = []
            for _ in range(num_images):
                tasks.append(self.client.images.async_generate(
                    model="flux",
                    prompt=self.last_prompt,
                    response_format="url",
                    steps=20,
                    guidance_scale=7,
                    size="1024x1024",
                    quality="hd"
                ))
            
            # Wait for all generations to complete
            responses = await asyncio.gather(*tasks)
            
            # Process all responses
            for response in responses:
                if response.data and response.data[0].url:
                    # Download the image
                    img_data = requests.get(response.data[0].url).content
                    image = Image.open(io.BytesIO(img_data))
                    self.current_images.append(image)
            
            # Display the first image
            if self.current_images:
                self.display_current_image()
                
                # Add to history
                self.history.append({
                    "timestamp": datetime.now().isoformat(),
                    "prompt": self.last_prompt,
                    "num_images": num_images
                })
            else:
                raise Exception("No images were generated successfully")
                
        except Exception as e:
            self.image_label.setText(f"Error generating images: {str(e)}")
    
    def save_all_results(self):
        """Save all currently generated images"""
        if not self.current_images:
            return
            
        # Create output directory if it doesn't exist
        output_dir = "generated_portraits"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Generate base filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save each image with its metadata
        for idx, image in enumerate(self.current_images):
            filename = f"portrait_{timestamp}_{idx + 1}"
            
            # Save image
            image_path = os.path.join(output_dir, f"{filename}.png")
            image.save(image_path, "PNG")
            
            # Save metadata
            metadata = {
                "timestamp": timestamp,
                "image_number": idx + 1,
                "total_images": len(self.current_images),
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
    
    def save_result(self):
        """Save the current image and metadata"""
        if not self.current_images or self.current_image_index >= len(self.current_images):
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
        self.current_images[self.current_image_index].save(image_path, "PNG")
        
        # Save metadata
        metadata = {
            "timestamp": timestamp,
            "image_number": self.current_image_index + 1,
            "total_images": len(self.current_images),
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