from PySide6.QtWidgets import (
    QLineEdit, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QSplitter, QCheckBox, QComboBox, QWidget,
    QTreeWidget, QTreeWidgetItem, QFrame, QDialog, QListWidget,
    QListWidgetItem, QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QTextCharFormat, QColor, QSyntaxHighlighter
import g4f
from googletrans import Translator
from .base import BaseHelper
from qasync import asyncSlot
import json
from datetime import datetime
import markdown2

class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.styles = {
            'header': self.format_style('#2196F3', True),  # Material Blue
            'bullet': self.format_style('#4CAF50', True),  # Material Green
            'emphasis': self.format_style('#FFC107', True, italic=True),  # Material Yellow
            'code': self.format_style('#FF5722', False, background='#1E1E1E'),  # Material Deep Orange
            'link': self.format_style('#9C27B0', False, underline=True),  # Material Purple
        }

    def format_style(self, color, bold=False, italic=False, background=None, underline=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if background:
            fmt.setBackground(QColor(background))
        fmt.setFontWeight(700 if bold else 400)
        fmt.setFontItalic(italic)
        if underline:
            fmt.setFontUnderline(True)
        return fmt

    def highlightBlock(self, text):
        # Headers
        for match in text.split('\n'):
            if match.startswith('##'):
                self.setFormat(0, len(match), self.styles['header'])
        
        # Bullet points
        if text.strip().startswith('*'):
            self.setFormat(0, len(text), self.styles['bullet'])
        
        # Emphasis (between asterisks)
        start = 0
        while True:
            start = text.find('*', start)
            if start == -1:
                break
            end = text.find('*', start + 1)
            if end == -1:
                break
            self.setFormat(start, end - start + 1, self.styles['emphasis'])
            start = end + 1

        # Code blocks
        start = 0
        while True:
            start = text.find('`', start)
            if start == -1:
                break
            end = text.find('`', start + 1)
            if end == -1:
                break
            self.setFormat(start, end - start + 1, self.styles['code'])
            start = end + 1

        # Links
        start = 0
        while True:
            start = text.find('[', start)
            if start == -1:
                break
            end = text.find(')', start)
            if end == -1:
                break
            self.setFormat(start, end - start + 1, self.styles['link'])
            start = end + 1

class MarkdownTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.highlighter = MarkdownHighlighter(self.document())
        
        # Set dark theme styles
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: none;
                padding: 12px;
                font-family: 'Geist Mono', 'JetBrains Mono', monospace;
                font-size: 14px;
                line-height: 1.6;
            }
            QScrollBar:vertical {
                background: #1e1e1e;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background: #363636;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #404040;
            }
        """)

    def setMarkdownText(self, text):
        # Convert markdown to HTML
        html = markdown2.markdown(text, extras=['fenced-code-blocks', 'tables'])
        
        # Add custom CSS
        styled_html = f"""
        <style>
            body {{ 
                color: #e0e0e0;
                font-family: 'Geist Mono', 'JetBrains Mono', monospace;
                line-height: 1.6;
                font-size: 15px;
                background-color: #1e1e1e;
            }}
            h2 {{ 
                color: #2196F3;
                font-size: 1.5em;
                margin-top: 28px;
                margin-bottom: 16px;
                font-weight: 600;
            }}
            ul {{ 
                margin-left: 20px;
                margin-bottom: 16px;
                font-size: 15px;
            }}
            li {{ 
                color: #e0e0e0;
                margin: 10px 0;
                font-size: 15px !important;
            }}
            li::marker {{
                color: #90CAF9;
                font-weight: bold;
                font-size: 15px;
            }}
            li > ul > li {{
                font-size: 15px !important;
            }}
            li > ul > li::marker {{
                font-size: 15px;
            }}
            code {{ 
                background-color: #2b2b2b;
                color: #e0e0e0;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: inherit;
            }}
            em {{ 
                color: #90CAF9;
                font-style: italic;
            }}
            strong {{ 
                color: #90CAF9;
                font-weight: 600;
            }}
            p {{
                margin: 12px 0;
                font-size: 15px;
            }}
        </style>
        {html}
        """
        
        self.setHtml(styled_html)

class EntitySelectDialog(QDialog):
    def __init__(self, graph_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Entities")
        self.setModal(True)
        
        # Setup layout
        layout = QVBoxLayout(self)
        
        # Create entity list
        self.entity_list = QListWidget()
        self.entity_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.entity_list)
        
        # Populate entities from graph
        for node in graph_manager.nodes.values():
            item = QListWidgetItem(node.node.label)
            item.setData(Qt.ItemDataRole.UserRole, node.node)
            self.entity_list.addItem(item)
        
        # Add buttons
        button_layout = QHBoxLayout()
        select_btn = QPushButton("Select")
        select_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(select_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.resize(400, 500)
    
    def get_selected_entities(self):
        """Get the selected entities"""
        return [
            self.entity_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.entity_list.count())
            if self.entity_list.item(i).isSelected()
        ]

class StatementWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Statement text
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Enter statement...")
        self.text_edit.setMaximumHeight(100)
        layout.addWidget(self.text_edit)

    def get_statement(self):
        """Get the statement text"""
        return self.text_edit.toPlainText().strip()

class EntityStatementItem(QTreeWidgetItem):
    def __init__(self, parent=None, entity=None):
        super().__init__(parent)
        self.setExpanded(True)
        
        # Create widget for the statement
        self.statement_widget = StatementWidget()
        self.treeWidget().setItemWidget(self, 1, self.statement_widget)
        
        # Set entity name editable
        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsEditable)
        
        # Set entity data if provided
        if entity:
            self.setText(0, entity.label)
            self.setData(0, Qt.ItemDataRole.UserRole, entity)
        else:
            self.setText(0, "New Entity")

class CrossExaminationHelper(BaseHelper):
    name = "Cross-Examination Assistant"
    description = "AI-powered analysis for testimony cross-examination and information gathering"
    
    LANGUAGES = {
        "English": "en",
        "Turkish": "tr",
        "German": "de",
        "Russian": "ru",
        "French": "fr",
        "Spanish": "es",
        "Italian": "it",
        "Japanese": "ja",
        "Chinese": "zh",
        "Arabic": "ar"
    }
    
    def setup_ui(self):
        """Setup the cross-examination UI"""
        # Create translator instance
        self.translator = Translator()
        
        # Create main horizontal splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Entity statements
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Entity tree
        self.entity_tree = QTreeWidget()
        self.entity_tree.setHeaderLabels(["Entity", "Statement"])
        self.entity_tree.setColumnWidth(0, 150)
        left_layout.addWidget(self.entity_tree)
        
        # Entity controls
        entity_controls = QHBoxLayout()
        
        # Add entity button
        add_entity_btn = QPushButton("+")
        add_entity_btn.setToolTip("Add new entity")
        add_entity_btn.clicked.connect(self.add_entity)
        
        # Select from graph button
        select_entities_btn = QPushButton("Select from Graph")
        select_entities_btn.clicked.connect(self.select_entities)
        
        # Remove entity button
        remove_entity_btn = QPushButton("-")
        remove_entity_btn.setToolTip("Remove selected entity")
        remove_entity_btn.clicked.connect(self.remove_entity)
        
        entity_controls.addWidget(add_entity_btn)
        entity_controls.addWidget(select_entities_btn)
        entity_controls.addWidget(remove_entity_btn)
        entity_controls.addStretch()
        left_layout.addLayout(entity_controls)
        
        # Right side - AI Analysis
        self.analysis_output = MarkdownTextEdit()
        self.analysis_output.setPlaceholderText("AI analysis will appear here...")
        
        # Add widgets to splitter
        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(self.analysis_output)
        
        # Set initial sizes (50-50 split)
        self.splitter.setSizes([500, 500])
        
        # Create controls layout
        controls_layout = QHBoxLayout()
        
        # Add language selection
        lang_layout = QHBoxLayout()
        lang_label = QLabel("Response Language:")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(self.LANGUAGES.keys())
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_combo)
        controls_layout.addLayout(lang_layout)
        
        # Add consider graph state checkbox
        self.consider_graph = QCheckBox("Consider existing investigation data")
        self.consider_graph.setChecked(True)
        self.consider_graph.setToolTip("Include existing entities, relationships, and timeline in the analysis")
        controls_layout.addWidget(self.consider_graph)
        
        # Create analyze button
        analyze_button = QPushButton("Analyze Statements")
        analyze_button.clicked.connect(self.analyze_testimony)
        controls_layout.addWidget(analyze_button)
        
        # Add to main layout
        self.main_layout.addWidget(self.splitter)
        self.main_layout.addLayout(controls_layout)
        
        # Set dialog size
        self.resize(1200, 800)

    def select_entities(self):
        """Open dialog to select entities from the graph"""
        dialog = EntitySelectDialog(self.graph_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_entities = dialog.get_selected_entities()
            for entity in selected_entities:
                item = EntityStatementItem(self.entity_tree, entity)
    
    def add_entity(self):
        """Add a new entity item to the tree"""
        item = EntityStatementItem(self.entity_tree)
        self.entity_tree.setCurrentItem(item)
        self.entity_tree.editItem(item, 0)
    
    def remove_entity(self):
        """Remove the selected entity from the tree"""
        current = self.entity_tree.currentItem()
        if current:
            self.entity_tree.takeTopLevelItem(self.entity_tree.indexOfTopLevelItem(current))
    
    def collect_statements(self):
        """Collect all entity statements with metadata"""
        statements = []
        for i in range(self.entity_tree.topLevelItemCount()):
            item = self.entity_tree.topLevelItem(i)
            statement_widget = self.entity_tree.itemWidget(item, 1)
            
            if isinstance(statement_widget, StatementWidget):
                # Get entity data
                entity = item.data(0, Qt.ItemDataRole.UserRole)
                entity_name = entity.label if entity else item.text(0)
                statement_text = statement_widget.get_statement()
                
                if statement_text:  # Only add if there's a statement
                    statements.append({
                        "entity": entity_name,
                        "statement": statement_text,
                        "entity_data": entity
                    })
        
        return statements

    @asyncSlot()
    async def analyze_testimony(self):
        """Analyze all entity statements using AI"""
        statements = self.collect_statements()
        if not statements:
            self.analysis_output.clear()
            return
            
        try:
            # Base prompt
            system_prompt = """You are an expert investigator and interrogator analyzing statements in the context of an ongoing investigation. Your role is to perform deep analysis of the provided statements and identify strategic questions that could reveal critical information.

Key Analysis Principles:
1. ASSUME ALL BASIC INFORMATION IS INTENTIONALLY PROVIDED - Do not ask for clarification of details that are explicitly stated
2. FOCUS ON DEEPER ANALYSIS - Look for psychological indicators, deception markers, and logical inconsistencies
3. CROSS-REFERENCE EVERYTHING - Compare statements with known facts and other statements
4. ANALYZE PRECISION OF LANGUAGE - Pay attention to specific word choices and phrasing
5. IDENTIFY PATTERNS - Look for behavioral and linguistic patterns across statements

When analyzing statements, focus on:
1. CREDIBILITY ANALYSIS:
   - Internal consistency within each statement
   - Consistency with known facts and timeline
   - Presence of verifiable details vs vague statements
   - Signs of deception or truthfulness in language patterns

2. BEHAVIORAL ANALYSIS:
   - Psychological state indicators
   - Motivation analysis
   - Response patterns
   - Signs of stress or comfort in specific topics

3. RELATIONSHIP DYNAMICS:
   - Power dynamics between entities
   - Conflicting interests
   - Alliance patterns
   - Information sharing patterns

4. TIMELINE ANALYSIS:
   - Sequence consistency
   - Time gaps significance
   - Pattern of events
   - Temporal relationships between statements

5. STRATEGIC INSIGHTS:
   - Key points of leverage
   - Critical inconsistencies
   - Significant patterns
   - Investigation priorities

Format your response in these sections:

CREDIBILITY ASSESSMENT:
- Detailed analysis of statement reliability
- Consistency evaluation
- Truth indicators and deception markers

BEHAVIORAL INSIGHTS:
- Psychological state analysis
- Motivation assessment
- Pattern recognition

RELATIONSHIP ANALYSIS:
- Entity interaction patterns
- Power dynamics
- Information flow analysis

CRITICAL FINDINGS:
- Key inconsistencies
- Significant patterns
- Important revelations

STRATEGIC RECOMMENDATIONS:
- Investigation priorities
- Key areas requiring verification
- Tactical approaches for information gathering

STRATEGIC QUESTIONS:
- Questions designed to reveal deception
- Questions to explore inconsistencies
- Questions to fill critical information gaps
- Questions to verify suspected relationships
- Questions to test alternative scenarios

Remember: 
1. Focus on analyzing what is known rather than seeking basic clarifications
2. When you identify gaps, explain their significance and provide strategic questions to address them
3. Questions should be tactical and designed to reveal deeper truths, not just gather basic facts
4. Each question should have a clear strategic purpose explained
5. Questions should be ordered by priority and potential impact

Use markdown formatting for your response.
"""

            # Add graph state if enabled
            if self.consider_graph.isChecked():
                graph_state = self.get_graph_state()
                if graph_state["entities"] or graph_state["relationships"] or graph_state["timeline_events"]:
                    system_prompt += "\n\nCurrent Investigation Context:\n"
                    system_prompt += json.dumps(graph_state, indent=2)
                    system_prompt += "\n\nIntegrate this context in your analysis:"
                    system_prompt += "\n1. How new statements support or contradict existing evidence"
                    system_prompt += "\n2. How relationships in statements align with known connections"
                    system_prompt += "\n3. How timeline elements fit with established chronology"
                    system_prompt += "\n4. How behavioral patterns match known entity profiles"
                    system_prompt += "\n5. How new information affects overall investigation landscape"

            # Format statements for AI
            statements_text = "\n\n".join([
                f"Entity: {s['entity']}\nStatement: {s['statement']}"
                for s in statements
            ])

            # Get AI analysis in English
            response = await g4f.ChatCompletion.create_async(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": statements_text}
                ]
            )
            
            # Translate if not English
            target_lang = self.LANGUAGES[self.lang_combo.currentText()]
            if target_lang != "en":
                try:
                    # Get target language code
                    translation = await self.translator.translate(
                        response,
                        dest=target_lang
                    )
                    response = translation.text
                except Exception as e:
                    response += f"\n\n**Translation Error:** {str(e)}"
            
            self.analysis_output.setMarkdownText(response)
            
        except Exception as e:
            self.analysis_output.setMarkdownText(f"**Analysis Error:** {str(e)}")

    def get_graph_state(self):
        """Get the current state of the investigation graph"""
        if not self.graph_manager:
            return {}
            
        graph_state = {
            "entities": [],
            "relationships": [],
            "timeline_events": []
        }
        
        def serialize_value(value):
            """Helper function to serialize any value"""
            if value is None or value == "":
                return None
            if isinstance(value, (int, float, bool, str)):
                return value
            try:
                return str(value)
            except:
                return None
        
        # Collect entities with their properties
        for node in self.graph_manager.nodes.values():
            try:
                # Convert properties to serializable format
                serializable_props = {}
                for key, value in node.node.properties.items():
                    serialized = serialize_value(value)
                    if serialized is not None:
                        serializable_props[key] = serialized
                
                # Create entity info with serialized values
                entity_info = {
                    "type": serialize_value(node.node.type),
                    "label": serialize_value(node.node.label),
                    "properties": serializable_props
                }
                graph_state["entities"].append(entity_info)
            except Exception as e:
                continue  # Skip problematic entities
        
        # Collect relationships
        for edge in self.graph_manager.edges:
            try:
                # Get source and target nodes
                source_node = edge.source_node if hasattr(edge, 'source_node') else None
                target_node = edge.target_node if hasattr(edge, 'target_node') else None
                
                # If direct access fails, try through visual nodes
                if not source_node and hasattr(edge, 'source'):
                    source_node = edge.source.node if hasattr(edge.source, 'node') else None
                if not target_node and hasattr(edge, 'target'):
                    target_node = edge.target.node if hasattr(edge.target, 'node') else None
                
                # Only add if we have both source and target
                if source_node and target_node:
                    rel_info = {
                        "from": serialize_value(source_node.label),
                        "to": serialize_value(target_node.label),
                        "type": serialize_value(edge.relationship_type if hasattr(edge, 'relationship_type') else "CONNECTED_TO")
                    }
                    # Only add if all values were serialized successfully
                    if all(rel_info.values()):
                        graph_state["relationships"].append(rel_info)
            except Exception:
                continue  # Skip edges with missing or invalid data
        
        # Collect timeline events if timeline manager exists
        if hasattr(self.parent(), "timeline_manager"):
            timeline = self.parent().timeline_manager
            for event in timeline.get_events():
                try:
                    event_info = {
                        "name": serialize_value(event.name),
                        "description": serialize_value(event.description) or "",
                        "start_time": event.start_time.strftime("%Y-%m-%d %H:%M") if event.start_time else None,
                        "end_time": event.end_time.strftime("%Y-%m-%d %H:%M") if event.end_time else None
                    }
                    # Only add if name was serialized successfully
                    if event_info["name"]:
                        graph_state["timeline_events"].append(event_info)
                except Exception:
                    continue  # Skip events with missing attributes
        
        return graph_state 