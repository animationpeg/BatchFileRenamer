from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QCheckBox, QLineEdit,
    QAbstractItemView, QScrollArea
)
from PyQt5.QtCore import Qt
from _pytest.monkeypatch import K
from engine import get_all_tokens, process_files, rename_files, get_default_template, detect_pattern
import os

from rules import extract_tokens


class RenamerApp(QWidget):


    def __init__(self):
        super().__init__()

        self.folder = None

        # Available Tokens
        self.available_tokens = [
            "title",
            "season",
            "episode",
            "episode2",
            "episode_title",
            "resolution",
            "year",
            "edition",
            "index"
        ]

        # Define the window
        window_width = 800
        self.setWindowTitle("Batch Renamer")
        self.setGeometry(100, 100, window_width, 500)

        # Layout
        main_layout = QHBoxLayout()
        # Left Side: token controls
        self.token_panel = QVBoxLayout()
        token_widget = QWidget()
        token_widget.setLayout(self.token_panel)
        # Right Side: file naming
        right_layout = QVBoxLayout()

        # Input text box for the renaming template
        self.template_input = QLineEdit()
        self.template_input.setPlaceholderText("Enter new naming convention here")
        self.template_input.textChanged.connect(self.update_preview_files)

        # The table
        self.label = DropLabel(self.load_folder, self)
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setColumnWidth(0, int(window_width / 2 - 20))
        self.table.setColumnWidth(1, int(window_width / 2 - 20))
        self.table.setHorizontalHeaderLabels(["Original", "New"])
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)

        # Dry run Checkbox
        self.dry_run_checkbox = QCheckBox("Dry run (preview only)")
        self.dry_run_checkbox.setChecked(True)

        # Rename button to commence the batch renaming
        self.rename_button = QPushButton("Rename")
        self.rename_button.clicked.connect(self.rename_files)

        # -----------------
        # Build the layout
        # -----------------
        # Add all the RIGHT SIDE widgets
        right_layout.addWidget(self.label)
        right_layout.addWidget(QLabel("Template"))
        right_layout.addWidget(self.template_input)
        right_layout.addWidget(self.table)
        right_layout.addWidget(self.dry_run_checkbox)
        right_layout.addWidget(self.rename_button)


        # Scroll box for Token widget
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(token_widget)

        # Dynamically build all the LEFT SIDE rows
        self.token_panel.addWidget(QLabel("Tokens"))
        self.token_inputs = {}
        for token in self.available_tokens:
            row = QHBoxLayout()

            label = QLabel(token)
            input_field = QLineEdit()
            button = QPushButton("+")
            button.setFixedWidth(30)

            # Store input for later use
            self.token_inputs[token] = input_field

            # Button inserts token into template
            button.clicked.connect(lambda _, t=token: self.insert_token(t))

            # Add row to the layout
            row.addWidget(label)
            row.addWidget(input_field)
            row.addWidget(button)

            self.token_panel.addLayout(row)
        self.token_panel.addStretch()

        # Add LEFT and RIGHT side panels to main layout
        main_layout.addWidget(scroll, 1) # Left, (narrow)
        main_layout.addLayout(right_layout, 3)     # Right, (wide)

        self.setLayout(main_layout)
        self.setAcceptDrops(True)
    # -------------------------
    # Insert token text into template field
    # -------------------------
    def populate_token_input_fields(self):
        if not hasattr(self, "files") or not self.files:
            return
        sample_tokens = extract_tokens(self.files[0], index=1)

        for key, input_field in self.token_inputs.items(): # Check every input field of the token_panel widget
            value = sample_tokens.get(key, "")
            input_field.setText(value)
    # -------------------------
    # Highlight token fields with found tokens
    # -------------------------
    def highlight_token_input_fields(self):
        if not hasattr(self, "files") or not self.files:
            return
        sample_tokens = extract_tokens(self.files[0], index=1)

        for key, input_field in self.token_inputs.items():
            if sample_tokens.get(key):
                input_field.setStyleSheet("background-color: #e6ffe6;") # Light green
            else:
                input_field.setStyleSheet("background-color: #f0f0f0;") # Grey
    # -------------------------
    # Function to insert token text into template field
    # -------------------------
    def insert_token(self, token):
        current = self.template_input.text()
        self.template_input.setText(current + f"{{{token}}}")
    # -------------------------
    # Load Files
    # -------------------------
    def load_files(self):
        self.files = [
            f for f in os.listdir(self.folder)
            if f.lower().endswith((".mp4", ".m4v", ".mkv", ".avi", ".png", ".jpg"))
        ]

        pattern = detect_pattern(self.files)
        self.pattern = pattern

        if not self.template_input.text().strip():
            template = get_default_template(pattern)
            self.template_input.setText(template)

        self.populate_token_input_fields()
        self.highlight_token_input_fields()
        self.update_preview_files()
    # -------------------------
    # Update Preview Files
    # -------------------------
    def update_preview_files(self):
        if not self.folder or not hasattr(self, "files"):
            return

        template = self.template_input.text()
        results = process_files(self.files, template)

        self.table.setRowCount(0)

        for old, new in results:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(old))
            self.table.setItem(row, 1, QTableWidgetItem(new))
    # -------------------------
    # Apply rename
    # -------------------------
    def rename_files(self):
        from engine import rename_files

        mappings = []

        for row in range(self.table.rowCount()):
            old = self.table.item(row, 0).text()
            new = self.table.item(row, 1).text()
            mappings.append((old, new))

        rename_files(
            self.folder,
            mappings,
            dry_run=self.dry_run_checkbox.isChecked()
        )

    def load_folder(self, path):
        if os.path.isdir(path):
            self.folder = path
            self.load_files()
            return True
        return False


class DropLabel(QLabel):
    def __init__(self, drop_callback, parent=None):
        super().__init__(parent)
        self.drop_callback = drop_callback
        self.setText("Drag & drop a folder here")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            border: 2px dashed gray;
            padding: 20px;
            font-size: 14px;
        """)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        self.setStyleSheet("border: 2px dashed blue; padding: 20px; font-size: 14px;")
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    def dragLeaveEvent(self, event):
        self.setStyleSheet("border: 2px dashed gray; padding: 20px; font-size: 14px;")
        event.accept()

    def dropEvent(self, event):
        urls = event.mimeData().urls()

        self.setStyleSheet("border: 2px dashed gray; padding: 20px; font-size: 14px;")

        if not urls:
            return

        path = urls[0].toLocalFile()

        if os.path.isdir(path):
            self.drop_callback(path)

        event.acceptProposedAction()

    