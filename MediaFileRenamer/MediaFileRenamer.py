import sys
import os
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QCheckBox
)
from PyQt5.QtCore import Qt

def clean_filename(filename):
    name, ext = os.path.splitext(filename)

    # Replace dots with spaces
    name = name.replace('.', ' ')

    # Replace underscores with spaces
    name = name.replace('_', ' ')

    # Extract season/episode pattern like S01E01 or S01E01E02
    match = re.search(r'(S\d{2}E\d{2}(?:E\d{2})?)', name, re.IGNORECASE)
    season_episode = match.group(1) if match else ""

    # Extract resolution (720p, 1080p, etc.)
    res_match = re.search(r'(\d{3,4}p)', name, re.IGNORECASE)
    resolution = res_match.group(1) if res_match else ""

    # Extract title (everything else before S##E##)
    title = name.split(season_episode)[0].strip()

    # Clean extra spaces
    title = re.sub(r'\s+', ' ', title)

    # Build new filename
    new_name = f"{title} {season_episode} - {resolution}{ext}"

    return new_name.strip()

class RenamerApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Batch Renamer")
        self.setGeometry(100, 100, 500, 400)

        layout = QVBoxLayout()

        self.label = QLabel("Drag & drop a folder here")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("border: 2px dashed gray; padding: 20px;")

        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Original Name", "New Name"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.doubleClicked)

        # DRY RUN checkbox
        self.dry_run_checkbox = QCheckBox("Dry Run (preview only)")
        self.dry_run_checkbox.setChecked(True)

        self.rename_button = QPushButton("Rename Files")
        self.rename_button.clicked.connect(self.rename_files)

        # Create layout
        layout.addWidget(self.label)
        layout.addWidget(self.table)
        layout.addWidget(self.dry_run_checkbox)
        layout.addWidget(self.rename_button)

        self.setLayout(layout)

        self.setAcceptDrops(True)
        self.folder = None

    # Drag and drop
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()

            if os.path.isdir(path):
                self.folder = path
                self.load_files()
    
    # Load files into table
    def load_files(self):
        self.table.setRowCount(0)

        for file in os.listdir(self.folder):
            if not file.lower().endswith(('.mkv', '.mp4', '.avi')):
                continue

            new_name = clean_filename(file)

            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(file))
            self.table.setItem(row, 1, QTableWidgetItem(new_name))

    # Rename logic
    def rename_files(self):
        if not self.folder:
            return

        dry_run = self.dry_run_checkbox.isChecked()

        for row in range(self.table.rowCount()):
            old_name = self.table.item(row, 0).text()
            new_name = self.table.item(row, 1).text()

            old_path = os.path.join(self.folder, old_name)
            new_path = os.path.join(self.folder, new_name)

            if old_name == new_name:
                continue

            if os.path.exists(new_path):
                print(f"Skipping (exists): {new_name}")
                continue

            if dry_run:
                print(f"[DRY RUN] {old_name} -> {new_name}")
            else:
                os.rename(old_path, new_path)

        # Refresh after rename
        if not dry_run:
            self.load_files()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RenamerApp()
    window.show()
    sys.exit(app.exec_())
