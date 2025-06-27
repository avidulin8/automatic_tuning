import logging
import os
import time
import shutil
from lupa import LuaRuntime
import subprocess
import yaml
import optuna

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
        #print("pomocna linija")
    
    def setup(self, trial):
        translation_weight = trial.suggest_int('translation_weight', 1, 10)
        rotation_weight = trial.suggest_int('rotation_weight', 1, 100)
        #high_resolution = trial.suggest_float('high_resolution', 0.1, 0.35)
        num_range_data = trial.suggest_int('num_range_data', 600, 900)
        voxel_filter_size = trial.suggest_float('voxel_filter_size', 0.05, 0.4, step=0.001)

        self.options_dict["trajectory_builder"]["trajectory_builder_3d"]['ceres_scan_matcher']['translation_weight'] = translation_weight
        self.options_dict["trajectory_builder"]["trajectory_builder_3d"]['ceres_scan_matcher']['rotation_weight'] = rotation_weight
        self.options_dict["trajectory_builder"]["trajectory_builder_3d"]['submaps']['num_range_data'] = num_range_data
        self.options_dict["trajectory_builder"]["trajectory_builder_3d"]['voxel_filter_size'] = voxel_filter_size
    
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
        os.makedirs('/tmp/results/traj_eval', exist_ok=True)

        conf_filename = '/tmp/results/cartographer_config.lua'
        lua_table_str_options = self.lua_table_to_string(self.options_dict)
        lua_code2 = f"options = {lua_table_str_options}\n\nreturn options\n"

        with open(conf_filename, "w") as f:
            f.write(lua_code2)

        rmse_list = []
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
    #if 'poses' not in traj_info or traj_info['poses'] < gt_info['poses'] * 0.6:
    #    logger.info('[%.9f] Too many frames dropped (gt:%d traj:%d)' % (time.time(), gt_info['poses'], traj_info['poses']))
    #    return 1e9
        #rpe = eval_rpe(gt_filename, traj_filename, delta_unit='m', delta=100, all_pairs=True, t_offset=-1000)
        data = self.run_rpg_ate(gt_filename, traj_filename)
    #print(rpe["rmse"])
        os.makedirs('%s/results' % self.study_name, exist_ok=True)
        subprocess.run(['zip', '-r', '%s/results/results_%05d.zip' % (self.study_name, trial.number), '/tmp/results'])

        return data['trans']['rmse']

    def run_cartographer(self, bag_filename, conf_filename, traj_filename):
        subprocess.run(['roslaunch', '/home/arijan/Documents/Diplomski_rad/automatic_tuning/scripts/automatic_tuning/offline_cartographer.launch', 'rosbag:=%s' % bag_filename, 'conf:=%s' % conf_filename])

        subprocess.run(['rosrun', 'cartographer_ros', 'cartographer_dev_pbstream_trajectories_to_rosbag', '-input=%s.pbstream' % bag_filename, '-output=/tmp/integrated_to_init.bag'])
        subprocess.run(['python3', '/home/arijan/catkin_ws/src/rpg_trajectory_evaluation/scripts/dataset_tools/bag_to_pose.py', '/tmp/integrated_to_init.bag', 'trajectory_0', '--msg_type=TransformStamped', '--output=%s' % traj_filename])
    
    def run_rpg_ate(self, gt_filename, traj_filename):
        shutil.copy(gt_filename, '/tmp/results/traj_eval/stamped_groundtruth.txt')
        shutil.copy(traj_filename, '/tmp/results/traj_eval/stamped_traj_estimate.txt')
        subprocess.run(
            ['rosrun', 'rpg_trajectory_evaluation', 'analyze_trajectory_single.py', 'traj_eval'],
            cwd='/tmp/results'
        )
        yaml_path = '/tmp/results/traj_eval/saved_results/traj_est/absolute_err_statistics_sim3_-1.yaml'
        with open(yaml_path, 'r') as f:
            data=yaml.safe_load(f)
        return data
    
def main():
    tuning = CartographerTuning('cartographer_tuning_without_glob_slam')

    x0 = {
        'translation_weight': 5,
        'rotation_weight': 10,
        'voxel_filter_size': 0.1,
        'num_range_data': 700
    }
    if tuning.log_id == 0:
        tuning.study.enqueue_trial(x0)

    tuning.optimize(n_trials=128)
    #testiranje funkcije za importances
    importances_dict=optuna.importance.get_param_importances(study=tuning.study, normalize=False, params=['translation_weight','rotation_weight','num_range_data','voxel_filter_size','optimize_every_n_nodes'])
    print(importances_dict)

if __name__ == '__main__':
    main()