class MapStyles:
    DIALOG = """
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QListWidget {
                background-color: #2d2d2d;
                border: 1px solid #555555;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #3d3d3d;
            }
            QListWidget::item:hover {
                background-color: #353535;
            }
            QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                color: #ffffff;
                min-width: 80px;
                height: 24px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
    """

    SEARCH_CONTROLS = """
        QLineEdit {
            background-color: #3d3d3d;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 5px;
            color: #ffffff;
            height: 24px;
        }
        QLineEdit:focus {
            border: 1px solid #777777;
        }
        QPushButton {
            background-color: #3d3d3d;
            border: none;
            border-radius: 4px;
            padding: 5px 10px;
            color: #ffffff;
            min-width: 68px;
            height: 24px;
        }
        QPushButton:hover {
            background-color: #4d4d4d;
        }
    """

    TOOL_BUTTON = """
        QToolButton {
            background-color: #3d3d3d;
            border: none;
            border-radius: 4px;
            padding: 5px;
            color: #ffffff;
            min-width: 24px;
            height: 24px;
        }
        QToolButton:hover {
            background-color: #4d4d4d;
        }
        QToolButton::menu-indicator {
            image: none;
        }
    """

    MENU = """
        QMenu {
            background-color: #2d2d2d;
            border: 1px solid #555555;
            color: #ffffff;
            padding: 5px;
        }
        QMenu::item {
            padding: 5px 25px;
            border-radius: 3px;
        }
        QMenu::item:selected {
            background-color: #3d3d3d;
        }
    """

    CHECKBOX = """
        QCheckBox {
            color: white;
            background: transparent;
            padding: 8px;
            font-size: 13px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
        QCheckBox::indicator:unchecked {
            background-color: #2d2d2d;
            border: 1px solid #555555;
            border-radius: 3px;
        }
        QCheckBox::indicator:checked {
            background-color: #3d3d3d;
            border: 1px solid #777777;
            border-radius: 3px;
        }
    """ 