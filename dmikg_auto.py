import os
import shutil

from qgis.core import QgsProject, QgsMessageLog, QgsApplication, Qgis
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolButton, QMenu
from qgis.PyQt.QtCore import QSettings

from .options import DmikgAutoOptionsFactory
from .config import (
    ENABLED_KEY,
    SETTINGS_KEY,
    SHARED_STYLE_OVERRIDES,
    get_style_folder,
    get_template_source,
)

class DmikgAuto:

    def __init__(self, iface):
        self.iface = iface
        self.options_factory = None
        self.action = None
        self.tool_button = None
        self.enabled_action = None
        
    def initGui(self):
        # Opdater lokal projektskabelon
        self.sync_template()
        
        # Nye lag får altid auto-style
        QgsProject.instance().layersAdded.connect(self.layers_added)

        # Reager når et projekt er færdigindlæst
        QgsProject.instance().readProject.connect(self.project_loaded)

        # Registrer indstillingssiden
        self.options_factory = DmikgAutoOptionsFactory(
            enabled_changed_callback=self.set_auto_enabled,
            root_folder_changed_callback=self.sync_template,
        )
            
        self.iface.registerOptionsWidgetFactory(self.options_factory)

        # Plugin-ikon
        plugin_dir = os.path.dirname(__file__)
        icon_path = os.path.join(plugin_dir, "kds_logo.png")

        # Toolbar-knap
        self.tool_button = QToolButton()
        self.tool_button.setIcon(QIcon(icon_path))
        self.tool_button.setToolTip("DMIKG Auto")
        
        # Klik på selve ikonet åbner indstillinger
        self.tool_button.clicked.connect(
            self.open_settings
        )
        
        # Lille pil giver dropdown
        self.tool_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.MenuButtonPopup
        )
        
        menu = QMenu(self.tool_button)
        
        # Indstillinger
        settings_action = QAction(
            "Indstillinger...",
            menu
        )
        
        settings_action.triggered.connect(
            self.open_settings
        )
        
        menu.addAction(settings_action)
        menu.addSeparator()
        
        # Auto styling ON/OFF
        self.enabled_action = QAction(
            "Automatisk styling",
            menu
        )
        
        self.enabled_action.setCheckable(True)
        
        enabled = QSettings().value(
            ENABLED_KEY,
            True,
            type=bool
        )
        
        self.enabled_action.setChecked(enabled)
        
        self.enabled_action.toggled.connect(
            self.set_auto_enabled
        )
        
        menu.addAction(self.enabled_action)
        
        self.tool_button.setMenu(menu)
        
        # Tilføj knappen til QGIS toolbar
        self.action = self.iface.addToolBarWidget(
            self.tool_button
        )

    def open_settings(self):
        # Åbn DMIKG Auto-siden i QGIS-indstillinger
        self.iface.showOptionsDialog(
            self.iface.mainWindow(),
            currentPage="DMIKG Auto"
        )

    def set_auto_enabled(self, enabled):
        settings = QSettings()
    
        settings.setValue(
            ENABLED_KEY,
            enabled
        )
    
    
        if self.enabled_action:
            self.enabled_action.blockSignals(True)
            self.enabled_action.setChecked(enabled)
            self.enabled_action.blockSignals(False)

    
        if enabled:
            self.tool_button.setToolTip(
                "DMIKG Auto"
            )
        else:
            self.tool_button.setToolTip(
                "DMIKG Auto - automatisk styling deaktiveret"
            )

    def sync_template(self):
        template_source = get_template_source()

        # Stop hvis fællesdrevets skabelon ikke findes
        if not os.path.exists(template_source):
            QgsMessageLog.logMessage(
                f"Skabelon ikke fundet: {template_source}",
                "DMIKG Auto",
                level=Qgis.Warning
            )
            return

        # Find brugerens aktive QGIS-profil
        profile_path = QgsApplication.qgisSettingsDirPath()
        
        if Qgis.QGIS_VERSION_INT >= 40000:
            profile_path = profile_path.replace(
                "QGIS3",
                "QGIS4"
            )

        # Lokal mappe til projektskabeloner
        template_folder = os.path.join(
            profile_path,
            "project_templates"
        )

        os.makedirs(
            template_folder,
            exist_ok=True
        )

        # Lokal projektskabelon
        local_template = os.path.join(
            template_folder,
            "SKABELONV2.qgz"
        )

        # Kopier skabelonen hvis den mangler lokalt,
        # eller hvis fællesversionen er nyere
        should_copy = (
            not os.path.exists(local_template)
            or os.path.getmtime(template_source)
            > os.path.getmtime(local_template)
        )

        if should_copy:
            shutil.copy2(
                template_source,
                local_template
            )

            QgsMessageLog.logMessage(
                f"SKABELONV2 opdateret: {local_template}",
                "DMIKG Auto",
                level=Qgis.Info
            )
        
    def unload(self):
        # Fjern signaler igen når pluginet unloades
        QgsProject.instance().layersAdded.disconnect(self.layers_added)
        QgsProject.instance().readProject.disconnect(self.project_loaded)

        # Fjern indstillingssiden
        if self.options_factory:
            self.iface.unregisterOptionsWidgetFactory(
                self.options_factory
            )

        # Fjern toolbar-knappen
        if self.action:
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None

    def layers_added(self, layers):
        settings = QSettings()
    
        enabled = settings.value(
            ENABLED_KEY,
            True,
            type=bool
        )
    
        # Stop helt hvis automatisk styling er deaktiveret
        if not enabled:
            return
    
        # Behandl alle nye lag der bliver tilføjet
        for layer in layers:
            self.process_layer(layer)

    def process_layer(self, layer):
        # Nye lag får automatisk style
        self.apply_style(layer)

    def project_loaded(self, *args):
        project = QgsProject.instance()

        # Find projektfilens navn uden .qgz
        project_path = project.fileName()
        project_name = os.path.splitext(
            os.path.basename(project_path)
        )[0]

        # Kun SKABELONV2 må få eksisterende lag restylet
        if project_name != "SKABELONV2":
            return

        QgsMessageLog.logMessage(
            "SKABELONV2 åbnet - opdaterer layer styles",
            "DMIKG Auto",
            level=Qgis.Info
        )

        # Gennemgå alle lag der allerede findes i skabelonen
        for layer in project.mapLayers().values():
            self.apply_style(layer)

    def apply_style(self, layer):
        settings = QSettings()
        layer_name = layer.name()

        # 1. Tjek om brugeren har lavet en lokal override
        custom_rules = settings.value(
            SETTINGS_KEY,
            [],
            type=list
        )

        for rule in custom_rules:
            if rule.get("layer", "") == layer_name:
                custom_style_path = rule.get("style", "")

                # Brug kun override hvis filen faktisk findes
                if custom_style_path and os.path.exists(
                    custom_style_path
                ):
                    message, success = layer.loadNamedStyle(
                        custom_style_path
                    )

                    if success:
                        layer.triggerRepaint()

                        QgsMessageLog.logMessage(
                            (
                                f"Brugerregel anvendt på "
                                f"{layer_name}: "
                                f"{custom_style_path}"
                            ),
                            "DMIKG Auto",
                            level=Qgis.Info
                        )

                    else:
                        QgsMessageLog.logMessage(
                            (
                                f"Kunne ikke indlæse brugerregel "
                                f"på {layer_name}: {message}"
                            ),
                            "DMIKG Auto",
                            level=Qgis.Warning
                        )

                    return

        # 2. Fælles filsti for særlige lag (efter eventuel lokal override).
        shared_style_path = SHARED_STYLE_OVERRIDES.get(layer_name)
        if shared_style_path:
            if os.path.isfile(shared_style_path):
                message, success = layer.loadNamedStyle(shared_style_path)
                if success:
                    layer.triggerRepaint()
                    QgsMessageLog.logMessage(
                        f"Fælles style anvendt på {layer_name}: {shared_style_path}",
                        "DMIKG Auto", level=Qgis.Info,
                    )
                    return
                QgsMessageLog.logMessage(
                    f"Kunne ikke indlæse fælles style på {layer_name}: {message}. "
                    "Forsøger standard-QML.",
                    "DMIKG Auto", level=Qgis.Warning,
                )
            else:
                QgsMessageLog.logMessage(
                    f"Fælles style mangler for {layer_name}: {shared_style_path}. "
                    "Forsøger standard-QML.",
                    "DMIKG Auto", level=Qgis.Warning,
                )

        # 3. Hvis ingen override findes:
        # prøv standard style fra fællesmappen
        style_path = os.path.join(
            get_style_folder(),
            f"{layer_name}.qml"
        )

        # Ingen matchende QML = gør ingenting
        if not os.path.exists(style_path):
            return

        message, success = layer.loadNamedStyle(style_path)

        # 3. Opdater laget hvis style blev indlæst korrekt
        if success:
            layer.triggerRepaint()

            QgsMessageLog.logMessage(
                (
                    f"Standard style anvendt på "
                    f"{layer_name}: {style_path}"
                ),
                "DMIKG Auto",
                level=Qgis.Info
            )

        else:
            QgsMessageLog.logMessage(
                (
                    f"Kunne ikke indlæse style "
                    f"på {layer_name}: {message}"
                ),
                "DMIKG Auto",
                level=Qgis.Warning
            )