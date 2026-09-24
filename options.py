import os

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from qgis.gui import QgsOptionsPageWidget, QgsOptionsWidgetFactory

from .config import (
    DEVELOPER_CODE,
    DEVELOPER_MODE_KEY,
    ENABLED_KEY,
    ROOT_FOLDER_KEY,
    SETTINGS_KEY,
    get_root_folder,
    get_style_folder,
)


class DmikgAutoOptionsPage(QgsOptionsPageWidget):

    def __init__(
        self,
        parent=None,
        enabled_changed_callback=None,
        root_folder_changed_callback=None,
    ):
        super().__init__(parent)

        self.enabled_changed_callback = enabled_changed_callback
        self.root_folder_changed_callback = root_folder_changed_callback

        layout = QVBoxLayout()

        # ------------------------------------------------------------
        # Fælles DMIKG-mappe
        # ------------------------------------------------------------
        folder_group = QGroupBox("Fælles DMIKG-mappe")
        folder_layout = QVBoxLayout(folder_group)

        folder_info = QLabel(
            "Herfra findes både layer_styles og TEMPLATE_PROJECT. "
            "Skift denne mappe hvis fx F:\\GDL bliver til F:\\GRF."
        )
        folder_info.setWordWrap(True)
        folder_layout.addWidget(folder_info)

        folder_row = QHBoxLayout()
        self.root_folder_edit = QLineEdit(get_root_folder())
        self.root_folder_button = QPushButton("...")
        self.root_folder_button.setFixedWidth(38)
        self.root_folder_button.clicked.connect(self.choose_root_folder)

        folder_row.addWidget(self.root_folder_edit)
        folder_row.addWidget(self.root_folder_button)
        folder_layout.addLayout(folder_row)

        layout.addWidget(folder_group)

        # ------------------------------------------------------------
        # Automatisk styling
        # ------------------------------------------------------------
        title = QLabel("Automatiske layer styles")
        layout.addWidget(title)

        self.enabled_checkbox = QCheckBox("Automatisk styling aktiveret")
        enabled = QSettings().value(ENABLED_KEY, True, type=bool)
        self.enabled_checkbox.setChecked(enabled)
        layout.addWidget(self.enabled_checkbox)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            "Lagnavn",
            "Style-sti",
            "Status",
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(2, 110)

        self.table.cellDoubleClicked.connect(self.choose_style_file)
        self.table.itemSelectionChanged.connect(self.update_buttons)
        layout.addWidget(self.table)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Tilføj")
        self.remove_button = QPushButton("Fjern")
        self.reset_button = QPushButton("Nulstil valgt")

        self.add_button.clicked.connect(self.add_row)
        self.remove_button.clicked.connect(self.remove_row)
        self.reset_button.clicked.connect(self.reset_row)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # ------------------------------------------------------------
        # Udviklertilstand
        # ------------------------------------------------------------
        developer_group = QGroupBox("Udvikler")
        developer_layout = QVBoxLayout(developer_group)

        self.developer_checkbox = QCheckBox("Aktivér udviklertilstand")
        developer_enabled = QSettings().value(
            DEVELOPER_MODE_KEY,
            False,
            type=bool,
        )
        self.developer_checkbox.setChecked(developer_enabled)
        self.developer_checkbox.toggled.connect(self.update_developer_ui)
        developer_layout.addWidget(self.developer_checkbox)

        self.developer_info = QLabel(
            "Gemmer de aktuelle styles fra projektets lag tilbage til de "
            "tilsvarende QML-filer i den fælles layer_styles-mappe."
        )
        self.developer_info.setWordWrap(True)
        developer_layout.addWidget(self.developer_info)

        self.save_all_styles_button = QPushButton("Gem alle lagstyles")
        self.save_all_styles_button.clicked.connect(self.save_all_styles)
        developer_layout.addWidget(self.save_all_styles_button)

        layout.addWidget(developer_group)
        layout.addStretch()

        self.setLayout(layout)

        self.load_settings()
        self.update_buttons()
        self.update_developer_ui()

    def current_root_folder(self):
        return self.root_folder_edit.text().strip()

    def current_style_folder(self):
        return os.path.join(self.current_root_folder(), "layer_styles")

    def choose_root_folder(self):
        start_folder = self.current_root_folder()
        folder = QFileDialog.getExistingDirectory(
            self,
            "Vælg fælles DMIKG-mappe",
            start_folder,
        )

        if not folder:
            return

        self.root_folder_edit.setText(folder)
        self.load_settings()

    def get_standard_styles(self):
        styles = {}
        style_folder = self.current_style_folder()

        if not os.path.isdir(style_folder):
            return styles

        for filename in os.listdir(style_folder):
            if not filename.lower().endswith(".qml"):
                continue

            layer_name = os.path.splitext(filename)[0]
            styles[layer_name] = os.path.join(style_folder, filename)

        return styles

    def load_settings(self):
        settings = QSettings()
        custom_rules = settings.value(SETTINGS_KEY, [], type=list)
        standard_styles = self.get_standard_styles()

        self.table.setRowCount(0)

        for layer_name, standard_path in sorted(standard_styles.items()):
            style_path = standard_path
            status = "Standard"

            for rule in custom_rules:
                if rule.get("layer", "") == layer_name:
                    custom_path = rule.get("style", "")
                    if custom_path:
                        style_path = custom_path
                        status = "Tilpasset"
                    break

            self.add_table_row(layer_name, style_path, status)

        for rule in custom_rules:
            layer_name = rule.get("layer", "")
            style_path = rule.get("style", "")

            if not layer_name or layer_name in standard_styles:
                continue

            self.add_table_row(layer_name, style_path, "Brugerregel")

    def add_table_row(self, layer_name, style_path, status):
        row = self.table.rowCount()
        self.table.insertRow(row)

        layer_item = QTableWidgetItem(layer_name)
        style_item = QTableWidgetItem(style_path)
        status_item = QTableWidgetItem(status)

        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        if status in ("Standard", "Tilpasset"):
            layer_item.setFlags(layer_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        self.table.setItem(row, 0, layer_item)
        self.table.setItem(row, 1, style_item)
        self.table.setItem(row, 2, status_item)

    def choose_style_file(self, row, column):
        if column != 1:
            return

        status_item = self.table.item(row, 2)
        if not status_item:
            return

        current_status = status_item.text()
        current_item = self.table.item(row, 1)
        start_path = current_item.text() if current_item else self.current_style_folder()

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Vælg QGIS style",
            start_path,
            "QGIS style (*.qml)",
        )

        if not file_path:
            return

        self.table.setItem(row, 1, QTableWidgetItem(file_path))

        if current_status in ("Standard", "Tilpasset"):
            status_item.setText("Tilpasset")
        else:
            status_item.setText("Brugerregel")

        self.update_buttons()

    def add_row(self):
        self.add_table_row("", "", "Brugerregel")
        row = self.table.rowCount() - 1
        self.table.selectRow(row)
        self.update_buttons()

    def remove_row(self):
        row = self.table.currentRow()
        if row < 0:
            return

        status_item = self.table.item(row, 2)
        if not status_item or status_item.text() != "Brugerregel":
            return

        self.table.removeRow(row)
        self.update_buttons()

    def reset_row(self):
        row = self.table.currentRow()
        if row < 0:
            return

        layer_item = self.table.item(row, 0)
        status_item = self.table.item(row, 2)

        if not layer_item or not status_item or status_item.text() != "Tilpasset":
            return

        standard_path = os.path.join(
            self.current_style_folder(),
            f"{layer_item.text()}.qml",
        )

        self.table.setItem(row, 1, QTableWidgetItem(standard_path))
        status_item.setText("Standard")
        self.update_buttons()

    def update_buttons(self):
        row = self.table.currentRow()

        if row < 0:
            self.remove_button.setEnabled(False)
            self.reset_button.setEnabled(False)
            return

        status_item = self.table.item(row, 2)
        if not status_item:
            self.remove_button.setEnabled(False)
            self.reset_button.setEnabled(False)
            return

        status = status_item.text()
        self.remove_button.setEnabled(status == "Brugerregel")
        self.reset_button.setEnabled(status == "Tilpasset")

    def update_developer_ui(self, *args):
        enabled = self.developer_checkbox.isChecked()
        self.developer_info.setVisible(enabled)
        self.save_all_styles_button.setVisible(enabled)

    def save_all_styles(self):
        style_folder = self.current_style_folder()

        if not os.path.isdir(style_folder):
            QMessageBox.warning(
                self,
                "DMIKG Auto",
                f"Style-mappen blev ikke fundet:\n{style_folder}",
            )
            return

        code, ok = QInputDialog.getText(
            self,
            "Bekræft udviklerhandling",
            "Indtast udviklerkoden for at fortsætte:",
            QLineEdit.EchoMode.Password,
        )

        if not ok:
            return

        if code != DEVELOPER_CODE:
            QMessageBox.warning(
                self,
                "Forkert kode",
                "Udviklerkoden er forkert. Ingen styles blev gemt.",
            )
            return

        # Kun lag med en eksisterende standard-QML gemmes.
        # Det forhindrer fx baggrundskort/WMS i pludselig at oprette nye QML-filer.
        candidates = []
        skipped = []

        for layer in QgsProject.instance().mapLayers().values():
            qml_path = os.path.join(style_folder, f"{layer.name()}.qml")

            if os.path.isfile(qml_path):
                candidates.append((layer, qml_path))
            else:
                skipped.append(layer.name())

        if not candidates:
            QMessageBox.information(
                self,
                "DMIKG Auto",
                "Ingen projektlag matcher eksisterende QML-filer i style-mappen.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Overskriv fælles lagstyles?",
            (
                f"Du er ved at overskrive {len(candidates)} fælles QML-fil(er) "
                "med de styles, der er aktive i projektet lige nu.\n\n"
                "Vil du fortsætte?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        saved = []
        failed = []

        for layer, qml_path in candidates:
            try:
                message, success = layer.saveNamedStyle(qml_path)
            except Exception as exc:
                failed.append(f"{layer.name()}: {exc}")
                continue

            if success:
                saved.append(layer.name())
            else:
                failed.append(f"{layer.name()}: {message}")

        summary = [f"Gemte styles: {len(saved)}"]
        summary.append(f"Sprunget over: {len(skipped)}")
        summary.append(f"Fejl: {len(failed)}")

        if failed:
            summary.append("\nFejl:\n" + "\n".join(failed[:10]))

        QMessageBox.information(
            self,
            "DMIKG Auto - færdig",
            "\n".join(summary),
        )

        # Genindlæs tabellen så den afspejler style-mappen.
        self.load_settings()

    def apply(self):
        rules = []

        for row in range(self.table.rowCount()):
            layer_item = self.table.item(row, 0)
            style_item = self.table.item(row, 1)
            status_item = self.table.item(row, 2)

            if not layer_item or not status_item:
                continue

            layer_name = layer_item.text().strip()
            status = status_item.text()
            style_path = style_item.text().strip() if style_item else ""

            if status == "Standard":
                continue

            if not layer_name or not style_path:
                continue

            rules.append({
                "layer": layer_name,
                "style": style_path,
                "status": status,
            })

        settings = QSettings()
        old_root_folder = settings.value(ROOT_FOLDER_KEY, get_root_folder(), type=str)
        new_root_folder = self.current_root_folder()

        settings.setValue(SETTINGS_KEY, rules)
        settings.setValue(ENABLED_KEY, self.enabled_checkbox.isChecked())
        settings.setValue(DEVELOPER_MODE_KEY, self.developer_checkbox.isChecked())
        settings.setValue(ROOT_FOLDER_KEY, new_root_folder)

        if self.enabled_changed_callback:
            self.enabled_changed_callback(self.enabled_checkbox.isChecked())

        if (
            self.root_folder_changed_callback
            and os.path.normcase(os.path.normpath(old_root_folder))
            != os.path.normcase(os.path.normpath(new_root_folder))
        ):
            self.root_folder_changed_callback()


class DmikgAutoOptionsFactory(QgsOptionsWidgetFactory):

    def __init__(
        self,
        enabled_changed_callback=None,
        root_folder_changed_callback=None,
    ):
        super().__init__()

        self.enabled_changed_callback = enabled_changed_callback
        self.root_folder_changed_callback = root_folder_changed_callback
        self.setTitle("DMIKG Auto")

        plugin_dir = os.path.dirname(__file__)
        self.icon_path = os.path.join(plugin_dir, "kds_logo.png")

    def icon(self):
        return QIcon(self.icon_path)

    def createWidget(self, parent):
        return DmikgAutoOptionsPage(
            parent,
            enabled_changed_callback=self.enabled_changed_callback,
            root_folder_changed_callback=self.root_folder_changed_callback,
        )
