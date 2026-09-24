from foamlib_patch import apply_all_patches
apply_all_patches()  # MUST be FIRST

from foamlib import FoamCase, FoamFile, Dimensioned, DimensionSet  # Now uses all patched versions

import yaml
import shutil
from pathlib import Path

YAML_CASE_FILE_PATH = Path("./yaml-files/laminar-options.yaml")

CASE_NAME = "SolverCase"
CASE_PATH = Path(f"./NewCases/{CASE_NAME}")

special_items = {
    "dimensions": {"mass": 0, "length": 0, "time": 0, "temperature": 0, "moles": 0, "current": 0, "luminous_intensity": 0},
    "headerLess": ["alphaDivScheme", "cAlpha", "turbulenceLib"],
    "Tupled": ["fvSchemes"]
}


def load_solver_proc_vals(yaml_file_path: Path = None):
    path = yaml_file_path or YAML_CASE_FILE_PATH
    if path.exists():
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    return {"key": "vals"}


def setup_case_paths(case_path: Path):
    zero_path = case_path / "0"
    constant_path = case_path / "constant"
    system_path = case_path / "system"

    if case_path.exists():
        shutil.rmtree(case_path)

    case_path.mkdir(parents=True)
    zero_path.mkdir()
    constant_path.mkdir()
    system_path.mkdir()

    foam_scripts_path = Path("./FoamScripts")
    for item in foam_scripts_path.iterdir():
        if item.is_file():
            shutil.copy2(item, case_path / item.name)

    return zero_path, constant_path, system_path


def add_trisurface(case_path: Path):
    trisurface_path = case_path / "constant" / "triSurface"
    if not trisurface_path.exists():
        trisurface_path.mkdir(parents=True)
    return trisurface_path


def write_case(case_data: dict, case_name: str, case_path: Path):
    def dimension_writer(foam_file_key, dimension, value=None):
        dim_set = DimensionSet(
            mass=dimension[0], length=dimension[1], time=dimension[2],
            temperature=dimension[3], moles=dimension[4],
            current=dimension[5], luminous_intensity=dimension[6]
        )
        if value is None:
            foam_file[foam_file_key] = dim_set
        else:
            foam_file[foam_file_key] = Dimensioned(value, dim_set)

    def header_less_writer(file_content):
        multi_line = ""
        keys = list(file_content.keys())
        if len(keys) == 1:
            val = list(file_content.values())[0]
            return f"{keys[0]} {val};" if val is not None else f"{keys[0]}"
        for item_key in keys:
            item_value = file_content.get(item_key)
            if item_value is not None:
                multi_line += f"{item_key} {item_value};\n"
            else:
                multi_line += f"{item_key}\n"
        return multi_line

    items_copy = {
        "dimensions": {"mass": 0, "length": 0, "time": 0, "temperature": 0, "moles": 0, "current": 0, "luminous_intensity": 0},
        "headerLess": ["alphaDivScheme", "cAlpha", "turbulenceLib"],
        "Tupled": ["fvSchemes", "controlDict", "blockMeshDict"]
    }

    case = FoamCase(case_path)

    for folder, file_dict in case_data.items():
        for file_name, file_content in file_dict.items():
            for content_key in file_content.keys():
                value_content = file_content.get(content_key)
                if isinstance(value_content, dict):
                    keys_to_remove = [k for k in value_content.keys() if k.endswith("_options")]
                    for key in keys_to_remove:
                        del value_content[key]
                if file_name in items_copy["headerLess"]:
                    print(f"headerless: {file_name}")
                    file_path = f"{case_path}/{folder}/{file_name}"
                    with open(file_path, "w", encoding="utf-8") as out_file:
                        out_file.write(header_less_writer(file_content))
                else:
                    with case.file(f"{folder}/{file_name}") as foam_file:
                        if content_key in items_copy.keys():
                            for key, val in file_content.get(content_key).items():
                                items_copy[content_key][key] = val
                            dims = [val for key, val in items_copy[content_key].items()]
                            dimension_writer(foam_file_key=content_key, dimension=dims, value=None)
                        elif isinstance(value_content, dict) and "dimensions" in value_content and "value" in value_content:
                            for key, val in value_content.items():
                                dims = []
                                dim_set_val = 0.0
                                if key in items_copy.keys():
                                    for k, v in value_content.get(key).items():
                                        items_copy[key][k] = v
                                    dims = [val for key, val in items_copy[key].items()]
                                    dim_set_val = dict(value_content.items())["value"]
                                    dimension_writer(foam_file_key=content_key, dimension=dims, value=dim_set_val)
                        else:
                            foam_file[content_key] = file_content.get(content_key)