import os
import json
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QGroupBox, QTextEdit, QMessageBox
)
from PySide6.QtCore import Signal, Qt
from translations import translator


class CaseRunner(QWidget):
    """Case Runner widget for OpenFOAM meshing operations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.foam_dir = ""
        self.foam_ver = ""
        self.working_dir = ""
        self._load_env()
        self._setup_ui()
        translator.language_changed.connect(self.on_language_changed)

    def _load_env(self):
        env_path = "liteSolve.json"
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                data = json.load(f)
                self.foam_dir = data.get("FOAMDIR", "")
                self.foam_ver = data.get("FOAMVER", "")

    def _save_env(self):
        with open("liteSolve.json", "w") as f:
            json.dump({
                "FOAMDIR": self.foam_dir,
                "FOAMVER": self.foam_ver
            }, f, indent=4)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # OpenFOAM Settings Group
        self.foam_group = QGroupBox(translator.get("foam_settings"))
        foam_layout = QVBoxLayout()

        foam_dir_row = QHBoxLayout()
        self.foam_dir_label = QLabel(translator.get("foam_dir_label"))
        foam_dir_row.addWidget(self.foam_dir_label)
        self.foam_dir_input = QLineEdit(self.foam_dir)
        self.foam_dir_input.setPlaceholderText("D:\\OpenFOAM\\2024")
        foam_dir_row.addWidget(self.foam_dir_input)
        self.foam_dir_browse = QPushButton(translator.get("btn_browse"))
        self.foam_dir_browse.clicked.connect(self._browse_foam_dir)
        foam_dir_row.addWidget(self.foam_dir_browse)
        foam_layout.addLayout(foam_dir_row)

        foam_ver_row = QHBoxLayout()
        self.foam_ver_label = QLabel(translator.get("foam_ver_label"))
        foam_ver_row.addWidget(self.foam_ver_label)
        self.foam_ver_input = QLineEdit(self.foam_ver)
        self.foam_ver_input.setPlaceholderText("12")
        foam_ver_row.addWidget(self.foam_ver_input)
        foam_layout.addLayout(foam_ver_row)

        self.save_btn = QPushButton(translator.get("btn_save_settings"))
        self.save_btn.clicked.connect(self._save_settings)
        foam_layout.addWidget(self.save_btn)

        self.foam_group.setLayout(foam_layout)
        layout.addWidget(self.foam_group)

        # Working Directory Group
        self.cwd_group = QGroupBox(translator.get("cwd_group"))
        cwd_layout = QHBoxLayout()
        self.cwd_input = QLineEdit(self.working_dir or os.getcwd())
        self.cwd_input.setPlaceholderText(translator.get("placeholder_cwd"))
        cwd_layout.addWidget(self.cwd_input)
        self.cwd_browse = QPushButton(translator.get("btn_browse"))
        self.cwd_browse.clicked.connect(self._browse_working_dir)
        cwd_layout.addWidget(self.cwd_browse)
        self.cwd_group.setLayout(cwd_layout)
        layout.addWidget(self.cwd_group)

        #######################################################

        # Meshing Commands Group
        self.mesh_group = QGroupBox(translator.get("mesh_group"))
        mesh_layout = QHBoxLayout()

        self.run_allmesh_bat_btn = QPushButton(translator.get("btn_run_allmesh"))
        self.run_allmesh_bat_btn.clicked.connect(lambda: self._run_mesh_command("Allmesh.bat"))
        mesh_layout.addWidget(self.run_allmesh_bat_btn)

        self.mesh_group.setLayout(mesh_layout)
        layout.addWidget(self.mesh_group)

        # Running Commands Group
        self.runner_group = QGroupBox(translator.get("runner_group"))
        runner_layout = QHBoxLayout()

        self.run_allrun_bat_btn = QPushButton(translator.get("btn_run_allrun"))
        self.run_allrun_bat_btn.clicked.connect(lambda: self._run_case_command("Allrun.bat"))
        runner_layout.addWidget(self.run_allrun_bat_btn)

        self.runner_group.setLayout(runner_layout)
        layout.addWidget(self.runner_group)

        # Visualization Group
        self.vis_group = QGroupBox(translator.get("vis_group"))
        vis_layout = QHBoxLayout()

        self.open_paraview_mesh_btn = QPushButton(translator.get("btn_open_mesh_paraview"))
        self.open_paraview_mesh_btn.clicked.connect(self._open_mesh_paraview)
        vis_layout.addWidget(self.open_paraview_mesh_btn)

        self.open_paraview_sim_btn = QPushButton(translator.get("btn_open_sim_paraview"))
        self.open_paraview_sim_btn.clicked.connect(self._open_sim_paraview)
        vis_layout.addWidget(self.open_paraview_sim_btn)

        self.vis_group.setLayout(vis_layout)
        layout.addWidget(self.vis_group)

        # Output Log
        self.log_label = QLabel(translator.get("log_label"))
        layout.addWidget(self.log_label)
        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setMaximumHeight(350)
        layout.addWidget(self.output_log)

    def on_language_changed(self):
        """Update all UI text when language changes."""
        self.foam_group.setTitle(translator.get("foam_settings"))
        self.foam_dir_label.setText(translator.get("foam_dir_label"))
        self.foam_dir_browse.setText(translator.get("btn_browse"))
        self.foam_ver_label.setText(translator.get("foam_ver_label"))
        self.save_btn.setText(translator.get("btn_save_settings"))
        self.cwd_group.setTitle(translator.get("cwd_group"))
        self.cwd_input.setPlaceholderText(translator.get("placeholder_cwd"))
        self.cwd_browse.setText(translator.get("btn_browse"))
        self.mesh_group.setTitle(translator.get("mesh_group"))
        self.run_allmesh_bat_btn.setText(translator.get("btn_run_allmesh"))
        self.runner_group.setTitle(translator.get("runner_group"))
        self.run_allrun_bat_btn.setText(translator.get("btn_run_allrun"))
        self.vis_group.setTitle(translator.get("vis_group"))
        self.open_paraview_mesh_btn.setText(translator.get("btn_open_mesh_paraview"))
        self.open_paraview_sim_btn.setText(translator.get("btn_open_sim_paraview"))
        self.log_label.setText(translator.get("log_label"))

    def _browse_foam_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, translator.get("dialog_select_foam_dir"))
        if dir_path:
            self.foam_dir_input.setText(dir_path)

    def _browse_working_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, translator.get("dialog_select_working_dir"))
        if dir_path:
            self.cwd_input.setText(dir_path)

    def _save_settings(self):
        self.foam_dir = self.foam_dir_input.text()
        self.foam_ver = self.foam_ver_input.text()
        self._save_env()
        QMessageBox.information(self, translator.get("msg_settings_saved"), translator.get("msg_settings_saved") + " - OpenFOAM")

    def _run_mesh_command(self, script_name: str):
        work_dir = self.cwd_input.text()
        if not work_dir or not os.path.isdir(work_dir):
            QMessageBox.warning(self, translator.get("msg_invalid_directory"), translator.get("msg_invalid_directory"))
            return

        script_path = os.path.join(work_dir, script_name)
        if not os.path.exists(script_path):
            script_path = os.path.join(work_dir, script_name)

        if not os.path.exists(script_path):
            QMessageBox.warning(self, translator.get("msg_script_not_found"), f"{translator.get('msg_script_not_found')}: {script_name}")
            return

        self.output_log.clear()
        self.output_log.append(f"Running {script_name} in {work_dir}...")
        self.output_log.repaint()

        try:
            env = os.environ.copy()
            env["FOAMDIR"] = self.foam_dir_input.text()
            env["FOAMVER"] = self.foam_ver_input.text()

            if script_name.endswith(".bat"):
                result = subprocess.run(
                    ["cmd", "/c", script_path],
                    cwd=work_dir,
                    env=env,
                    capture_output=True,
                    text=True
                )
            elif script_name.endswith(".ps1"):
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path],
                    cwd=work_dir,
                    env=env,
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ["bash", script_path],
                    cwd=work_dir,
                    env=env,
                    capture_output=True,
                    text=True
                )

            self.output_log.append(result.stdout)
            if result.stderr:
                self.output_log.append(f"STDERR:\n{result.stderr}")
            self.output_log.append(f"\nExit code: {result.returncode}")

        except Exception as e:
            self.output_log.append(f"Error: {str(e)}")

    def _run_case_command(self, script_name: str):
        work_dir = self.cwd_input.text()
        if not work_dir or not os.path.isdir(work_dir):
            QMessageBox.warning(self, translator.get("msg_invalid_directory"), translator.get("msg_invalid_directory"))
            return

        script_path = os.path.join(work_dir, script_name)
        if not os.path.exists(script_path):
            script_path = os.path.join(work_dir, script_name)

        if not os.path.exists(script_path):
            QMessageBox.warning(self, translator.get("msg_script_not_found"), f"{translator.get('msg_script_not_found')}: {script_name}")
            return

        self.output_log.clear()
        self.output_log.append(f"Running {script_name} in {work_dir}...")
        self.output_log.repaint()

        try:
            env = os.environ.copy()
            env["FOAMDIR"] = self.foam_dir_input.text()
            env["FOAMVER"] = self.foam_ver_input.text()

            if script_name.endswith(".bat"):
                result = subprocess.run(
                    ["cmd", "/c", script_path],
                    cwd=work_dir,
                    env=env,
                    capture_output=True,
                    text=True
                )
            elif script_name.endswith(".ps1"):
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path],
                    cwd=work_dir,
                    env=env,
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ["bash", script_path],
                    cwd=work_dir,
                    env=env,
                    capture_output=True,
                    text=True
                )

            self.output_log.append(result.stdout)
            if result.stderr:
                self.output_log.append(f"STDERR:\n{result.stderr}")
            self.output_log.append(f"\nExit code: {result.returncode}")

        except Exception as e:
            self.output_log.append(f"Error: {str(e)}")

    def _open_mesh_paraview(self):
        work_dir = self.cwd_input.text()
        if not work_dir or not os.path.isdir(work_dir):
            QMessageBox.warning(self, translator.get("msg_invalid_directory"), translator.get("msg_invalid_directory"))
            return

        paraview_path = os.path.join(self.foam_dir_input.text(), "AddOns", "ParaView", "bin", "paraview.exe")
        if not os.path.exists(paraview_path):
            QMessageBox.warning(self, translator.get("msg_paraview_not_found"), f"{translator.get('msg_paraview_not_found')}:\n{paraview_path}")
            return

        script_path = os.path.join(work_dir, "pvScriptMesh.py")
        if not os.path.exists(script_path):
            script_path = os.path.join(work_dir, "pvScriptMesh.py")

        if not os.path.exists(script_path):
            QMessageBox.warning(self, translator.get("msg_script_not_found"), f"{translator.get('msg_script_not_found')}: pvScriptMesh.py")
            return

        self.output_log.clear()
        self.output_log.append(f"Opening ParaView with {script_path}...")
        self.output_log.repaint()

        try:
            subprocess.Popen(
                ["powershell", "-Command", f"& '{paraview_path}' '{script_path}'"],
                cwd=work_dir,
                env=os.environ.copy()
            )
            self.output_log.append("ParaView launched successfully.")
        except Exception as e:
            self.output_log.append(f"Error: {str(e)}")

    def _open_sim_paraview(self):
        work_dir = self.cwd_input.text()
        if not work_dir or not os.path.isdir(work_dir):
            QMessageBox.warning(self, translator.get("msg_invalid_directory"), translator.get("msg_invalid_directory"))
            return

        paraview_path = os.path.join(self.foam_dir_input.text(), "AddOns", "ParaView", "bin", "paraview.exe")
        if not os.path.exists(paraview_path):
            QMessageBox.warning(self, translator.get("msg_paraview_not_found"), f"{translator.get('msg_paraview_not_found')}:\n{paraview_path}")
            return

        script_path = os.path.join(work_dir, "pvScript.py")
        if not os.path.exists(script_path):
            script_path = os.path.join(work_dir, "pvScript.py")

        if not os.path.exists(script_path):
            QMessageBox.warning(self, translator.get("msg_script_not_found"), f"{translator.get('msg_script_not_found')}: pvScript.py")
            return

        self.output_log.clear()
        self.output_log.append(f"Opening ParaView with {script_path}...")
        self.output_log.repaint()

        try:
            subprocess.Popen(
                ["powershell", "-Command", f"& '{paraview_path}' '{script_path}'"],
                cwd=work_dir,
                env=os.environ.copy()
            )
            self.output_log.append("ParaView launched successfully.")
        except Exception as e:
            self.output_log.append(f"Error: {str(e)}")