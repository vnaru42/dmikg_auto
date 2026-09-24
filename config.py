import os

from qgis.PyQt.QtCore import QSettings


SETTINGS_KEY = "DMIKG_Auto/style_rules"
ENABLED_KEY = "DMIKG_AUTO/enabled"
ROOT_FOLDER_KEY = "DMIKG_AUTO/root_folder"
DEVELOPER_MODE_KEY = "DMIKG_AUTO/developer_mode"

DEFAULT_ROOT_FOLDER = r"F:\GDL\Software\QGIS_komplet_stytem"

# Dette er kun en ekstra bekræftelse mod utilsigtet overskrivning.
# Det er ikke tænkt som egentlig adgangssikring.
DEVELOPER_CODE = "DMIKG"

# Fælles undtagelser: samme filsti bruges af alle medarbejdere.
# Lokale brugerregler kan fortsat overstyre disse.
SHARED_STYLE_OVERRIDES = {
    "V_ALLE_NIV_OBS": (
        r"F:\GDL\Data\GEO\BC\Niv_Opgaver\QGIS_Skabelon"
        r"\ALLE_NIV_OBS_opmålingsår.qml"
    ),
}


def get_root_folder():
    return QSettings().value(
        ROOT_FOLDER_KEY,
        DEFAULT_ROOT_FOLDER,
        type=str,
    )


def get_style_folder():
    return os.path.join(get_root_folder(), "layer_styles")


def get_template_source():
    return os.path.join(
        get_root_folder(),
        "TEMPLATE_PROJECT",
        "SKABELONV2.qgz",
    )
