import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QMenuBar, QMenu
from PySide6.QtGui import QAction

from translations import translator
from geometry_editor import GeometryProcessorWindow
from yaml_editor import YamlEditor
from case_runner import CaseRunner
from case_visualizer import CaseVisualizer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(translator.get("app_title"))
        self.setGeometry(100, 100, 900, 600)

        self._create_menu_bar()

        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_geometry_tab(), translator.get("tab_geometry"))
        self.tabs.addTab(self._create_case_tab(), translator.get("tab_case"))
        self.tabs.addTab(self._create_runner_tab(), translator.get("tab_runner"))
        self.tabs.addTab(self._create_visualizer_tab(), translator.get("tab_visualizer"))
        self.setCentralWidget(self.tabs)

        translator.language_changed.connect(self.on_language_changed)

    def _create_menu_bar(self):
        menubar = QMenuBar()
        language_menu = QMenu(translator.get("language"), menubar)

        self.action_en = QAction(translator.get("lang_en"), self)
        self.action_en.setCheckable(True)
        self.action_en.setChecked(translator.get_language() == "en")
        self.action_en.triggered.connect(lambda: self._set_language("en"))

        self.action_hi = QAction(translator.get("lang_hi"), self)
        self.action_hi.setCheckable(True)
        self.action_hi.setChecked(translator.get_language() == "hi")
        self.action_hi.triggered.connect(lambda: self._set_language("hi"))

        language_menu.addAction(self.action_en)
        language_menu.addAction(self.action_hi)
        menubar.addMenu(language_menu)
        self.setMenuBar(menubar)

    def _set_language(self, lang: str):
        translator.set_language(lang)

    def on_language_changed(self):
        self.setWindowTitle(translator.get("app_title"))
        self.tabs.setTabText(0, translator.get("tab_geometry"))
        self.tabs.setTabText(1, translator.get("tab_case"))
        self.tabs.setTabText(2, translator.get("tab_runner"))
        self.tabs.setTabText(3, translator.get("tab_visualizer"))

        self.action_en.setText(translator.get("lang_en"))
        self.action_hi.setText(translator.get("lang_hi"))
        self.action_en.setChecked(translator.get_language() == "en")
        self.action_hi.setChecked(translator.get_language() == "hi")

    def _create_geometry_tab(self) -> QWidget:
        self.geometry_window = GeometryProcessorWindow()
        return self.geometry_window.central_widget

    def _create_case_tab(self) -> QWidget:
        self.yaml_editor = YamlEditor()
        return self.yaml_editor

    def _create_runner_tab(self) -> QWidget:
        self.case_runner = CaseRunner()
        return self.case_runner

    def _create_visualizer_tab(self) -> QWidget:
        self.case_runner = CaseVisualizer()
        return self.case_runner


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())