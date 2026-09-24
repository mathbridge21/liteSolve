"""YAML Editor with PySide6 - Structure-agnostic recursive editor."""

import shutil
import sys
from pathlib import Path
from typing import Any

import yaml
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from case_writer import add_trisurface, load_solver_proc_vals, setup_case_paths, write_case, YAML_CASE_FILE_PATH
from translations import translator

DEFAULT_INDENT_SIZE = 20
DEFAULT_DEPTH_AUTO_EXPAND = 2
DEFAULT_VALUE_MIN_WIDTH = 200
DEFAULT_KEY_MIN_WIDTH = 100
DEFAULT_EXPAND_BTN_WIDTH = 20
DEFAULT_SAVE_FEEDBACK_DURATION_MS = 1500
DEFAULT_STL_DIR = "./liteSolve-test-cases/stl"
DEFAULT_CASE_DIR = "./liteSolve-test-cases"
DEFAULT_POLYMESH_DIR = "./liteSolve-test-cases/MeshCase/constant/polyMesh"


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(item) for item in obj]
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    return str(obj)


class YamlKeyValueItem(QWidget):
    changed = Signal()

    @staticmethod
    def _clear_layout(layout: QLayout) -> None:
        while layout.count():
            child = layout.takeAt(0)
            if child and child.widget():
                child.widget().deleteLater()

    @staticmethod
    def _parse_value(text: str) -> Any:
        try:
            return int(text)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                return text

    def __init__(self, key: str, value: Any, path: tuple, depth: int = 0, parent=None, options: list | None = None):
        super().__init__(parent)
        self.key = key
        self.path = path
        self._depth = depth
        self._value = value
        self._options = options
        self._children: list[YamlKeyValueItem] = []
        self._children_widget: QWidget | None = None
        self._expand_btn: QPushButton | None = None
        self._value_edit: QWidget | None = None
        self._is_expanded = depth < DEFAULT_DEPTH_AUTO_EXPAND
        self._setup_ui()

    @property
    def depth(self) -> int:
        return self._depth

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        row = QHBoxLayout()
        row.setSpacing(4)
        row.addSpacing(self._depth * DEFAULT_INDENT_SIZE)

        is_container = isinstance(self._value, (dict, list)) and len(self._value) > 0

        if is_container:
            self._expand_btn = QPushButton("-" if self._is_expanded else "+")
            self._expand_btn.setFixedWidth(DEFAULT_EXPAND_BTN_WIDTH)
            self._expand_btn.clicked.connect(self._toggle_expand)
            row.addWidget(self._expand_btn)
        else:
            row.addSpacing(DEFAULT_EXPAND_BTN_WIDTH)

        self._key_label = QLabel(str(self.key))
        self._key_label.setMinimumWidth(DEFAULT_KEY_MIN_WIDTH)
        row.addWidget(self._key_label)

        if is_container:
            self._value_edit = None
        elif self._options:
            combo = QComboBox()
            combo.addItems([str(opt) for opt in self._options])
            if str(self._value) in [str(opt) for opt in self._options]:
                combo.setCurrentText(str(self._value))
            else:
                combo.setCurrentIndex(0)
                self._value = combo.currentText()
            combo.currentTextChanged.connect(self._on_combo_changed)
            combo.setMinimumWidth(DEFAULT_VALUE_MIN_WIDTH)
            self._value_edit = combo
            row.addWidget(self._value_edit)
        else:
            self._value_edit = QLineEdit(str(self._value))
            self._value_edit.textChanged.connect(self._on_value_changed)
            self._value_edit.setMinimumWidth(DEFAULT_VALUE_MIN_WIDTH)
            row.addWidget(self._value_edit)

        layout.addLayout(row)

        if is_container:
            self._children_widget = QWidget()
            children_layout = QVBoxLayout(self._children_widget)
            children_layout.setContentsMargins(0, 0, 0, 0)
            children_layout.setSpacing(2)
            self._rebuild_children()
            if not self._is_expanded:
                self._children_widget.hide()
            layout.addWidget(self._children_widget)

    def _rebuild_children(self):
        for child in self._children:
            child.deleteLater()
        self._children.clear()

        if not self._children_widget:
            return

        children_layout = self._children_widget.layout()
        if children_layout:
            self._clear_layout(children_layout)

        if isinstance(self._value, dict):
            for k, v in self._value.items():
                if k.endswith("_options"):
                    continue
                options_key = f"{k}_options"
                opts = self._value.get(options_key) if isinstance(self._value, dict) else None
                item = YamlKeyValueItem(k, v, (*self.path, k), self._depth + 1, options=opts)
                item.changed.connect(self._propagate_change)
                self._children.append(item)
                if children_layout:
                    children_layout.addWidget(item)
        elif isinstance(self._value, list):
            for i, v in enumerate(self._value):
                item = YamlKeyValueItem(f"[{i}]", v, (*self.path, i), self._depth + 1)
                item.changed.connect(self._propagate_change)
                self._children.append(item)
                if children_layout:
                    children_layout.addWidget(item)

    def _toggle_expand(self):
        self._is_expanded = not self._is_expanded
        if self._expand_btn:
            self._expand_btn.setText("-" if self._is_expanded else "+")
        if self._children_widget:
            self._children_widget.setVisible(self._is_expanded)

    def _on_value_changed(self, text: str):
        self._value = text
        self.changed.emit()

    def _on_combo_changed(self, text: str):
        self._value = text
        self.changed.emit()

    def _propagate_change(self):
        self._sync_from_children()
        self.changed.emit()

    def _sync_from_children(self):
        if isinstance(self._value, dict):
            for child in self._children:
                child_val = child.get_value()
                key = child.key if isinstance(child.key, str) and not child.key.startswith("[") else str(child.key)
                self._value[key] = child_val
        elif isinstance(self._value, list):
            for child in self._children:
                try:
                    idx = int(child.key[1:-1])
                    self._value[idx] = child.get_value()
                except (ValueError, IndexError):
                    pass

    def get_value(self) -> Any:
        self._sync_from_children()
        val = self._value
        if isinstance(val, dict):
            return {child.key: child.get_value() for child in self._children}
        if isinstance(val, list):
            return [child.get_value() for child in self._children]
        if self._value_edit and (not isinstance(self._value_edit, QComboBox)) and not self._value_edit.isReadOnly():
            if isinstance(self._value_edit, QComboBox):
                return self._parse_value(self._value_edit.currentText())
            return self._parse_value(self._value_edit.text())
        return val


class YamlEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file_path: Path | None = None
        self.yaml_data: dict = {}
        self.root_items: list[YamlKeyValueItem] = []
        self._setup_ui()
        translator.language_changed.connect(self.on_language_changed)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.file_label = QLabel(translator.get("file_label_default"))
        header.addWidget(self.file_label)

        self.browse_btn = QPushButton(translator.get("btn_browse"))
        self.browse_btn.setMaximumWidth(60)
        self.browse_btn.clicked.connect(self._browse_file)
        header.addWidget(self.browse_btn)

        self.save_btn = QPushButton(translator.get("btn_save"))
        self.save_btn.setMaximumWidth(60)
        self.save_btn.clicked.connect(self._save_yaml)
        self.save_btn.setEnabled(False)
        header.addWidget(self.save_btn)

        self.save_as_btn = QPushButton(translator.get("btn_save_as"))
        self.save_as_btn.setMaximumWidth(70)
        self.save_as_btn.clicked.connect(self._save_yaml_as)
        self.save_as_btn.setEnabled(False)
        header.addWidget(self.save_as_btn)

        header.addSpacing(20)

        self.case_name_label = QLabel(translator.get("case_name_label"))
        header.addWidget(self.case_name_label)
        self.case_name_input = QLineEdit("SolverCase")
        self.case_name_input.setMinimumWidth(100)
        self.case_name_input.setMaximumWidth(150)
        header.addWidget(self.case_name_input)

        self.case_path_label = QLabel(translator.get("case_path_label"))
        header.addWidget(self.case_path_label)
        self.case_path_input = QLineEdit()
        self.case_path_input.setText(DEFAULT_CASE_DIR)
        self.case_path_input.setPlaceholderText(translator.get("placeholder_export_dir"))
        self.case_path_input.setMinimumWidth(100)
        self.case_path_input.setMaximumWidth(150)
        header.addWidget(self.case_path_input)

        self.case_path_btn = QPushButton(translator.get("btn_browse"))
        self.case_path_btn.setMaximumWidth(60)
        self.case_path_btn.clicked.connect(self._browse_case_path)
        header.addWidget(self.case_path_btn)

        self.write_case_btn = QPushButton(translator.get("btn_write_case"))
        self.write_case_btn.clicked.connect(self._write_case)
        header.addWidget(self.write_case_btn)

        header.addSpacing(10)

        header.addStretch()
        layout.addLayout(header)

        subheader = QHBoxLayout()

        self.stl_dir_label = QLabel(translator.get("stl_dir_label"))
        subheader.addWidget(self.stl_dir_label)
        self.stl_dir_input = QLineEdit()
        self.stl_dir_input.setText(DEFAULT_STL_DIR)
        self.stl_dir_input.setPlaceholderText(translator.get("placeholder_stl_dir"))
        self.stl_dir_input.setMinimumWidth(100)
        self.stl_dir_input.setMaximumWidth(150)
        subheader.addWidget(self.stl_dir_input)

        self.stl_dir_btn = QPushButton(translator.get("btn_browse"))
        self.stl_dir_btn.setMaximumWidth(60)
        self.stl_dir_btn.clicked.connect(self._browse_stl_dir)
        subheader.addWidget(self.stl_dir_btn)

        self.copy_stl_btn = QPushButton(translator.get("btn_copy_stl"))
        self.copy_stl_btn.clicked.connect(self._copy_stl_files)
        subheader.addWidget(self.copy_stl_btn)

        self.polymesh_label = QLabel(translator.get("polymesh_label"))
        subheader.addWidget(self.polymesh_label)

        self.polymesh_dir_label = QLabel(translator.get("polymesh_dir_label"))
        subheader.addWidget(self.polymesh_dir_label)
        self.polymesh_dir_input = QLineEdit()
        self.polymesh_dir_input.setText(DEFAULT_POLYMESH_DIR)
        self.polymesh_dir_input.setPlaceholderText(translator.get("placeholder_polymesh_dir"))
        self.polymesh_dir_input.setMinimumWidth(100)
        self.polymesh_dir_input.setMaximumWidth(150)
        subheader.addWidget(self.polymesh_dir_input)

        self.polymesh_dir_btn = QPushButton(translator.get("btn_browse"))
        self.polymesh_dir_btn.setMaximumWidth(60)
        self.polymesh_dir_btn.clicked.connect(self._browse_polymesh_dir)
        subheader.addWidget(self.polymesh_dir_btn)

        self.copy_polymesh_btn = QPushButton(translator.get("btn_copy_polymesh"))
        self.copy_polymesh_btn.clicked.connect(self._copy_polymesh_files)
        subheader.addWidget(self.copy_polymesh_btn)


        subheader.addSpacing(10)

        subheader.addStretch()
        layout.addLayout(subheader)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setSpacing(2)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            translator.get("dialog_open_yaml"),
            "",
            "YAML Files (*.yaml *.yml);;All Files (*)",
        )
        if file_path:
            self._load_file(Path(file_path))

    def _load_file(self, file_path: Path):
        self.yaml_data = {}
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                self.yaml_data = yaml.safe_load(f) or {}
        self.current_file_path = file_path
        self.file_label.setText(f"File: {file_path.name}")
        self.save_btn.setEnabled(True)
        self.save_as_btn.setEnabled(True)
        self._rebuild_editor()

    def _browse_case_path(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            translator.get("dialog_select_case_dir"),
            "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if dir_path:
            self.case_path_input.setText(dir_path)

    def _write_case(self):
        if not self.case_path_input.text() or not self.case_name_input.text():
            return

        case_name = self.case_name_input.text()
        case_path = Path(self.case_path_input.text()) / case_name

        setup_case_paths(case_path)
        write_case(self.yaml_data, case_name, case_path)

        self.write_case_btn.setText(translator.get("msg_success"))
        QTimer.singleShot(
            DEFAULT_SAVE_FEEDBACK_DURATION_MS,
            lambda: self.write_case_btn.setText(translator.get("btn_write_case")),
        )

    def _browse_stl_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            translator.get("dialog_select_stl_dir"),
            "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if dir_path:
            self.stl_dir_input.setText(dir_path)

    def _copy_stl_files(self):
        if not self.case_path_input.text() or not self.case_name_input.text():
            return

        stl_dir = self.stl_dir_input.text()
        if not stl_dir:
            return

        case_name = self.case_name_input.text()
        case_path = Path(self.case_path_input.text()) / case_name
        trisurface_path = add_trisurface(case_path)

        stl_source_path = Path(stl_dir)
        if stl_source_path.exists() and stl_source_path.is_dir():
            for stl_file in stl_source_path.glob("*.stl"):
                shutil.copy(stl_file, trisurface_path / stl_file.name)
                print(f"Copied {stl_file.name} to {trisurface_path}")

        self.copy_stl_btn.setText(translator.get("msg_success"))
        QTimer.singleShot(
            DEFAULT_SAVE_FEEDBACK_DURATION_MS,
            lambda: self.copy_stl_btn.setText(translator.get("btn_copy_stl")),
        )

    def _browse_polymesh_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            translator.get("dialog_select_export_dir"),
            "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if dir_path:
            self.polymesh_dir_input.setText(dir_path)

    def _copy_polymesh_files(self):
        if not self.case_path_input.text() or not self.case_name_input.text():
            return

        source_polymesh_dir = self.polymesh_dir_input.text()
        if not source_polymesh_dir:
            return
        
        case_name = self.case_name_input.text()
        case_path = Path(self.case_path_input.text()) / case_name
        target_polymesh_path = case_path / "constant" / "polyMesh"

        if not target_polymesh_path.exists():
            target_polymesh_path.mkdir(parents=True)

        for item in Path(source_polymesh_dir).iterdir():
            if item.is_file():
                shutil.copy2(item, target_polymesh_path / item.name)
                print(f"Copied {item} to {target_polymesh_path}")

        self.copy_polymesh_btn.setText(translator.get("msg_success"))
        QTimer.singleShot(
            DEFAULT_SAVE_FEEDBACK_DURATION_MS,
            lambda: self.copy_polymesh_btn.setText(translator.get("btn_copy_polymesh")),
        )

    def _rebuild_editor(self):
        for item in self.root_items:
            item.deleteLater()
        self.root_items.clear()

        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child and child.widget():
                child.widget().deleteLater()

        self._build_items_recursive(self.yaml_data, self.scroll_layout, 0)

    def _build_items_recursive(self, data: Any, parent_layout: QVBoxLayout, depth: int):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(key, str) and key.endswith("_options"):
                    continue
                options_key = f"{key}_options"
                opts = data.get(options_key) if isinstance(data, dict) else None
                item = YamlKeyValueItem(key, value, (key,), depth, options=opts)
                item.changed.connect(self._on_data_changed)
                self.root_items.append(item)
                parent_layout.addWidget(item)
        elif isinstance(data, list):
            for i, value in enumerate(data):
                item = YamlKeyValueItem(f"[{i}]", value, (i,), depth)
                item.changed.connect(self._on_data_changed)
                self.root_items.append(item)
                parent_layout.addWidget(item)

    def _on_data_changed(self):
        self._sync_root_items()

    def _sync_root_items(self):
        self.yaml_data.clear()
        for item in self.root_items:
            self.yaml_data[item.key] = item.get_value()

    def _save_yaml(self):
        if not self.current_file_path:
            return
        self._sync_root_items()
        with open(self.current_file_path, "w", encoding="utf-8") as f:
            yaml.dump(
                _sanitize(self.yaml_data),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
        self.save_btn.setText(translator.get("msg_success"))
        self.save_btn.setEnabled(False)
        QTimer.singleShot(
            DEFAULT_SAVE_FEEDBACK_DURATION_MS,
            lambda: (self.save_btn.setText(translator.get("btn_save")), self.save_btn.setEnabled(True)),
        )

    def _save_yaml_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translator.get("dialog_save_yaml_as"),
            "",
            "YAML Files (*.yaml *.yml);;All Files (*)",
        )
        if not file_path:
            return
        self._sync_root_items()
        save_path = Path(file_path)
        with open(save_path, "w", encoding="utf-8") as f:
            yaml.dump(
                _sanitize(self.yaml_data),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
        self.current_file_path = save_path
        self.file_label.setText(f"File: {save_path.name}")
        self.save_as_btn.setText(translator.get("msg_success"))
        QTimer.singleShot(
            DEFAULT_SAVE_FEEDBACK_DURATION_MS,
            lambda: self.save_as_btn.setText(translator.get("btn_save_as")),
        )

    def on_language_changed(self):
        self.file_label.setText(translator.get("file_label_default"))
        self.browse_btn.setText(translator.get("btn_browse"))
        self.save_btn.setText(translator.get("btn_save"))
        self.save_as_btn.setText(translator.get("btn_save_as"))
        self.case_name_label.setText(translator.get("case_name_label"))
        self.case_path_label.setText(translator.get("case_path_label"))
        self.case_path_input.setPlaceholderText(translator.get("placeholder_export_dir"))
        self.case_path_btn.setText(translator.get("btn_browse"))
        self.write_case_btn.setText(translator.get("btn_write_case"))
        self.stl_dir_label.setText(translator.get("stl_dir_label"))
        self.stl_dir_input.setPlaceholderText(translator.get("placeholder_stl_dir"))
        self.stl_dir_btn.setText(translator.get("btn_browse"))
        self.copy_stl_btn.setText(translator.get("btn_copy_stl"))
        self.polymesh_label.setText(translator.get("polymesh_label"))
        self.polymesh_dir_label.setText(translator.get("polymesh_dir_label"))
        self.polymesh_dir_input.setPlaceholderText(translator.get("placeholder_polymesh_dir"))
        self.polymesh_dir_btn.setText(translator.get("btn_browse"))
        self.copy_polymesh_btn.setText(translator.get("btn_copy_polymesh"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = YamlEditor()
    window.setWindowTitle("Case Editor")
    window.resize(480, 1080)
    window.show()
    sys.exit(app.exec())