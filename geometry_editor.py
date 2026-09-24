"""
liteSolve - Geometry Processor Application
GUI, 3D STEP viewer, face selectors, selection exporters, and STL/trimesh processors.
Also includes features to print selected faces' XYZ locations and export the loaded STEP to BREP.
"""

import sys
import ctypes
import os
import math
import struct
from pathlib import Path
import numpy as np
import random
import json
import yaml
import math

# PySide6 imports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                QPushButton, QFileDialog, QMessageBox, QLineEdit, QLabel,
                                QListWidget, QListWidgetItem, QCheckBox, QSplitter)
from PySide6.QtGui import QScreen
from PySide6.QtCore import Qt

# Translation imports
from translations import translator

# VTK imports
from vtkmodules.vtkRenderingCore import (
    vtkRenderer,
    vtkRenderWindow,
    vtkTextActor3D,
    vtkActor,
)
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor
from vtkmodules.vtkCommonTransforms import vtkTransform

# QVTKRenderWindowInteractor for PySide6 integration
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

# CadQuery imports
import cadquery
from cadquery import cq, Assembly, Color
from cadquery.vis import show as cq_show


# ==========================================
# STEP / CAD Loading and Helper Functions
# ==========================================

def load_step_file(filename):
    """Load a STEP file using cadquery."""
    wp = cadquery.importers.importStep(filename)
    shape = wp.val()
    return shape


def get_model_center(shape):
    """Get the bounding box/geometric center of the shape."""
    shape_center = shape.Center()
    shape_bb = shape.BoundingBox()
    shapexlen, shapeylen, shapezlen = shape_bb.xlen, shape_bb.ylen, shape_bb.zlen
    print(f"model dimensions: x:{shapexlen}, y:{shapeylen}, z:{shapezlen}")
    geo_center = (shape_center.x, shape_center.y, shape_center.z)
    return geo_center

def get_model_bounds(shape):
    """Get the bounding box/geometric center of the shape."""
    geo_bb = shape.BoundingBox()
    geo_bounds = (geo_bb.xmin, geo_bb.xmax,
                  geo_bb.ymin,geo_bb.ymax,
                  geo_bb.zmin, geo_bb.zmax)
    return geo_bounds

def get_faces_with_centers(shape):
    """Extract all faces with their centers and normals from a shape."""
    faces = []
    face_list = shape.Faces()

    for i, face in enumerate(face_list):
        try:
            center = face.Center()
            normal = face.normalAt()
            faceBB = face.BoundingBox()
            xlen = faceBB.xlen
            ylen = faceBB.ylen
            zlen = faceBB.zlen
            fArea = face.Area()
            faces.append({
                'index': i,
                'face': face,
                'center': (center.x, center.y, center.z),
                'normal': (normal.x, normal.y, normal.z),
                'dims' : (xlen, ylen, zlen),
                'area': fArea
            })
        except Exception as e:
            print(f"Warning: Could not get center for face {i}: {e}")
    
    return faces


def calculate_label_orientation(normal: tuple) -> list:
    """Calculate the 3D text label orientation to align with face normal."""
    n = np.array(normal, dtype=float)
    n = n / np.linalg.norm(n)
    
    up = np.array([0.0, 0.0, 1.0])
    
    if np.abs(np.dot(n, up)) > 0.99:
        right = np.array([1.0, 0.0, 0.0])
    else:
        right = np.cross(up, n)
        right = right / np.linalg.norm(right)
        
    local_up = np.cross(n, right)
    rotation_matrix = np.column_stack((right, local_up, n))
    
    from scipy.spatial.transform import Rotation
    r = Rotation.from_matrix(rotation_matrix)
    euler_degrees = r.as_euler('xyz', degrees=True)
    
    return [float(euler_degrees[0]), float(euler_degrees[1]), float(euler_degrees[2])]


# ==========================================
# STL Trimesh Processing Functions
# ==========================================

def read_stl_facets(filepath):
    """
    Reads an STL file (detects auto Binary or ASCII) and extracts 
    only the raw facet data blocks.
    """
    if not os.path.exists(filepath):
        print(f"Warning: File not found -> {filepath}")
        return []
        
    facets = []
    
    # Read first 80 bytes to check if it's binary or ASCII
    with open(filepath, 'rb') as test_f:
        header = test_f.read(80)
        
    is_binary = False
    if len(header) == 80:
        with open(filepath, 'rb') as f:
            f.seek(80)
            try:
                count_bytes = f.read(4)
                if len(count_bytes) == 4:
                    num_triangles = struct.unpack('<I', count_bytes)[0]
                    file_size = os.path.getsize(filepath)
                    if file_size == 84 + (num_triangles * 50):
                        is_binary = True
            except Exception:
                pass

    if is_binary:
        with open(filepath, 'rb') as f:
            f.seek(84)
            while True:
                data = f.read(50)
                if len(data) < 50:
                    break
                floats = struct.unpack('<12f', data[:48])
                n = floats[0:3]
                v0 = floats[3:6]
                v1 = floats[6:9]
                v2 = floats[9:12]
                
                facet_str = (
                    f"  facet normal {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n"
                    f"    outer loop\n"
                    f"      vertex {v0[0]:.6f} {v0[1]:.6f} {v0[2]:.6f}\n"
                    f"      vertex {v1[0]:.6f} {v1[1]:.6f} {v1[2]:.6f}\n"
                    f"      vertex {v2[0]:.6f} {v2[1]:.6f} {v2[2]:.6f}\n"
                    f"    endloop\n"
                    f"  endfacet\n"
                )
                facets.append(facet_str)
    else:
        with open(filepath, 'r', errors='ignore') as f:
            current_facet = []
            in_facet = False
            for line in f:
                line_clean = line.strip().lower()
                if line_clean.startswith('facet normal') or in_facet:
                    in_facet = True
                    current_facet.append(line)
                    if line_clean.startswith('endfacet'):
                        facets.append("".join(current_facet))
                        current_facet = []
                        in_facet = False
                        
    return facets


