from PyQt6.QtGui import QColor

class TimelineStyle:
    # Colors
    BACKGROUND_COLOR = QColor("#1e1e1e")
    TIMELINE_COLOR = QColor("#404040")
    TEXT_COLOR = QColor("#ffffff")
    EVENT_FILL_COLOR = QColor("#2d2d2d")
    DEFAULT_EVENT_COLOR = QColor("#0078d4")
    
    # Dimensions
    LEFT_MARGIN = 90
    TOP_MARGIN = 50
    BOX_WIDTH = 250
    COLUMN_SPACING = 10
    CONNECTOR_LENGTH = 30
    MIN_LABEL_SPACING = 25
    CONTENT_MARGIN = 10
    TITLE_HEIGHT = 30
    DESC_MIN_HEIGHT = 25
    DURATION_HEIGHT = 25
    
    # Widget dimensions
    MINIMUM_DOCK_WIDTH = 400
    PREFERRED_DOCK_WIDTH = 800
    
    # Zoom settings
    MIN_PIXELS_PER_HOUR = 0.1
    MAX_PIXELS_PER_HOUR = 7200
    ZOOM_IN_FACTOR = 1.1
    ZOOM_OUT_FACTOR = 0.9
    BASE_PIXELS_PER_HOUR = 20

    # Style sheets
    MAIN_STYLE = """
        QMainWindow, QWidget {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QPushButton {
            background-color: #3d3d3d;
            border: none;
            padding: 8px;
            color: white;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #3d3d3d;
        }
        QScrollArea {
            border: none;
        }
    """

    DIALOG_STYLE = """
        QDialog {
            background-color: #1e1e1e;
            color: white;
        }
        QLabel {
            color: white;
        }
        QPushButton {
            background-color: #0078d4;
            color: white;
            border: none;
            padding: 5px;
            border-radius: 3px;
            margin: 2px;
        }
        QPushButton:hover {
            background-color: #1084d8;
        }
        QPushButton[text="Delete Event"] {
            background-color: #d42828;
        }
        QPushButton[text="Delete Event"]:hover {
            background-color: #e13232;
        }
        QLineEdit, QDateTimeEdit {
            background-color: #2d2d2d;
            color: white;
            border: 1px solid #404040;
            padding: 5px;
            border-radius: 3px;
        }
    """

    DATETIME_STYLE = """
        QDateTimeEdit {
            padding: 5px;
            border-radius: 4px;
        }
        QDateTimeEdit::drop-down {
            border: none;
            width: 20px;
        }
        QDateTimeEdit::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid white;
        }
    """ 