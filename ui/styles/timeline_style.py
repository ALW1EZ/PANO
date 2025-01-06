from PyQt6.QtGui import QColor

class TimelineStyle:
    # Colors
    BACKGROUND_COLOR = QColor("#1e1e1e")
    TIMELINE_COLOR = QColor("#404040")
    TEXT_COLOR = QColor("#ffffff")
    EVENT_FILL_COLOR = QColor("#2d2d2d")
    DEFAULT_EVENT_COLOR = QColor("#0078d4")
    
    # Timeline dimensions
    LEFT_MARGIN = 145
    TOP_MARGIN = 50
    BOX_WIDTH = 250
    EVENT_SPACING = 50
    BOX_HEIGHT = 100
    CONTENT_MARGIN = 10
    
    # Widget dimensions
    MINIMUM_DOCK_WIDTH = 420
    PREFERRED_DOCK_WIDTH = 320

    # Style sheets
    MAIN_STYLE = """
        QMainWindow, QWidget {
            background-color: #1e1e1e;
            color: #ffffff;
            font-family: "Geist Mono";
            font-size: 12px;
        }
        QPushButton {
            background-color: #3d3d3d;
            border: none;
            padding: 8px;
            color: white;
            border-radius: 4px;
            font-family: "Geist Mono";
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #4d4d4d;
        }
        QScrollArea {
            border: none;
        }
    """

    DIALOG_STYLE = """
        QDialog {
            background-color: #1e1e1e;
            color: white;
            font-family: "Geist Mono";
            font-size: 12px;
        }
        QLabel {
            color: white;
            font-family: "Geist Mono";
            font-size: 12px;
        }
        QPushButton {
            background-color: #0078d4;
            color: white;
            border: none;
            padding: 5px;
            border-radius: 3px;
            margin: 2px;
            font-family: "Geist Mono";
            font-size: 12px;
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
            font-family: "Geist Mono";
            font-size: 12px;
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