def find_stl_files(directory):
    """
    Automatically find STL files in the directory and group by prefix.
    Looks for files matching: inlet*.stl, outlet*.stl, wall.stl
    """
    if not os.path.exists(directory):
        print(f"Warning: Directory not found -> {directory}")
        return {}
    
    files = os.listdir(directory)

    json_file_path = os.path.join(directory, "patches.json")

    with open(json_file_path, "r") as file:
        data = json.load(file)

    stl_files = [f for f in files if f.lower().endswith('.stl')]
    
    grouped = {'patches': []}
    
    for filename in stl_files:
        filepath = os.path.join(directory, filename)
        name_lower = filename.lower()
        
        if name_lower.startswith('patch'):
            grouped['patches'].append(filepath)
    
    for key in grouped:
        grouped[key].sort()
    
    return grouped

SNAPPYHEXMESH_PATH = Path(__file__).parent / "yaml-files" / "snappyhexmesh.yaml"
LAMINAR_PATH = Path(__file__).parent / "yaml-files" / "laminar.yaml"
LAMINAR_OPTIONS_PATH = Path(__file__).parent / "yaml-files" / "laminar-options.yaml"

def get_snappyhexmesh_yaml():
    if SNAPPYHEXMESH_PATH.exists():
        with open(SNAPPYHEXMESH_PATH, 'r') as f:
            return yaml.safe_load(f)
    return {}

SHM_CASE_DATA = get_snappyhexmesh_yaml()

def get_laminar_yaml():
    if LAMINAR_PATH.exists():
        with open(LAMINAR_PATH, 'r') as f:
            return yaml.safe_load(f)
    return {}

def get_laminar_options_yaml():
    if LAMINAR_OPTIONS_PATH.exists():
        with open(LAMINAR_OPTIONS_PATH, 'r') as f:
            return yaml.safe_load(f)
    return {}

LAMINAR_CASE_DATA = get_laminar_yaml()
LAMINAR_OPTIONS_CASE_DATA = get_laminar_options_yaml()

DEFAULT_STL_DIR = "./liteSolve-test-cases/stl"


def generate_openfoam_stls_auto(input_dir, output_multi, output_single):
    """
    Automatically detect and process STL files from input directory.
    """
    print("🚀 Starting Standalone STL Pipeline (Auto-detect mode)...")
    grouped_files = find_stl_files(input_dir)
    
    if not grouped_files or not any(grouped_files.values()):
        print("❌ Error: No STL files found in directory.")
        return
    
    print(f"\nFound files in '{input_dir}':")
    for prefix, files in grouped_files.items():
        if files:
            print(f"  {prefix}: {len(files)} file(s) - {[os.path.basename(f) for f in files]}")
    
    # VARIATION 1: Multi Solid Mesh (Extrude_Geometry.stl)
    print(f"\nGenerating Multi-Solid variant: {output_multi}...")
    with open(output_multi, 'w') as f:
        for patch_name, filepaths in grouped_files.items():
            if not filepaths:
                continue
            
            for filepath in filepaths:
                basename = os.path.splitext(os.path.basename(filepath))[0]
                solid_name = basename
                
                print(f"  Processing: {basename}...")
                facets = read_stl_facets(filepath)
                
                if facets:
                    f.write(f"solid {solid_name}\n")
                    for facet in facets:
                        f.write(facet)
                    f.write(f"endsolid {solid_name}\n")
    
    # VARIATION 2: Single Closed Mesh (MeshRefinement.stl)
    print(f"Generating Single-Closed variant: {output_single}...")
    all_facets = []
    
    for patch_name, filepaths in grouped_files.items():
        if not filepaths:
            continue
        for filepath in filepaths:
            print(f"  Reading: {os.path.basename(filepath)}...")
            facets = read_stl_facets(filepath)
            if facets:
                all_facets.extend(facets)
    
    with open(output_single, 'w') as f:
        f.write("solid MeshRefinement\n")
        for facet in all_facets:
            f.write(facet)
        f.write("endsolid MeshRefinement\n")

    print("\n🎉 Done! Files compiled cleanly for snappyHexMesh.")



# ==========================================
# Main GUI Window Class
# ==========================================

