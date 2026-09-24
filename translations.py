"""
Internationalization (i18n) support for liteSolve-beta application.
Provides English and Hindi language support with Qt signal-based language change notifications.
"""

from PySide6.QtCore import QObject, Signal


TRANSLATIONS = {
    "en": {
        # main.py
        "app_title": "liteSolve-beta",
        "tab_geometry": "Geometry Processor",
        "tab_case": "Case Writer",
        "tab_runner": "Case Runner",
        "tab_visualizer": "Case Visualizer (WIP)",

        # geometry_editor.py
        "geo_title": "liteSolve - Geometry Editor",
        "view_3d_title": "3D STEP File Viewer",
        "ctrl_title": "Geometry Controls & Face Selection",
        "btn_load_step": "Load STEP File",
        "btn_export_brep": "Export STEP to BREP",
        "inlet_label": "Inlet Selector:",
        "outlet_label": "Outlet Selector:",
        "inlet_separate": "Export inlets separately",
        "outlet_separate": "Export outlets separately",
        "btn_browse": "Browse",
        "btn_export_selected": "Export Selected Faces",
        "trimesh_title": "Trimesh Processor",
        "btn_process_stl": "Process STL Files",
        "btn_update_shm_patches": "Update SnappyHexMesh patch data",
        "btn_update_shm_model": "Update SnappyHexMesh model data",
        "btn_update_solver": "Update solver data",
        "placeholder_export_dir": "Select export directory...",
        "placeholder_stl_dir": "Select STL files directory...",
        "msg_no_shape": "No Shape",
        "msg_error": "Error",
        "msg_load_step_first": "Please load a STEP file first",
        "msg_no_faces": "No Faces",
        "msg_invalid_dir": "Invalid Directory",
        "msg_success": "Success",
        "msg_no_selection": "No Selection",
        "msg_select_faces_export": "Please select faces to export.",
        "dialog_open_step": "Open STEP File",
        "dialog_export_brep": "Export Shape to BREP",
        "dialog_select_stl_dir": "Select STL Files Directory",
        "dialog_select_export_dir": "Select Export Directory",

        # QMessageBox content messages (geometry_editor.py)
        "msg_load_step_failed": "Failed to load STEP file:\n{error}",
        "msg_exported_stl_count": "Exported {count} STL file(s) to:",
        "msg_face_ids": "Face IDs:",
        "msg_export_brep_success": "Successfully exported STEP shape to BREP:\n{path}",
        "msg_export_brep_failed": "Failed to export BREP:\n{error}",
        "msg_process_stl_success": "Successfully compiled STL files!\nCreated:\n{multi}\n{single}",
        "msg_process_stl_failed": "Failed to process STL files:\n{error}",
        "msg_write_shm_success": "Successfully wrote layer/region info to Snapphexmesh data",
        "msg_write_point_success": "Successfully wrote Point in volume: {point} to Snapphexmesh data",
        "msg_write_boundary_success": "Successfully wrote boundary & patch data to Laminar case",

        # case_runner.py and case_visualizer.py
        "foam_settings": "OpenFOAM Settings",
        "foam_dir_label": "OpenFOAM Directory:",
        "foam_ver_label": "OpenFOAM Version:",
        "btn_save_settings": "Save Settings",
        "cwd_group": "Working Directory",
        "placeholder_cwd": "Select case directory...",
        "mesh_group": "Meshing Commands",
        "runner_group": "Case runner Commands",
        "vis_group": "Visualization",
        "btn_run_allmesh": "Run Allmesh.bat",
        "btn_run_allrun": "Run Allrun.bat",
        "btn_open_mesh_paraview": "Open Mesh in ParaView",
        "btn_open_sim_paraview": "Open simulation results in ParaView",
        "log_label": "Output Log:",
        "msg_settings_saved": "Settings Saved",
        "msg_invalid_directory": "Invalid Directory",
        "msg_script_not_found": "Script Not Found",
        "msg_paraview_not_found": "ParaView Not Found",
        "dialog_select_foam_dir": "Select OpenFOAM Directory",
        "dialog_select_working_dir": "Select Working Directory",

        # yaml_editor.py
        "file_label_default": "No file loaded",
        "btn_save": "Save",
        "btn_save_as": "Save As",
        "case_name_label": "Case Name:",
        "case_path_label": "Case Path:",
        "btn_write_case": "Write Case",
        "stl_dir_label": "STL Dir:",
        "btn_copy_stl": "Copy Stl files",
        "polymesh_label": "For simulation cases",
        "polymesh_dir_label": "Polymesh Dir:",
        "btn_copy_polymesh": "Copy Polymesh folder",
        "placeholder_polymesh_dir": "Select Polymesh directory...",
        "dialog_open_yaml": "Open YAML File",
        "dialog_select_case_dir": "Select Case Output Directory",
        "dialog_save_yaml_as": "Save YAML File As",

        # General
        "lang_en": "English",
        "lang_hi": "हिंदी",
        "language": "Language",
    },
    "hi": {
        # main.py
        "app_title": "liteSolve-beta (हिंदी)",
        "tab_geometry": "ज्यामिति प्रोसेसर",
        "tab_case": "केस राइटर",
        "tab_runner": "केस रनर",
        "tab_visualizer": "केस विज़ुअलाइज़र (कार्य प्रगति पर)",

        # geometry_editor.py
        "geo_title": "liteSolve - ज्यामिति एडिटर",
        "view_3d_title": "3D STEP फ़ाइल व्यूअर",
        "ctrl_title": "ज्यामिति नियंत्रण और फेस चयन",
        "btn_load_step": "STEP फ़ाइल लोड करें",
        "btn_export_brep": "STEP को BREP में निर्यात करें",
        "inlet_label": "इनलेट चयनकर्ता:",
        "outlet_label": "आउटलेट चयनकर्ता:",
        "inlet_separate": "इनलेट अलग से निर्यात करें",
        "outlet_separate": "आउटलेट अलग से निर्यात करें",
        "btn_browse": "ब्राउज़ करें",
        "btn_export_selected": "चयनित फेस निर्यात करें",
        "trimesh_title": "ट्राइमेश प्रोसेसर",
        "btn_process_stl": "STL फ़ाइलें प्रोसेस करें",
        "btn_update_shm_patches": "SnappyHexMesh पैच डेटा अपडेट करें",
        "btn_update_shm_model": "SnappyHexMesh मॉडल डेटा अपडेट करें",
        "btn_update_solver": "सॉल्वर डेटा अपडेट करें",
        "placeholder_export_dir": "निर्यात डायरेक्टरी चुनें...",
        "placeholder_stl_dir": "STL फ़ाइल डायरेक्टरी चुनें...",
        "msg_no_shape": "कोई आकार नहीं",
        "msg_error": "त्रुटि",
        "msg_load_step_first": "कृपया पहले STEP फ़ाइल लोड करें",
        "msg_no_faces": "कोई फेस नहीं",
        "msg_invalid_dir": "अमान्य डायरेक्टरी",
        "msg_success": "सफलता",
        "msg_no_selection": "कोई चयन नहीं",
        "msg_select_faces_export": "कृपया निर्यात के लिए फेस चुनें।",
        "dialog_open_step": "STEP फ़ाइल खोलें",
        "dialog_export_brep": "BREP में आकार निर्यात करें",
        "dialog_select_stl_dir": "STL फ़ाइल डायरेक्टरी चुनें",
        "dialog_select_export_dir": "निर्यात डायरेक्टरी चुनें",

        # QMessageBox content messages (geometry_editor.py)
        "msg_load_step_failed": "STEP फ़ाइल लोड करने में विफल:\n{error}",
        "msg_exported_stl_count": "{count} STL फ़ाइलें निर्यात की गईं:",
        "msg_face_ids": "फेस आईडी:",
        "msg_export_brep_success": "STEP आकार को BREP में सफलतापूर्वक निर्यात किया:\n{path}",
        "msg_export_brep_failed": "BREP निर्यात करने में विफल:\n{error}",
        "msg_process_stl_success": "STL फ़ाइलें सफलतापूर्वक संकलित!\nबनाई गईं:\n{multi}\n{single}",
        "msg_process_stl_failed": "STL फ़ाइलें प्रोसेस करने में विफल:\n{error}",
        "msg_write_shm_success": "Snapphexmesh डेटा में लेयर/रिजन जानकारी सफलतापूर्वक लिखी गई",
        "msg_write_point_success": "Snapphexmesh डेटा में वॉल्यूम में पॉइंट सफलतापूर्वक लिखा गया: {point}",
        "msg_write_boundary_success": "Laminar case में बाउंड्री और पैच डेटा सफलतापूर्वक लिखा गया",

        # case_runner.py and case_visualizer.py
        "foam_settings": "OpenFOAM सेटिंग्स",
        "foam_dir_label": "OpenFOAM डायरेक्टरी:",
        "foam_ver_label": "OpenFOAM संस्करण:",
        "btn_save_settings": "सेटिंग्स सेव करें",
        "cwd_group": "कार्य डायरेक्टरी",
        "placeholder_cwd": "केस डायरेक्टरी चुनें...",
        "mesh_group": "मेशिंग कमांड्स",
        "runner_group": "केस रनर कमांड्स",
        "vis_group": "विज़ुअलाइज़ेशन",
        "btn_run_allmesh": "Allmesh.bat चलाएं",
        "btn_run_allrun": "Allrun.bat चलाएं",
        "btn_open_mesh_paraview": "ParaView में मेश खोलें",
        "btn_open_sim_paraview": "ParaView में सिमुलेशन परिणाम खोलें",
        "log_label": "आउटपुट लॉग:",
        "msg_settings_saved": "सेटिंग्स सेव हुईं",
        "msg_invalid_directory": "अमान्य डायरेक्टरी",
        "msg_script_not_found": "स्क्रिप्ट नहीं मिली",
        "msg_paraview_not_found": "ParaView नहीं मिला",
        "dialog_select_foam_dir": "OpenFOAM डायरेक्टरी चुनें",
        "dialog_select_working_dir": "कार्य डायरेक्टरी चुनें",

        # yaml_editor.py
        "file_label_default": "कोई फ़ाइल लोड नहीं",
        "btn_save": "सेव करें",
        "btn_save_as": "दूसरे नाम से सेव करें",
        "case_name_label": "केस नाम:",
        "case_path_label": "केस पाथ:",
        "btn_write_case": "केस लिखें",
        "stl_dir_label": "STL डायरेक्टरी:",
        "btn_copy_stl": "Stl फ़ाइलें कॉपी करें",
        "polymesh_label": "सिमुलेशन केस के लिए",
        "polymesh_dir_label": "Polymesh डायरेक्टरी:",
        "btn_copy_polymesh": "Polymesh फ़ोल्डर कॉपी करें",
        "placeholder_polymesh_dir": "Polymesh डायरेक्टरी चुनें...",
        "dialog_open_yaml": "YAML फ़ाइल खोलें",
        "dialog_select_case_dir": "केस आउटपुट डायरेक्टरी चुनें",
        "dialog_save_yaml_as": "YAML फ़ाइल दूसरे नाम से सेव करें",

        # General
        "lang_en": "English",
        "lang_hi": "हिंदी",
        "language": "भाषा",
    },
}


class TranslationManager(QObject):
    """
    Singleton TranslationManager that provides language switching functionality.
    Emits a signal when the language changes so UI components can react.
    """
    language_changed = Signal()

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._current_language = "en"
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            super().__init__()
            self._current_language = "en"
            self._initialized = True

    def get(self, key: str) -> str:
        """
        Get the translation for the given key in the current language.
        
        Args:
            key: The translation key to look up
            
        Returns:
            The translated string, or the key itself if not found
        """
        lang_dict = TRANSLATIONS.get(self._current_language, TRANSLATIONS["en"])
        return lang_dict.get(key, key)

    def set_language(self, lang: str) -> None:
        """
        Set the current language.
        
        Args:
            lang: The language code ("en" or "hi")
        """
        if lang in ("en", "hi") and lang != self._current_language:
            self._current_language = lang
            self.language_changed.emit()

    def get_language(self) -> str:
        """
        Get the current language code.
        
        Returns:
            The current language code ("en" or "hi")
        """
        return self._current_language


# Global singleton instance
translator = TranslationManager()