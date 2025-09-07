import re
import ast
from lupa import LuaRuntime
from pathlib import Path

def lua_table_to_dict(lua_table):
        if not lua_table:
            return {}
        result = {}
        for key in lua_table:
            value = lua_table[key]
            if hasattr(value, 'keys'):
                result[key] = lua_table_to_dict(value)
            else:
                result[key] = value
        return result

def lua_table_to_string(table, indent=0):
    lua_str = "{\n"
    indent_str = "  " * (indent + 1)

    for key, value in table.items():
        if isinstance(key, str):
            key_str = key
        else:
            key_str = f"[{key}]"

        lua_str += f"{indent_str}{key_str} = "

        if hasattr(value, "items"):  # nested table
            lua_str += lua_table_to_string(value, indent + 1)
        elif isinstance(value, str):
            lua_str += f'"{value}"'
        elif isinstance(value, bool):
            lua_str += "true" if value else "false"
        else:
            lua_str += str(value)

        lua_str += ",\n"

    lua_str += "  " * indent + "}"
    return lua_str
    
def extract_best_trial_parameters(log_path): # log .txt file path

    with open(log_path, 'r') as file:
        lines = file.readlines()

    best_trial_line = None
    for line in reversed(lines):
        if "Best is trial" in line:
            best_trial_line = line
            break

    match = re.search(r'Best is trial (\d+)', best_trial_line)
    best_trial_num = int(match.group(1)) if match else None

    best_trial_params_line = None
    for line in lines:
        if f"Trial {best_trial_num} finished with value" in line:
            best_trial_params_line = line
            break

    params_match = re.search(r'parameters:\s*(\{.*\})', best_trial_params_line)
    params_dict = ast.literal_eval(params_match.group(1)) if params_match else {}

    print("Best Trial Number:", best_trial_num)
    print("Best Trial Parameters:", params_dict)

    return params_dict

def write_to_lua_file(params_dict, filename):
    lua = LuaRuntime(unpack_returned_tuples=True)
    with open('/home/arijan/Documents/Diplomski_rad/automatic_tuning/scripts/automatic_tuning/livox_cartographer_only.lua', 'r') as f:
        lua_code = f.read()
    lua.execute(lua_code)

    options = lua.globals().options
    options_dict = lua_table_to_dict(options)
    #banana
    options_dict["trajectory_builder"]["trajectory_builder_3d"]['ceres_scan_matcher']['translation_weight'] = params_dict["translation_weight"]
    options_dict["trajectory_builder"]["trajectory_builder_3d"]['ceres_scan_matcher']['rotation_weight'] = params_dict["rotation_weight"]
    options_dict["trajectory_builder"]["trajectory_builder_3d"]['submaps']['high_resolution'] = params_dict["high_resolution"]
    options_dict["trajectory_builder"]["trajectory_builder_3d"]['submaps']['low_resolution'] = params_dict["low_resolution"]
    options_dict["trajectory_builder"]["trajectory_builder_3d"]['submaps']['num_range_data'] = params_dict["num_range_data"]
    options_dict["trajectory_builder"]["trajectory_builder_3d"]['voxel_filter_size'] = params_dict["voxel_filter_size"]
    options_dict["trajectory_builder"]["trajectory_builder_3d"]['max_range'] = params_dict["max_range"]
    options_dict["trajectory_builder"]["trajectory_builder_3d"]['high_resolution_adaptive_voxel_filter']['max_length'] = params_dict["high_res_max_length"]
    options_dict["trajectory_builder"]["trajectory_builder_3d"]['high_resolution_adaptive_voxel_filter']['min_num_points'] = params_dict["high_res_min_num_points"]
    options_dict["trajectory_builder"]["trajectory_builder_3d"]['high_resolution_adaptive_voxel_filter']['max_range'] = params_dict["high_res_max_range"]
    options_dict["trajectory_builder"]["trajectory_builder_3d"]['low_resolution_adaptive_voxel_filter']['max_length'] = params_dict["low_res_max_length"]
    options_dict["trajectory_builder"]["trajectory_builder_3d"]['low_resolution_adaptive_voxel_filter']['min_num_points'] = params_dict["low_res_min_num_points"]
    options_dict["trajectory_builder"]["trajectory_builder_3d"]['low_resolution_adaptive_voxel_filter']['max_range'] = params_dict["low_res_max_range"]

    lua_table_str_options = lua_table_to_string(options_dict)
    lua_code2 = f"options = {lua_table_str_options}\n\nreturn options\n"

    with open(filename, "w") as f:
        f.write(lua_code2)
    
def write_params_txt(params_dict, txt_path, append=False):
    """
    Save extracted hyperparameters to a human-readable .txt file.
    Format: one 'key: value' per line. Floats use full precision.
    """
    # Optional: fix an order so files are consistent
    preferred_order = [
        "translation_weight", "rotation_weight",
        "high_resolution", "low_resolution",
        "num_range_data", "voxel_filter_size", "max_range",
        "high_res_max_length", "high_res_min_num_points", "high_res_max_range",
        "low_res_max_length", "low_res_min_num_points", "low_res_max_range"
    ]
    keys = [k for k in preferred_order if k in params_dict] + [k for k in params_dict.keys() if k not in preferred_order]

    mode = "a" if append else "w"
    txt_path = Path(txt_path)
    txt_path.parent.mkdir(parents=True, exist_ok=True)

    with open(txt_path, mode) as f:
        for k in keys:
            v = params_dict[k]
            if isinstance(v, float):
                f.write(f"{k}: {v:.16g}\n")  # high precision, no trailing zeros explosion
            else:
                f.write(f"{k}: {v}\n")

def main():
    #define log bile from which you want to extract the best trial parameters
    log_path = '/home/arijan/Documents/Diplomski_rad/automatic_tuning/cartographer_all_parameters_bag8_real/log/log_00.txt' 
    params_dict = extract_best_trial_parameters(log_path=log_path)
    #define new lua file name where you want to write the best parameters
    new_lua_filename = '/home/arijan/Documents/Diplomski_rad/automatic_tuning/cartographer_all_parameters_bag8_real/log/optimal.lua'
    write_to_lua_file(params_dict, new_lua_filename)

    txt_out = '/home/arijan/Documents/Diplomski_rad/automatic_tuning/cartographer_all_parameters_bag8_real/log/best_params.txt'
    write_params_txt(params_dict, txt_out, append=False)

if __name__ == '__main__':
    main()