class GeometryProcessorWindow(QMainWindow):
    """Main window for geometry editor with STEP viewer and selectors."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(translator.get("geo_title"))
        
        # Maximize geometry editor layout space
        MyScn = QScreen
        self.setGeometry(0, 0, MyScn.availableGeometry(QApplication.primaryScreen()).width(), MyScn.availableGeometry(QApplication.primaryScreen()).height())

        # Store the shape state
        self.shape = None
        self.current_step_file = None
        self.step_geometry_center = None
        
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # We only have one single main splitter now to contain the editor column and options
        self.main_splitter = QSplitter(Qt.Horizontal) # type: ignore
        self.main_layout.addWidget(self.main_splitter)
        
        # Left container - 3D VTK View
        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        
        self.view_title = QLabel(translator.get("view_3d_title"))
        self.view_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.left_layout.addWidget(self.view_title)
        
        # VTK integration
        self.vtk_widget = QVTKRenderWindowInteractor(self.left_container)
        self.left_layout.addWidget(self.vtk_widget, stretch=1)
        
        self.render_window = self.vtk_widget.GetRenderWindow()
        self.renderer = vtkRenderer()
        self.renderer.SetBackground(1, 1, 1)  # White background
        self.render_window.AddRenderer(self.renderer)
        
        style = vtkInteractorStyleTrackballCamera()
        self.vtk_widget.SetInteractorStyle(style)
        
        self.main_splitter.addWidget(self.left_container)
        
        # Right container - Geometry Controls & Selection Exporters
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_container.setMaximumWidth(500)
        
        self.ctrl_title = QLabel(translator.get("ctrl_title"))
        self.ctrl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.right_layout.addWidget(self.ctrl_title)
        
        # File Action Row (Load STEP, Export to BREP)
        file_action_layout = QHBoxLayout()
        self.load_button = QPushButton(translator.get("btn_load_step"))
        self.load_button.clicked.connect(self.load_step_file_dialog)
        file_action_layout.addWidget(self.load_button)
        
        self.brep_button = QPushButton(translator.get("btn_export_brep"))
        self.brep_button.clicked.connect(self.export_to_brep)
        file_action_layout.addWidget(self.brep_button)
        self.right_layout.addLayout(file_action_layout)
        
        # Face selectors lists
        selectors_layout = QHBoxLayout()
        
        # Inlet
        inlet_col = QVBoxLayout()
        self.inlet_label = QLabel(translator.get("inlet_label"))
        self.inlet_list = QListWidget()
        self.inlet_list.setSelectionMode(QListWidget.MultiSelection) # type: ignore
        self.inlet_separate_checkbox = QCheckBox(translator.get("inlet_separate"))
        inlet_col.addWidget(self.inlet_label)
        inlet_col.addWidget(self.inlet_list)
        inlet_col.addWidget(self.inlet_separate_checkbox)
        
        # Outlet
        outlet_col = QVBoxLayout()
        self.outlet_label = QLabel(translator.get("outlet_label"))
        self.outlet_list = QListWidget()
        self.outlet_list.setSelectionMode(QListWidget.MultiSelection) # type: ignore
        self.outlet_separate_checkbox = QCheckBox(translator.get("outlet_separate"))
        outlet_col.addWidget(self.outlet_label)
        outlet_col.addWidget(self.outlet_list)
        outlet_col.addWidget(self.outlet_separate_checkbox)
        
        selectors_layout.addLayout(inlet_col)
        selectors_layout.addLayout(outlet_col)
        self.right_layout.addLayout(selectors_layout)
        
        # Export path row
        export_dir_row = QHBoxLayout()
        self.export_dir_input = QLineEdit()
        self.export_dir_input.setText(DEFAULT_STL_DIR)
        self.export_dir_input.setPlaceholderText(translator.get("placeholder_export_dir"))
        self.export_browse_button = QPushButton(translator.get("btn_browse"))
        self.export_browse_button.clicked.connect(self.browse_export_directory)
        export_dir_row.addWidget(self.export_dir_input)
        export_dir_row.addWidget(self.export_browse_button)
        self.right_layout.addLayout(export_dir_row)

        # Export Selected Faces button
        self.export_button = QPushButton(translator.get("btn_export_selected"))
        self.export_button.clicked.connect(self.export_all_selected_faces)
        self.right_layout.addWidget(self.export_button)
        
        # Separator line
        sep = QLabel()
        sep.setFrameStyle(QLabel.HLine | QLabel.Sunken) # type: ignore
        self.right_layout.addWidget(sep)
        
        # Trimesh processing section
        self.trimesh_title = QLabel(translator.get("trimesh_title"))
        self.trimesh_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.right_layout.addWidget(self.trimesh_title)
        
        stl_dir_row = QHBoxLayout()
        self.stl_dir_input = QLineEdit()
        self.stl_dir_input.setText(DEFAULT_STL_DIR)
        self.stl_dir_input.setPlaceholderText(translator.get("placeholder_stl_dir"))
        self.stl_browse_button = QPushButton(translator.get("btn_browse"))
        self.stl_browse_button.clicked.connect(self.browse_stl_directory)
        stl_dir_row.addWidget(self.stl_dir_input)
        stl_dir_row.addWidget(self.stl_browse_button)
        self.right_layout.addLayout(stl_dir_row)
        
        self.process_stl_button = QPushButton(translator.get("btn_process_stl"))
        self.process_stl_button.clicked.connect(self.process_stl_files)
        self.right_layout.addWidget(self.process_stl_button)

        self.update_shm_patch_data = QPushButton(translator.get("btn_update_shm_patches"))
        self.update_shm_patch_data.clicked.connect(self.update_shm_patches_layers_regions)
        self.right_layout.addWidget(self.update_shm_patch_data)

        self.update_shm_data = QPushButton(translator.get("btn_update_shm_model"))
        self.update_shm_data.clicked.connect(self.update_shm_model_data)
        self.right_layout.addWidget(self.update_shm_data)

        self.update_solver_data_btn = QPushButton(translator.get("btn_update_solver"))
        self.update_solver_data_btn.clicked.connect(self.update_solver_data)
        self.right_layout.addWidget(self.update_solver_data_btn)
        
        self.right_layout.addStretch()
        self.main_splitter.addWidget(self.right_container)
        
        # Set initial proportions
        self.main_splitter.setSizes([800, 400])
        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 1)
        
        # Store faces data for export
        self.faces_data = []
        self.text_actors = {}
        
        # Connect selections to live dynamic VTK updates
        self.inlet_list.itemChanged.connect(self.on_face_selection_changed)
        self.outlet_list.itemChanged.connect(self.on_face_selection_changed)
        
        # Initialize the VTK interactor
        self.vtk_widget.Initialize()
        self.vtk_widget.Start()
        
        # Connect to language change signal
        translator.language_changed.connect(self.on_language_changed)
        
    def on_language_changed(self):
        """Update all UI text when language changes."""
        self.setWindowTitle(translator.get("geo_title"))
        
        # Update labels
        for i in range(self.left_layout.count()):
            widget = self.left_layout.itemAt(i).widget()
            if isinstance(widget, QLabel) and "3D" in widget.text():
                widget.setText(translator.get("view_3d_title"))
                break
        
        for i in range(self.right_layout.count()):
            widget = self.right_layout.itemAt(i).widget()
            if isinstance(widget, QLabel):
                text = widget.text()
                if "Geometry Controls" in text:
                    widget.setText(translator.get("ctrl_title"))
                elif "Trimesh" in text:
                    widget.setText(translator.get("trimesh_title"))
        
        # Update buttons
        self.load_button.setText(translator.get("btn_load_step"))
        self.brep_button.setText(translator.get("btn_export_brep"))
        self.export_browse_button.setText(translator.get("btn_browse"))
        self.stl_browse_button.setText(translator.get("btn_browse"))
        self.export_button.setText(translator.get("btn_export_selected"))
        self.process_stl_button.setText(translator.get("btn_process_stl"))
        self.update_shm_patch_data.setText(translator.get("btn_update_shm_patches"))
        self.update_shm_data.setText(translator.get("btn_update_shm_model"))
        self.update_solver_data_btn.setText(translator.get("btn_update_solver"))
        
        # Update labels
        self.inlet_label.setText(translator.get("inlet_label"))
        self.outlet_label.setText(translator.get("outlet_label"))
        
        # Update checkboxes
        self.inlet_separate_checkbox.setText(translator.get("inlet_separate"))
        self.outlet_separate_checkbox.setText(translator.get("outlet_separate"))
        
        # Update placeholders
        self.export_dir_input.setPlaceholderText(translator.get("placeholder_export_dir"))
        self.stl_dir_input.setPlaceholderText(translator.get("placeholder_stl_dir"))
        
    def load_step_file_dialog(self):
        """Open file dialog to load a STEP file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            translator.get("dialog_open_step"),
            "",
            "STEP Files (*.step *.STEP);;All Files (*)"
        )
        if file_path:
            self.load_and_display_step(file_path)
            
    def load_and_display_step(self, file_path):
        """Load and render the step file and build selections."""
        try:
            self.renderer.RemoveAllViewProps()
            print(f"Loading STEP file: {file_path}")
            self.shape = load_step_file(file_path)
            self.current_step_file = file_path
            
            if self.shape is not None:
                self.step_geometry_center = list(get_model_center(self.shape))
                print(f"Computed geometry center: {self.step_geometry_center}")
            
            self.display_with_face_labels(self.shape)
        except Exception as e:
            QMessageBox.critical(self, translator.get("msg_error"), translator.get("msg_load_step_failed").format(error=str(e)))
            print(f"Error loading STEP file: {e}")
            
    def populate_face_lists(self):
        """Populate lists with face IDs and coordinates."""
        self.inlet_list.clear()
        self.outlet_list.clear()
        
        if not self.faces_data:
            return
            
        for fd in self.faces_data:
            face_id = fd['index']
            center = fd['center']
            display_text = f"ID: {face_id}"
            
            # Inlet item
            inlet_item = QListWidgetItem(display_text)
            inlet_item.setFlags(inlet_item.flags() | Qt.ItemIsUserCheckable) # type: ignore
            inlet_item.setCheckState(Qt.Unchecked) # type: ignore
            inlet_item.setData(Qt.UserRole, face_id) # type: ignore
            self.inlet_list.addItem(inlet_item)
            
            # Outlet item
            outlet_item = QListWidgetItem(display_text)
            outlet_item.setFlags(outlet_item.flags() | Qt.ItemIsUserCheckable) # type: ignore
            outlet_item.setCheckState(Qt.Unchecked) # type: ignore
            outlet_item.setData(Qt.UserRole, face_id) # type: ignore
            self.outlet_list.addItem(outlet_item)
            
    def display_with_face_labels(self, shape):
        """Display shape with face labels using VTK."""
        from cadquery.occ_impl.assembly import toVTKAssy
        from cadquery import Assembly, Color
        
        self.faces_data = get_faces_with_centers(shape)
        self.populate_face_lists()
        
        assy = Assembly(shape, color=Color(0.9, 0.9, 0.9, 0.8))
        for act in toVTKAssy(assy):
            self.renderer.AddActor(act)
            
        self.text_actors = {}

        areaList = []
        for faceAreas in self.faces_data:
            areaList.append(int(math.ceil(faceAreas['area'])))

        mnArea = min(areaList)
        mxArea = max(areaList)
        medArea = (mnArea + mxArea) / 2

        TARGET_LABEL_RATIO = 0.00075  # Label max dimension as fraction of face max dimension
        LABEL_OFFSET_DISTANCE = 0.05  # Distance above face surface (world units)
        BASE_FONT_SIZE = 96  # High resolution for texture quality; DO NOT scale this
        

        for face_data in self.faces_data:
            idx = face_data['index']
            center = face_data['center']
            normDir = face_data['normal']
            faceArea = face_data['area']
            normTuple = (normDir[0], normDir[1], normDir[2])
            
            # Create text label with face index and coordinates
            label_text = f"ID:{idx}"

            txtSize = 0.005 if faceArea <= medArea else 0.0075
            
            # Use vtkTextActor3D for 3D text positioned at faces
            text_actor = vtkTextActor3D()
            text_actor.SetInput(label_text)
            
            # Set text properties for rendering
            text_prop = text_actor.GetTextProperty()
            text_prop.SetFontSize(96) # set by the user, strictly, do not change
            text_prop.SetBold(True)
            text_prop.SetColor(0.0, 0.0, 0.0)  # Dark blue text

            
            # text_actor.SetOrientation(direction[0],direction[1],direction[2])
            newDirection = calculate_label_orientation(normTuple)
            text_actor.SetOrientation(newDirection[0], newDirection[1], newDirection[2])

            direction = (
                newDirection[0],
                newDirection[1],
                newDirection[2]
            )

            # 1. Get the normal vector from face_data
            nx, ny, nz = face_data['normal']
            
            # 2. Normalize the normal vector
            length = math.sqrt(nx*nx + ny*ny + nz*nz)
            if length > 0.001:
                normal_vec = np.array([nx/length, ny/length, nz/length])
            else:
                normal_vec = np.array([0, 0, 1])

            # 3. Calculate Orthogonal Basis (Right and Up vectors for the label)
            up_world = np.array([0.0, 0.0, 1.0])
            
            # If normal is close to vertical, use X as right, else cross product
            if np.abs(np.dot(normal_vec, up_world)) > 0.99:
                right_vec = np.array([1.0, 0.0, 0.0])
            else:
                right_vec = np.cross(up_world, normal_vec)
                right_vec = right_vec / np.linalg.norm(right_vec)
                
            local_up_vec = np.cross(normal_vec, right_vec)
            
            text_width_estimate = 3.0  # Approximate width of your label string in local units
            text_height_estimate = 0.5 # Approximate height of your label string in local units
            
            # Shift backwards along Right and Down along Local Up to center the text
            # center_offset = -(right_vec * (text_width_estimate * 0.5) + local_up_vec * (text_height_estimate * 0.5))
            center_offset = -(right_vec * text_width_estimate * + local_up_vec * text_height_estimate)
            # 5. Calculate Final Position
            # Move out along Normal (offset_distance) + Apply Centering Offset
            offset_distance = 0.05
            effective_offset = 0.05 # offset_distance if offset_distance != 0 else 1.5 
            
            final_position = (
                center[0] + normal_vec[0] * effective_offset + center_offset[0],
                center[1] + normal_vec[1] * effective_offset + center_offset[1],
                center[2] + normal_vec[2] * effective_offset + center_offset[2]
            )

            text_actor.SetPosition(final_position[0], final_position[1], final_position[2])

            # Set actor scale
            text_actor.SetScale(txtSize,txtSize,txtSize) # set by the user, strictly, do not change
            
            self.renderer.AddActor(text_actor)
            
            self.text_actors[idx] = {
                'actor': text_actor,
                'center': center,
                'label_text': f"ID:{idx}",
                'label_text_wall': f"ID:{idx} [Wall]",
                'label_text_inlet': f"ID:{idx} [Inlet]",
                'label_text_outlet': f"ID:{idx} [Outlet]"
            }

        # Add Axes
        axes = vtkAxesActor()
        axes.SetTotalLength(2, 2, 2)
        axes.SetAxisLabels(False)
        transform = vtkTransform()
        transform.Translate(-5.0, 0.0, 0.0)
        axes.SetUserTransform(transform)
        self.renderer.AddActor(axes)
        
        self.renderer.ResetCamera()
        self.render_window.Render()
        
    def get_checked_face_ids(self, list_widget):
        """Get checking face list indices."""
        face_ids = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.checkState() == Qt.Checked: # type: ignore
                face_ids.append(item.data(Qt.UserRole)) # type: ignore
        return face_ids
        
    def on_face_selection_changed(self, item):
        """Handle selection state updates on VTK viewer."""
        self.update_face_labels()
        
    def update_face_labels(self):
        """Refresh colors and label texts for all actors dynamically."""
        if not hasattr(self, 'text_actors') or not self.text_actors:
            return
            
        inlet_ids = set(self.get_checked_face_ids(self.inlet_list))
        outlet_ids = set(self.get_checked_face_ids(self.outlet_list))
        selected_ids = inlet_ids | outlet_ids
        
        for face_idx, actor_data in self.text_actors.items():
            text_actor = actor_data['actor']
            text_prop = text_actor.GetTextProperty()
            
            if face_idx in inlet_ids:
                text_actor.SetInput(actor_data['label_text_inlet'])
                text_prop.SetColor(0.0, 0.6, 0.0)  # Green
            elif face_idx in outlet_ids:
                text_actor.SetInput(actor_data['label_text_outlet'])
                text_prop.SetColor(0.8, 0.0, 0.0)  # Red
            elif selected_ids:
                text_actor.SetInput(actor_data['label_text_wall'])
                text_prop.SetColor(0.0, 0.0, 0.0)  # Black
            else:
                text_actor.SetInput(actor_data['label_text'])
                text_prop.SetColor(0.0, 0.0, 0.0)  # Black

        self.render_window.Render()
        
    def export_all_selected_faces(self):
        """Export inlet, outlet, and wall faces to their respective STL paths."""
        if not self.shape:
            QMessageBox.warning(self, translator.get("msg_no_shape"), translator.get("msg_load_step_first"))
            return
            
        if not self.faces_data:
            QMessageBox.warning(self, translator.get("msg_no_faces"), translator.get("msg_no_faces"))
            return
            
        inlet_ids = self.get_checked_face_ids(self.inlet_list)
        outlet_ids = self.get_checked_face_ids(self.outlet_list)
        
        exclude_ids = set(inlet_ids) | set(outlet_ids)
        wall_face_ids = [fd['index'] for fd in self.faces_data if fd['index'] not in exclude_ids]
        
        save_dir = self.export_dir_input.text().strip()
        if not save_dir or not os.path.isdir(save_dir):
            QMessageBox.warning(self, translator.get("msg_invalid_dir"), translator.get("msg_invalid_dir"))
            return
            
        exported_count = 0
        
        output_lines = []

        patches = 0

        cleaner = {}
        json_file_path = os.path.join(save_dir, "patches.json")
        with open(json_file_path, "w") as file:
            json.dump(cleaner, file, indent=4)

        # Export Inlet
        if inlet_ids:
            if self.inlet_separate_checkbox.isChecked():
                for i, face_id in enumerate(inlet_ids):

                    patches += 1
                    patch_label = f"patch_{patches}_1"

                    file_path = os.path.join(save_dir, f"patch_{patches}_1.stl")
                    self.export_single_face_to_stl(face_id, file_path)

                    json_file_path = os.path.join(save_dir, "patches.json")
                    with open(json_file_path, "r") as file:
                        data = json.load(file)
                    # new_entry = {f"{patch_label}": f"inlet_{i+1}"}
                    data[f"{patch_label}"] = f"inlet_{i+1}"

                    with open(json_file_path, "w") as file:
                        json.dump(data, file, indent=4)

                    with open(file_path, 'r') as file:
                            content = file.read()
        
                    modified_content = content.replace("solid", f"solid {patch_label}")
                    
                    with open(file_path, 'w') as file:
                        file.write(modified_content)

                    exported_count += 1
            else:
                patches += 1
                patch_label = f"patch_{patches}_1"
                file_path = os.path.join(save_dir, f"patch_{patches}_1.stl")

                json_file_path = os.path.join(save_dir, "patches.json")
                with open(json_file_path, "r") as file:
                    data = json.load(file)
                data[f"{patch_label}"] = f"inlet"
                with open(json_file_path, "w") as file:
                    json.dump(data, file, indent=4)


                if len(inlet_ids) > 1:
                    self.export_multiple_faces_to_stl(inlet_ids, file_path)
                else:
                    self.export_single_face_to_stl(inlet_ids[0], file_path)

                with open(file_path, 'r') as file:
                        content = file.read()
    
                modified_content = content.replace("solid", f"solid {patch_label}")
                
                with open(file_path, 'w') as file:
                    file.write(modified_content)

                exported_count += 1

            output_lines.append("Inlets:")
            for fid in inlet_ids:
                for fd in self.faces_data:
                    if fd['index'] == fid:
                        c = fd['center']
                        output_lines.append(f"  Face {fid}: X={c[0]:.4f}, Y={c[1]:.4f}, Z={c[2]:.4f}")
                
        # Export Outlet
        if outlet_ids:
            if self.outlet_separate_checkbox.isChecked():
                for i, face_id in enumerate(outlet_ids):

                    patches += 1
                    patch_label = f"patch_{patches}_1"

                    file_path = os.path.join(save_dir, f"patch_{patches}_1.stl")

                    json_file_path = os.path.join(save_dir, "patches.json")
                    with open(json_file_path, "r") as file:
                        data = json.load(file)
                    # new_entry = {f"{patch_label}": f"outlet_{i+1}"}
                    # data.append(new_entry)
                    data[f"{patch_label}"] = f"outlet_{i+1}"

                    with open(json_file_path, "w") as file:
                        json.dump(data, file, indent=4)

                    with open(file_path, 'r') as file:
                            content = file.read()
        
                    modified_content = content.replace("solid", f"solid {patch_label}")
                    
                    with open(file_path, 'w') as file:
                        file.write(modified_content)

                    exported_count += 1
            else:
                patches += 1
                patch_label = f"patch_{patches}_1"
                file_path = os.path.join(save_dir, f"patch_{patches}_1.stl")

                json_file_path = os.path.join(save_dir, "patches.json")
                with open(json_file_path, "r") as file:
                    data = json.load(file)
                # new_entry = {f"{patch_label}": f"outlet"}
                # data.append(new_entry)
                data[f"{patch_label}"] = f"outlet"

                with open(json_file_path, "w") as file:
                    json.dump(data, file, indent=4)

                if len(outlet_ids) > 1:
                    self.export_multiple_faces_to_stl(outlet_ids, file_path)
                else:
                    self.export_single_face_to_stl(outlet_ids[0], file_path)

                solid_label = "outlet"
                with open(file_path, 'r') as file:
                        content = file.read()
    
                modified_content = content.replace("solid", f"solid {patch_label}")
                
                with open(file_path, 'w') as file:
                    file.write(modified_content)

                exported_count += 1

            output_lines.append("Outlets:")
            for fid in inlet_ids:
                for fd in self.faces_data:
                    if fd['index'] == fid:
                        c = fd['center']
                        output_lines.append(f"  Face {fid}: X={c[0]:.4f}, Y={c[1]:.4f}, Z={c[2]:.4f}")
                
        # Export Wall
        if wall_face_ids:
            patches += 1
            patch_label = f"patch_{patches}_1"
            file_path = os.path.join(save_dir, f"patch_{patches}_1.stl")

            json_file_path = os.path.join(save_dir, "patches.json")
            with open(json_file_path, "r") as file:
                data = json.load(file)
            # new_entry = {f"{patch_label}": f"wall"}
            # data.append(new_entry)
            data[f"{patch_label}"] = f"wall"

            with open(json_file_path, "w") as file:
                json.dump(data, file, indent=4)

            if len(wall_face_ids) > 1:
                self.export_multiple_faces_to_stl(wall_face_ids, file_path)
            else:
                self.export_single_face_to_stl(wall_face_ids[0], file_path)

            solid_label = "wall"
            with open(file_path, 'r') as file:
                    content = file.read()

            modified_content = content.replace("solid", f"solid {patch_label}")
            
            with open(file_path, 'w') as file:
                file.write(modified_content)
            
            exported_count += 1

            output_lines.append("Walls:")
            for fid in wall_face_ids:
                for fd in self.faces_data:
                    if fd['index'] == fid:
                        c = fd['center']
                        output_lines.append(f"  Face {fid}: X={c[0]:.4f}, Y={c[1]:.4f}, Z={c[2]:.4f}")

        output_text = "\n".join(output_lines)
        print(output_text)

        print(patches)

        if exported_count > 0:
            QMessageBox.information(
                self,
                translator.get("msg_success"),
                f"{translator.get('msg_exported_stl_count').format(count=exported_count)}\n{save_dir}\n\n{translator.get('msg_face_ids')}\n{output_text}"
            )
            # Automatically populate STL directory input if empty
            if not self.stl_dir_input.text().strip():
                self.stl_dir_input.setText(save_dir)
        else:
            QMessageBox.warning(self, translator.get("msg_no_selection"), translator.get("msg_select_faces_export"))
            
    def export_single_face_to_stl(self, face_id: int, file_path: str):
        """Export single face to STL helper."""
        for fd in self.faces_data:
            if fd['index'] == face_id:
                try:
                    fd['face'].scale(0.001).exportStl(file_path, ascii=True)
                    # fd['face'].exportStl(file_path, ascii=True)
                    print(f"Exported face ID {face_id} -> {file_path}")
                except Exception as e:
                    print(f"Error exporting single face {face_id}: {e}")
                break
                
    def export_multiple_faces_to_stl(self, face_ids: list, file_path: str):
        """Export multiple faces merged into single compound STL."""
        faces = [fd['face'] for fd in self.faces_data if fd['index'] in face_ids]
        if not faces:
            return
            
        try:
            from OCP.BRep import BRep_Builder # type: ignore
            from OCP.TopoDS import TopoDS_Compound # type: ignore
            
            builder = BRep_Builder()
            compound = TopoDS_Compound()
            builder.MakeCompound(compound)
            
            for f in faces:
                builder.Add(compound, f.wrapped)
                
            shape = cq.Shape(compound) # type: ignore
            shape.scale(0.001).exportStl(file_path,ascii=True)
            # shape.exportStl(file_path,ascii=True)
            print(f"Exported compound of faces {face_ids} -> {file_path}")
        except Exception as e:
            print(f"Error exporting multiple faces: {e}")
            
        
    def export_to_brep(self):
        """Export the currently loaded shape to a BREP file."""
        if not self.shape:
            QMessageBox.warning(self, translator.get("msg_no_shape"), translator.get("msg_load_step_first"))
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translator.get("dialog_export_brep"),
            "model.brep",
            "BREP Files (*.brep *.BREP);;All Files (*)"
        )
        if not file_path:
            return
            
        try:
            from OCP.BRepTools import BRepTools # type: ignore
            success = BRepTools.Write_s(self.shape.wrapped, file_path) # type: ignore
            if success:
                QMessageBox.information(self, translator.get("msg_success"), translator.get("msg_export_brep_success").format(path=file_path))
                print(f"Exported shape to BREP -> {file_path}")
            else:
                raise RuntimeError("OCP BRepTools.Write_s returned false status")
        except Exception as e:
            QMessageBox.critical(self, translator.get("msg_error"), translator.get("msg_export_brep_failed").format(error=str(e)))
            print(f"Error exporting shape to BREP: {e}")
            
    def browse_stl_directory(self):
        """Browse folder containing individual inlet/outlet/wall STL files."""
        directory = QFileDialog.getExistingDirectory(
            self,
            translator.get("dialog_select_stl_dir"),
            self.stl_dir_input.text() if self.stl_dir_input.text() else "",
            QFileDialog.ShowDirsOnly # type: ignore
        )
        if directory:
            self.stl_dir_input.setText(directory)

    def browse_export_directory(self):
        """Browse folder for exporting selected faces."""
        directory = QFileDialog.getExistingDirectory(
            self,
            translator.get("dialog_select_export_dir"),
            self.export_dir_input.text() if self.export_dir_input.text() else "",
            QFileDialog.ShowDirsOnly # type: ignore
        )
        if directory:
            self.export_dir_input.setText(directory)
            
    def process_stl_files(self):
        """Merges files using trimesh auto-detection into Extrude_Geometry and MeshRefinement STL files."""
        stl_dir = self.stl_dir_input.text().strip()
        if not stl_dir or not os.path.isdir(stl_dir):
            QMessageBox.warning(self, translator.get("msg_invalid_dir"), translator.get("msg_invalid_dir"))
            self.browse_stl_directory()
            stl_dir = self.stl_dir_input.text().strip()
            if not stl_dir or not os.path.isdir(stl_dir):
                return
                
        output_multi = os.path.join(stl_dir, 'Extrude_Geometry.stl')
        output_single = os.path.join(stl_dir, 'MeshRefinement.stl')
        
        try:
            generate_openfoam_stls_auto(
                input_dir=stl_dir,
                output_multi=output_multi,
                output_single=output_single
            )
            QMessageBox.information(
                self,
                translator.get("msg_success"),
                translator.get("msg_process_stl_success").format(multi=f"- {output_multi}", single=f"- {output_single}")
            )
        except Exception as e:
            QMessageBox.critical(self, translator.get("msg_error"), translator.get("msg_process_stl_failed").format(error=str(e)))
            print(f"Error in STL processing: {e}")
            
    def update_shm_patches_layers_regions(self):
        stl_dir = self.stl_dir_input.text().strip()
        if not stl_dir or not os.path.isdir(stl_dir):
            QMessageBox.warning(self, translator.get("msg_invalid_dir"), translator.get("msg_invalid_dir"))
            self.browse_stl_directory()
            stl_dir = self.stl_dir_input.text().strip()
            if not stl_dir or not os.path.isdir(stl_dir):
                return
            
        json_file_path = os.path.join(stl_dir, "patches.json")
        with open(json_file_path, "r") as file:
            data = json.load(file)
        SHM_CASE_DATA["system"]["snappyHexMeshDict"]["geometry"]["\"Extrude_Geometry.stl\""]["regions"] = {}
        SHM_CASE_DATA["system"]["snappyHexMeshDict"]["addLayersControls"]["layers"] = {}

        regions = {}
        layers = {}
        for patch in data.keys():
            print(patch)
            regions[patch] = {"name": patch}
            layers[f"\"{patch}\""] = {"nSurfaceLayers" : 1, "expansionRatio" : 1.2}
        SHM_CASE_DATA["system"]["snappyHexMeshDict"]["geometry"]["\"Extrude_Geometry.stl\""]["regions"] = regions
        SHM_CASE_DATA["system"]["snappyHexMeshDict"]["addLayersControls"]["layers"] = layers
  
        with open(SNAPPYHEXMESH_PATH, 'w') as f:
            yaml.dump(SHM_CASE_DATA, f, default_flow_style=False, sort_keys=False)
            QMessageBox.information(self, translator.get("msg_success"), translator.get("msg_write_shm_success"))

    def update_shm_model_data(self):
        shapeData = self.shape
        shape_bb = shapeData.BoundingBox()
        bmesh_Scale = 0.001
        backgroundBox = shape_bb.enlarge(0.5)
        xdim, ydim, zdim = shape_bb.xlen, shape_bb.ylen, shape_bb.zlen

        SHM_CASE_DATA["system"]["blockMeshDict"]["cellsX"] = math.ceil(xdim)
        SHM_CASE_DATA["system"]["blockMeshDict"]["cellsX"] = math.ceil(ydim)
        SHM_CASE_DATA["system"]["blockMeshDict"]["cellsX"] = math.ceil(zdim)

        xin,xax,yin,yax,zin,zax = (backgroundBox.xmin * bmesh_Scale), (backgroundBox.xmax * bmesh_Scale), (backgroundBox.ymin * bmesh_Scale),(backgroundBox.ymax * bmesh_Scale), (backgroundBox.zmin * bmesh_Scale), (backgroundBox.zmax * bmesh_Scale)

        SHM_CASE_DATA["system"]["blockMeshDict"]["xMin"] = xin
        SHM_CASE_DATA["system"]["blockMeshDict"]["xMax"] = xax
        SHM_CASE_DATA["system"]["blockMeshDict"]["yMin"] = yin
        SHM_CASE_DATA["system"]["blockMeshDict"]["yMax"] = yax
        SHM_CASE_DATA["system"]["blockMeshDict"]["zMin"] = zin
        SHM_CASE_DATA["system"]["blockMeshDict"]["zMax"] = zax

        """Get a random point inside a model's volume space"""
        for i in range(100):
            x = random.uniform(shape_bb.xmin, shape_bb.xmax)
            y = random.uniform(shape_bb.ymin, shape_bb.ymax)
            z = random.uniform(shape_bb.zmin, shape_bb.zmax)
            modelPt = (x, y, z)
            ptInVolume = (x*bmesh_Scale,y*bmesh_Scale,z*bmesh_Scale)
            result = shapeData.isInside(modelPt, 1.0)
            if result:
                SHM_CASE_DATA["system"]["snappyHexMeshDict"]["castellatedMeshControls"]["locationInMesh"] = list(ptInVolume)
            
        with open(SNAPPYHEXMESH_PATH, 'w') as f:
            yaml.dump(SHM_CASE_DATA, f, default_flow_style=False, sort_keys=False)
            QMessageBox.information(self, translator.get("msg_success"), translator.get("msg_write_point_success").format(point=ptInVolume))

    def update_solver_data(self):
        stl_dir = self.stl_dir_input.text().strip()
        if not stl_dir or not os.path.isdir(stl_dir):
            QMessageBox.warning(self, translator.get("msg_invalid_dir"), translator.get("msg_invalid_dir"))
            self.browse_stl_directory()
            stl_dir = self.stl_dir_input.text().strip()
            if not stl_dir or not os.path.isdir(stl_dir):
                return
            
        json_file_path = os.path.join(stl_dir, "patches.json")
        with open(json_file_path, "r") as file:
            data = json.load(file)

        pBoundaries = {}
        uBoundaries = {}
        patchCreation = []

        for patchName, patchType in data.items():
            print(patchName, patchType)
            if "inlet" in patchType:
                pBoundaries[patchType] = {"type": "zeroGradient"}
                uBoundaries[patchType] = {"type": "flowRateInletVelocity",
                                      "volumetricFlowRate": 1.0000000000000001e-11,
                                      "value": "$internalField"}
            elif "outlet" in patchType:
                pBoundaries[patchType] = {"type": "totalPressure",
                                     "p0": ["uniform",601.2024048096192],
                                     "value": "$internalField"}
                uBoundaries[patchType] = {"type": "pressureInletOutletVelocity",
                                    "value": "$internalField"}
            elif "wall" in patchType:
                pBoundaries[patchType] = {"type": "zeroGradient"}
                uBoundaries[patchType] = {"type": "movingWallVelocity",
                                     "value": [0,0,0]}
            patchCreation.append({
                "name": patchType,
                "patchInfo": {"type":"patch"},
                "constructFrom": "patches",
                "patches": [f"\"{patchName}\""]
            })

        print(pBoundaries, uBoundaries, patchCreation)
        LAMINAR_CASE_DATA[0]["p"]["boundaryField"] = {}
        LAMINAR_CASE_DATA[0]["U"]["boundaryField"] = {}
        LAMINAR_CASE_DATA["system"]["createPatchDict"]["patches"] = []

        LAMINAR_CASE_DATA[0]["p"]["boundaryField"] = pBoundaries
        LAMINAR_CASE_DATA[0]["U"]["boundaryField"] = uBoundaries
        LAMINAR_CASE_DATA["system"]["createPatchDict"]["patches"] = patchCreation

        LAMINAR_OPTIONS_CASE_DATA[0]["p"]["boundaryField"] = {}
        LAMINAR_OPTIONS_CASE_DATA[0]["U"]["boundaryField"] = {}
        LAMINAR_OPTIONS_CASE_DATA["system"]["createPatchDict"]["patches"] = []

        LAMINAR_OPTIONS_CASE_DATA[0]["p"]["boundaryField"] = pBoundaries
        LAMINAR_OPTIONS_CASE_DATA[0]["U"]["boundaryField"] = uBoundaries
        LAMINAR_OPTIONS_CASE_DATA["system"]["createPatchDict"]["patches"] = patchCreation

        #change this
        with open(LAMINAR_PATH, 'w') as f:
            yaml.dump(LAMINAR_CASE_DATA, f, default_flow_style=False, sort_keys=False)
            # QMessageBox.information(self, "Success", f"Successfully wrote boundary & patch data to Laminar case")

        with open(LAMINAR_OPTIONS_PATH, 'w') as f:
            yaml.dump(LAMINAR_OPTIONS_CASE_DATA, f, default_flow_style=False, sort_keys=False)
            QMessageBox.information(self, translator.get("msg_success"), translator.get("msg_write_boundary_success"))

# ==========================================
# Application Entry Point
# ==========================================

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def main():
    if not is_admin():
        print("Requesting administrator privileges...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
        
    print("Running with administrator privileges!")
    app = QApplication(sys.argv)
    
    window = GeometryProcessorWindow()
    window.show()
    
    # Auto-load any step file present in the current directory as a default
    step_files = [f for f in os.listdir('.') if f.lower().endswith('.step')]
    if step_files:
        default_file = step_files[0]
        print(f"Auto-loading local STEP file: {default_file}")
        window.load_and_display_step(default_file)
        
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
