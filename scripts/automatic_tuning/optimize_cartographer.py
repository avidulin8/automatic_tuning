import logging
import os
import time
from lupa import LuaRuntime
import yaml

from automatic_tuning import AutomaticTuning

class CartographerTuning(AutomaticTuning):
    def __init__(self, study_name):
        super().__init__(study_name)

        lua = LuaRuntime(unpack_returned_tuples=True)
        with open('/home/arijan/Documents/Diplomski_rad/automatic_tuning/scripts/automatic_tuning/livox_cartographer_only.lua', 'r') as f:
            lua_code = f.read()
        lua.execute(lua_code)
        self.robot_name = lua.globals().robot_name
        self.MAX_3D_RANGE = lua.globals().MAX_3D_RANGE
        self.trajectory_builder_3d = lua.globals().TRAJECTORY_BUILDER_3D

        self.trajectory_builder3d_dict = self.lua_table_to_dict(self.trajectory_builder_3d)

        #print("TRAJECTORY_BUILDER_3D:", self.trajectory_builder3d_dict["ceres_scan_matcher"]["ceres_solver_options"]["max_num_iterations"])
        print("Loaded Lua configuration successfully.")

    def lua_table_to_dict(self,lua_table):
        if not lua_table:
            return {}
        result = {}
        for key in lua_table:
            value = lua_table[key]
            if hasattr(value, 'keys'):
                result[key] = self.lua_table_to_dict(value)
            else:
                result[key] = value
        return result
    
    def setup(self, trial):
        num_accumulated_range_data = trial.suggest_uniform('num_accumulated_range_data', 1, 10)
        translation_weight = trial.suggest_int('translation_weight', 2, 20)
        rotation_weight = trial.suggest_int('ceres_rotation_weight', 2, 30)
        high_resolution_max_range = trial.suggest_uniform('high_resolution_max_range', 30, 200)

        self.trajectory_builder3d_dict['num_accumulated_range_data'] = num_accumulated_range_data
        self.trajectory_builder3d_dict['ceres_scan_matcher']['translation_weight'] = translation_weight
        self.trajectory_builder3d_dict['ceres_scan_matcher']['rotation_weight'] = rotation_weight
        self.trajectory_builder3d_dict['submaps']['high_resolution_max_range'] = high_resolution_max_range
        
    def lua_table_to_string(self, table, indent=0):
        lua_str = "{\n"
        indent_str = "  " * (indent + 1)

        for key, value in table.items():
            if isinstance(key, str):
                key_str = key
            else:
                key_str = f"[{key}]"

            lua_str += f"{indent_str}{key_str} = "

            if hasattr(value, "items"):  # nested table
                lua_str += self.lua_table_to_string(value, indent + 1)
            elif isinstance(value, str):
                lua_str += f'"{value}"'
            elif isinstance(value, bool):
                lua_str += "true" if value else "false"
            else:
                lua_str += str(value)

            lua_str += ",\n"

        lua_str += "  " * indent + "}"
        return lua_str


    def run(self, trial):
        logger = logging.getLogger()
        logger.info('[%.9f] Start trial %d' % (time.time(), trial.number))

        os.makedirs('/tmp/results', exist_ok=True)

        lua_table_str = self.lua_table_to_string(self.trajectory_builder_dict)
        lua_code = f"TRAJECTORY_BUILDER_3D = {lua_table_str}\n\nreturn TRAJECTORY_BUILDER_3D\n"
        with open("/tmp/modified_tb3d.lua", "w") as f:
            f.write(lua_code)

        return 10
    
def main():
    tuning = CartographerTuning('cartographer_tuning')

    x0 = {
        'num_accumulated_range_data': 60,
        'ceres_translation_weight': 5,
        'ceres_rotation_weight': 3,
        'submaps_high_resolution_max_range': 0.1
    }
    if tuning.log_id == 0:
        tuning.study.enqueue_trial(x0)

    tuning.optimize(n_trials=128)


if __name__ == '__main__':
    main()