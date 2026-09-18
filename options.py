import os

from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHBoxLayout,
    QFileDialog,
    QHeaderView,
    QCheckBox,
)

from qgis.gui import QgsOptionsPageWidget, QgsOptionsWidgetFactory


# Gemte bruger-overrides og brugerregler
SETTINGS_KEY = "DMIKG_Auto/style_rules"
ENABLED_KEY = "DMIKG_AUTO/enabled"

# Fælles mappe med standard styles
STYLE_FOLDER = r"F:\GDL\Software\QGIS_komplet_stytem\layer_styles"


class DmikgAutoOptionsPage(QgsOptionsPageWidget):

    def __init__(self, parent=None, enabled_changed_callback=None):
        super().__init__(parent)
    
        self.enabled_changed_callback = enabled_changed_callback

        # Hovedlayout
        layout = QVBoxLayout()

        title = QLabel("Automatiske layer styles")
        layout.addWidget(title)
        
        self.enabled_checkbox = QCheckBox(
        "Automatisk styling aktiveret"
        )
           
        enabled = QSettings().value(
            ENABLED_KEY,
            True,
            type=bool
        )
    
        self.enabled_checkbox.setChecked(enabled)

        layout.addWidget(self.enabled_checkbox)

        # Tabel
        self.table = QTableWidget()
        self.table.setColumnCount(3)

        self.table.setHorizontalHeaderLabels([
            "Lagnavn",
            "Style-sti",
            "Status"
        ])

        # Giv style-stien mest plads
        header = self.table.horizontalHeader()
        
        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Interactive
        )
        
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch
        )
        
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Interactive
        )
        
        # Startbredder
        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(2, 110)

        # Dobbeltklik på style-sti åbner filvælger
        self.table.cellDoubleClicked.connect(
            self.choose_style_file
        )

        # Opdater knapper når en række vælges
        self.table.itemSelectionChanged.connect(
            self.update_buttons
        )

        layout.addWidget(self.table)

        # Knapper
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

        self.setLayout(layout)

        # Indlæs standard styles og brugerregler
        self.load_settings()

        # Sæt korrekt knap-status fra start
        self.update_buttons()

    # Find standard styles i fællesmappen
    def get_standard_styles(self):
        styles = {}

        if not os.path.isdir(STYLE_FOLDER):
            return styles

        for filename in os.listdir(STYLE_FOLDER):

            if not filename.lower().endswith(".qml"):
                continue

            # Filnavn uden .qml bruges som lagnavn
            layer_name = os.path.splitext(filename)[0]

            style_path = os.path.join(
                STYLE_FOLDER,
                filename
            )

            styles[layer_name] = style_path

        return styles

    # Indlæs tabellen
    def load_settings(self):
        settings = QSettings()

        custom_rules = settings.value(
            SETTINGS_KEY,
            [],
            type=list
        )

        standard_styles = self.get_standard_styles()

        self.table.setRowCount(0)

        # Vis standardregler
        for layer_name, standard_path in sorted(
            standard_styles.items()
        ):
            style_path = standard_path
            status = "Standard"

            # Tjek om brugeren har lavet en override
            for rule in custom_rules:
                if rule.get("layer", "") == layer_name:

                    custom_path = rule.get("style", "")

                    if custom_path:
                        style_path = custom_path
                        status = "Tilpasset"

                    break

            self.add_table_row(
                layer_name,
                style_path,
                status
            )

        # Vis brugerregler uden standardregel
        for rule in custom_rules:
            layer_name = rule.get("layer", "")
            style_path = rule.get("style", "")

            if not layer_name:
                continue

            # Standardregler er allerede vist ovenfor
            if layer_name in standard_styles:
                continue

            self.add_table_row(
                layer_name,
                style_path,
                "Brugerregel"
            )

    # Tilføj række til tabellen
    def add_table_row(
        self,
        layer_name,
        style_path,
        status
    ):
        row = self.table.rowCount()
        self.table.insertRow(row)

        layer_item = QTableWidgetItem(layer_name)
        style_item = QTableWidgetItem(style_path)
        status_item = QTableWidgetItem(status)

        # Status må ikke redigeres manuelt
        status_item.setFlags(
            status_item.flags()
            & ~Qt.ItemFlag.ItemIsEditable
        )

        # Standard og tilpassede regler har fast lagnavn
        if status in ("Standard", "Tilpasset"):
            layer_item.setFlags(
                layer_item.flags()
                & ~Qt.ItemFlag.ItemIsEditable
            )

        self.table.setItem(
            row,
            0,
            layer_item
        )

        self.table.setItem(
            row,
            1,
            style_item
        )

        self.table.setItem(
            row,
            2,
            status_item
        )

    # Vælg anden QML-fil
    def choose_style_file(self, row, column):

        # Kun dobbeltklik på Style-sti
        if column != 1:
            return

        status_item = self.table.item(row, 2)

        if not status_item:
            return

        current_status = status_item.text()

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Vælg QGIS style",
            "",
            "QGIS style (*.qml)"
        )

        if not file_path:
            return

        self.table.setItem(
            row,
            1,
            QTableWidgetItem(file_path)
        )

        # Standardregel bliver til override
        if current_status in ("Standard", "Tilpasset"):
            status_item.setText("Tilpasset")

        # Brugerregel forbliver brugerregel
        else:
            status_item.setText("Brugerregel")

        self.update_buttons()

    # Opret ny brugerregel
    def add_row(self):
        self.add_table_row(
            "",
            "",
            "Brugerregel"
        )

        row = self.table.rowCount() - 1
        self.table.selectRow(row)

        self.update_buttons()

    # Fjern brugerregel
    def remove_row(self):
        row = self.table.currentRow()

        if row < 0:
            return

        status_item = self.table.item(row, 2)

        if not status_item:
            return

        # Kun brugerregler må slettes
        if status_item.text() != "Brugerregel":
            return

        self.table.removeRow(row)

        self.update_buttons()

    # Nulstil override til standard
    def reset_row(self):
        row = self.table.currentRow()

        if row < 0:
            return

        layer_item = self.table.item(row, 0)
        status_item = self.table.item(row, 2)

        if not layer_item or not status_item:
            return

        # Kun tilpassede standardregler kan nulstilles
        if status_item.text() != "Tilpasset":
            return

        layer_name = layer_item.text()

        standard_path = os.path.join(
            STYLE_FOLDER,
            f"{layer_name}.qml"
        )

        self.table.setItem(
            row,
            1,
            QTableWidgetItem(standard_path)
        )

        status_item.setText("Standard")

        self.update_buttons()

    # Aktivér kun relevante knapper
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

        # Kun brugerregler kan fjernes
        self.remove_button.setEnabled(
            status == "Brugerregel"
        )

        # Kun overrides kan nulstilles
        self.reset_button.setEnabled(
            status == "Tilpasset"
        )

    # Gem ændringer
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

            style_path = ""

            if style_item:
                style_path = style_item.text().strip()

            # Standardregler gemmes ikke i QSettings
            if status == "Standard":
                continue

            # Tomme brugerregler gemmes heller ikke
            if not layer_name or not style_path:
                continue

            rules.append({
                "layer": layer_name,
                "style": style_path,
                "status": status
            })

        settings = QSettings()
        settings.setValue(
            SETTINGS_KEY,
            rules
        )
            
        settings.setValue(
            ENABLED_KEY,
            self.enabled_checkbox.isChecked()
        )

        if self.enabled_changed_callback:
            self.enabled_changed_callback(
            self.enabled_checkbox.isChecked()
            )
            
class DmikgAutoOptionsFactory(QgsOptionsWidgetFactory):

    def __init__(self, enabled_changed_callback=None):
        super().__init__()
    
        self.enabled_changed_callback = enabled_changed_callback

        self.setTitle("DMIKG Auto")

        plugin_dir = os.path.dirname(__file__)

        self.icon_path = os.path.join(
            plugin_dir,
            "kds_logo.png"
        )

    def icon(self):
        return QIcon(self.icon_path)

    def createWidget(self, parent):
        return DmikgAutoOptionsPage(
            parent,
            enabled_changed_callback=self.enabled_changed_callback
        )