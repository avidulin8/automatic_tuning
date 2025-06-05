import logging
import os
import time
from lupa import LuaRuntime
import subprocess

from evaluate_traj import get_traj_info
from evaluate_traj import eval_rpe
from automatic_tuning import AutomaticTuning

class CartographerTuning(AutomaticTuning):
    def __init__(self, study_name):
        super().__init__(study_name)

        lua = LuaRuntime(unpack_returned_tuples=True)
        with open('/home/arijan/Documents/Diplomski_rad/automatic_tuning/scripts/automatic_tuning/livox_cartographer_only.lua', 'r') as f:
            lua_code = f.read()
        lua.execute(lua_code)

        options = lua.globals().options
        self.options_dict = self.lua_table_to_dict(options)
        #print(self.options_dict)
        #print("lol")
    
    def setup(self, trial):
        num_accumulated_range_data = trial.suggest_uniform('num_accumulated_range_data', 1, 10)
        translation_weight = trial.suggest_int('translation_weight', 2, 20)
        rotation_weight = trial.suggest_int('rotation_weight', 2, 30)
        high_resolution_max_range = trial.suggest_uniform('high_resolution_max_range', 30, 200)

        self.options_dict["trajectory_builder"]["trajectory_builder_3d"]['num_accumulated_range_data'] = num_accumulated_range_data
        self.options_dict["trajectory_builder"]["trajectory_builder_3d"]['ceres_scan_matcher']['translation_weight'] = translation_weight
        self.options_dict["trajectory_builder"]["trajectory_builder_3d"]['ceres_scan_matcher']['rotation_weight'] = rotation_weight
        self.options_dict["trajectory_builder"]["trajectory_builder_3d"]['submaps']['high_resolution_max_range'] = high_resolution_max_range
    
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

        conf_filename = '/tmp/results/cartographer_config.lua'
        lua_table_str_options = self.lua_table_to_string(self.options_dict)
        lua_code2 = f"options = {lua_table_str_options}\n\nreturn options\n"

        with open(conf_filename, "w") as f:
            f.write(lua_code2)

        seq_id = 14
        gt_filename = f'/home/arijan/Documents/Diplomski_rad/automatic_tuning/scripts/automatic_tuning/{seq_id:02d}_tum.txt'
        bag_filename = f'/home/arijan/Documents/Diplomski_rad/Pastel_dataset/{seq_id:02d}.bag'
        traj_filename = f'/tmp/results/traj_{seq_id:02d}.txt'

        # run Cartographer
        gt_info = get_traj_info(gt_filename)
        print(gt_info['poses'])
        self.run_cartographer(bag_filename, conf_filename, traj_filename)
        traj_info = get_traj_info(traj_filename)
        print(traj_info['poses'])
        if 'poses' not in traj_info or traj_info['poses'] < gt_info['poses'] * 0.9:
            logger.info('[%.9f] Too many frames dropped (gt:%d traj:%d)' % (time.time(), gt_info['poses'], traj_info['poses']))
            return 1e9
        rpe = eval_rpe(gt_filename, traj_filename, delta_unit='m', delta=100, all_pairs=True, t_offset=-1000)

        os.makedirs('%s/results' % self.study_name, exist_ok=True)
        subprocess.run(['zip', '-r', '%s/results/results_%05d.zip' % (self.study_name, trial.number), '/tmp/results'])

        return rpe['rmse']

    def run_cartographer(self, bag_filename, conf_filename, traj_filename):
        subprocess.run(['roslaunch', '/home/arijan/Documents/Diplomski_rad/automatic_tuning/scripts/automatic_tuning/offline_cartographer.launch', 'rosbag:=%s' % bag_filename, 'conf:=%s' % conf_filename])

        subprocess.run(['rosrun', 'cartographer_ros', 'cartographer_dev_pbstream_trajectories_to_rosbag', '-input=%s.pbstream' % bag_filename, '-output=/tmp/integrated_to_init.bag'])
        subprocess.run(['python3', '/home/arijan/catkin_ws/src/rpg_trajectory_evaluation/scripts/dataset_tools/bag_to_pose.py', '/tmp/integrated_to_init.bag', 'trajectory_0', '--msg_type=TransformStamped', '--output=%s' % traj_filename])
        
        
    
def main():
    tuning = CartographerTuning('cartographer_tuning')

    x0 = {
        'num_accumulated_range_data': 10,
        'translation_weight': 5,
        'rotation_weight': 3,
        'high_resolution_max_range': 0.1
    }
    if tuning.log_id == 0:
        tuning.study.enqueue_trial(x0)

    tuning.optimize(n_trials=128)


if __name__ == '__main__':
    main()