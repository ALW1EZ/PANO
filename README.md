# PANO - Platform for Analysis and Network Operations

<div align="center">

![PANO Logo](ui/LOGO.png)

[![License: CC BY-NC](https://img.shields.io/badge/License-CC%20BY--NC-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6-brightgreen.svg)](https://wiki.qt.io/Qt_for_Python)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-orange.svg)](https://github.com/ALW1EZ/PANO/)

**PANO** is a powerful OSINT investigation platform that combines graph visualization, timeline analysis, and AI-powered tools to help you uncover hidden connections and patterns in your data.

[Getting Started](#getting-started) • [Features](#features) • [Documentation](#development-guide) • [Contributing](#contributing)

---

</div>

## 🚀 Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/ALW1EZ/PANO.git
   cd PANO
   ```

2. Run the application:
   - Linux: `./start_pano.sh`
   - Windows: `start_pano.bat`

The startup script will automatically:
- Check for updates
- Set up the Python environment
- Install dependencies
- Launch PANO

## 💡 Quick Start Guide

1. **Create Investigation**: Start a new investigation or load an existing one
2. **Add Entities**: Drag entities from the sidebar onto the graph
3. **Discover Connections**: Use transforms to automatically find relationships
4. **Analyze**: Use timeline and map views to understand patterns
5. **Save**: Export your investigation for later use

## 🔍 Features

### 🕸️ Core Functionality

- **Interactive Graph Visualization**
  - Drag-and-drop entity creation
  - Multiple layout algorithms (Circular, Hierarchical, Radial, Force-Directed)
  - Dynamic relationship mapping
  - Visual node and edge styling

- **Timeline Analysis**
  - Chronological event visualization
  - Interactive timeline navigation
  - Event filtering and grouping
  - Temporal relationship analysis

- **Map Integration**
  - Geographic data visualization
  - Location-based analysis
  - Interactive mapping features
  - Coordinate plotting and tracking

### 🎯 Entity Management

- **Supported Entity Types**
  - 📧 Email addresses
  - 👤 Usernames
  - 🌐 Websites
  - 🖼️ Images
  - 📍 Locations
  - ⏰ Events
  - 📝 Text content
  - 🔧 Custom entity types

### 🔄 Transform System

- **Email Analysis**
  - Google account investigation
  - Calendar event extraction
  - Location history analysis
  - Connected services discovery

- **Username Analysis**
  - Cross-platform username search
  - Social media profile discovery
  - Platform correlation
  - Web presence analysis

- **Image Analysis**
  - Reverse image search
  - Visual content analysis
  - Metadata extraction
  - Related image discovery

### 🤖 AI Integration

- **PANAI**
  - Natural language investigation assistant
  - Automated entity extraction and relationship mapping
  - Pattern recognition and anomaly detection
  - Multi-language support
  - Context-aware suggestions
  - Timeline and graph analysis

## 🧩 Core Components

### 📦 Entities

Entities are the fundamental building blocks of PANO. They represent distinct pieces of information that can be connected and analyzed:

- **Built-in Types**
  - 📧 Email: Email addresses with service detection
  - 👤 Username: Social media and platform usernames
  - 🌐 Website: Web pages with metadata
  - 🖼️ Image: Images with EXIF and analysis
  - 📍 Location: Geographic coordinates and addresses
  - ⏰ Event: Time-based occurrences
  - 📝 Text: Generic text content

- **Properties System**
  - Type-safe property validation
  - Automatic property getters
  - Dynamic property updates
  - Custom property types
  - Metadata support

### ⚡ Transforms

Transforms are automated operations that process entities to discover new information and relationships:

- **Operation Types**
  - 🔍 Discovery: Find new entities from existing ones
  - 🔗 Correlation: Connect related entities
  - 📊 Analysis: Extract insights from entity data
  - 🌐 OSINT: Gather open-source intelligence
  - 🔄 Enrichment: Add data to existing entities

- **Features**
  - Async operation support
  - Progress tracking
  - Error handling
  - Rate limiting
  - Result validation

### 🛠️ Helpers

Helpers are specialized tools with dedicated UIs for specific investigation tasks:

- **Available Helpers**
  - 🔍 Cross-Examination: Analyze statements and testimonies
  - 👤 Portrait Creator: Generate facial composites
  - 📊 Data Analyzer: Find patterns in investigation data
  - 🌍 Location Mapper: Advanced geographic analysis
  - 📅 Timeline Builder: Create and analyze event sequences

- **Helper Features**
  - Custom Qt interfaces
  - Real-time updates
  - Graph integration
  - Data visualization
  - Export capabilities

## 👥 Contributing

We welcome contributions! To contribute to PANO:

1. Fork the repository at https://github.com/ALW1EZ/PANO/
2. Make your changes in your fork
3. Test your changes thoroughly
4. Create a Pull Request to our main branch
5. In your PR description, include:
   - What the changes do
   - Why you made these changes
   - Any testing you've done
   - Screenshots if applicable

> **Note**: We use a single `main` branch for development. All pull requests should be made directly to `main`.

## 📖 Development Guide

<details>
<summary>Click to expand development documentation</summary>

### System Requirements

- Operating System: Windows or Linux
- Python 3.11+
- PySide6 for GUI
- Internet connection for online features

### Custom Entities

Entities are the core data structures in PANO. Each entity represents a piece of information with specific properties and behaviors. To create a custom entity:

1. Create a new file in the `entities` folder (e.g., `entities/phone_number.py`)
2. Implement your entity class:

```python
from dataclasses import dataclass
from typing import ClassVar, Dict, Any
from .base import Entity

@dataclass
class PhoneNumber(Entity):
    name: ClassVar[str] = "Phone Number"
    description: ClassVar[str] = "A phone number entity with country code and validation"
    
    def init_properties(self):
        """Initialize phone number properties"""
        self.setup_properties({
            "number": str,
            "country_code": str,
            "carrier": str,
            "type": str,  # mobile, landline, etc.
            "verified": bool
        })
    
    def update_label(self):
        """Update the display label"""
        self.label = self.format_label(["country_code", "number"])
```

### Custom Transforms

Transforms are operations that process entities and generate new insights or relationships. To create a custom transform:

1. Create a new file in the `transforms` folder (e.g., `transforms/phone_lookup.py`)
2. Implement your transform class:

```python
from dataclasses import dataclass
from typing import ClassVar, List
from .base import Transform
from entities.base import Entity
from entities.phone_number import PhoneNumber
from entities.location import Location
from ui.managers.status_manager import StatusManager

@dataclass
class PhoneLookup(Transform):
    name: ClassVar[str] = "Phone Number Lookup"
    description: ClassVar[str] = "Lookup phone number details and location"
    input_types: ClassVar[List[str]] = ["PhoneNumber"]
    output_types: ClassVar[List[str]] = ["Location"]
    
    async def run(self, entity: PhoneNumber, graph) -> List[Entity]:
        if not isinstance(entity, PhoneNumber):
            return []
            
        status = StatusManager.get()
        operation_id = status.start_loading("Phone Lookup")
        
        try:
            # Your phone number lookup logic here
            # Example: query an API for phone number details
            location = Location(properties={
                "country": "Example Country",
                "region": "Example Region",
                "carrier": "Example Carrier",
                "source": "PhoneLookup transform"
            })
            
            return [location]
            
        except Exception as e:
            status.set_text(f"Error during phone lookup: {str(e)}")
            return []
            
        finally:
            status.stop_loading(operation_id)
```

### Custom Helpers

Helpers are specialized tools that provide additional investigation capabilities through a dedicated UI interface. To create a custom helper:

1. Create a new file in the `helpers` folder (e.g., `helpers/data_analyzer.py`)
2. Implement your helper class:

```python
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QComboBox
)
from .base import BaseHelper
from qasync import asyncSlot

class DataAnalyzer(BaseHelper):
    """A helper for analyzing investigation data patterns"""
    
    name = "Data Analyzer"
    description = "Analyze patterns and correlations in investigation data"
    
    def __init__(self, graph_manager=None, parent=None):
        super().__init__(graph_manager, parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the helper's user interface"""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        
        # Analysis options
        options_layout = QHBoxLayout()
        
        # Analysis type selector
        self.analysis_type = QComboBox()
        self.analysis_type.addItems([
            "Temporal Patterns",
            "Location Clusters",
            "Connection Analysis"
        ])
        options_layout.addWidget(QLabel("Analysis Type:"))
        options_layout.addWidget(self.analysis_type)
        
        # Add analyze button
        analyze_btn = QPushButton("Analyze")
        analyze_btn.clicked.connect(self.analyze_data)
        options_layout.addWidget(analyze_btn)
        
        self.main_layout.addLayout(options_layout)
        
        # Results area
        self.results_area = QTextEdit()
        self.results_area.setReadOnly(True)
        self.results_area.setPlaceholderText("Analysis results will appear here...")
        self.main_layout.addWidget(self.results_area)
        
        # Set helper window properties
        self.setWindowTitle(self.name)
        self.resize(800, 600)
    
    @asyncSlot()
    async def analyze_data(self):
        """Perform the selected analysis on investigation data"""
        analysis_type = self.analysis_type.currentText()
        
        if not self.graph_manager:
            self.results_area.setText("No investigation data available")
            return
            
        try:
            # Get all nodes from the graph
            nodes = self.graph_manager.nodes.values()
            
            # Perform analysis based on selected type
            if analysis_type == "Temporal Patterns":
                results = self._analyze_temporal_patterns(nodes)
            elif analysis_type == "Location Clusters":
                results = self._analyze_location_clusters(nodes)
            else:
                results = self._analyze_connections(nodes)
                
            # Display results
            self.results_area.setText(results)
            
        except Exception as e:
            self.results_area.setText(f"Analysis failed: {str(e)}")
    
    def _analyze_temporal_patterns(self, nodes):
        """Analyze temporal patterns in the data"""
        # Your temporal analysis logic here
        return "Temporal analysis results..."
    
    def _analyze_location_clusters(self, nodes):
        """Analyze location clusters in the data"""
        # Your location clustering logic here
        return "Location cluster analysis results..."
    
    def _analyze_connections(self, nodes):
        """Analyze connection patterns in the data"""
        # Your connection analysis logic here
        return "Connection analysis results..."
```
</details>

## 📄 License

This project is licensed under the Creative Commons Attribution-NonCommercial (CC BY-NC) License.

**You are free to:**
- ✅ Share: Copy and redistribute the material
- ✅ Adapt: Remix, transform, and build upon the material

**Under these terms:**
- ℹ️ Attribution: You must give appropriate credit
- 🚫 NonCommercial: No commercial use
- 🔓 No additional restrictions

## 🙏 Acknowledgments

Special thanks to all library authors and contributors who made this project possible.

## 👨‍💻 Author

Created by ALW1EZ