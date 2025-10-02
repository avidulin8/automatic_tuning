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


def run(optimal_conf_filename, seq_id):
    seq_id = seq_id
    logger = logging.getLogger()
    logger.info('[%.9f] Start test' % (time.time()))

    os.makedirs('/tmp/results', exist_ok=True)
    os.makedirs('/tmp/results/traj_eval', exist_ok=True)

    gt_filename = f'/home/arijan/Documents/Diplomski_rad/automatic_tuning/scripts/automatic_tuning/{seq_id:02d}_tum.txt'
    bag_filename = f'/home/arijan/Documents/Diplomski_rad/Pastel_dataset/{seq_id:02d}.bag'
    traj_filename = f'/tmp/results/traj_{seq_id:02d}.txt'

    # run Cartographer
    #gt_info = get_traj_info(gt_filename)
    #print(gt_info['poses'])
    run_cartographer(bag_filename, optimal_conf_filename, traj_filename)
    #traj_info = get_traj_info(traj_filename)
    #print(traj_info['poses'])
#if 'poses' not in traj_info or traj_info['poses'] < gt_info['poses'] * 0.6:
#    logger.info('[%.9f] Too many frames dropped (gt:%d traj:%d)' % (time.time(), gt_info['poses'], traj_info['poses']))
#    return 1e9
    #rpe = eval_rpe(gt_filename, traj_filename, delta_unit='m', delta=100, all_pairs=True, t_offset=-1000)
    data = run_rpg_ate(gt_filename, traj_filename)

    return data['trans']['rmse']

def run_cartographer(bag_filename, conf_filename, traj_filename):
    subprocess.run(['roslaunch', '/home/arijan/Documents/Diplomski_rad/automatic_tuning/scripts/automatic_tuning/offline_cartographer.launch', 'rosbag:=%s' % bag_filename, 'conf:=%s' % conf_filename])

    subprocess.run(['rosrun', 'cartographer_ros', 'cartographer_dev_pbstream_trajectories_to_rosbag', '-input=%s.pbstream' % bag_filename, '-output=/tmp/integrated_to_init.bag'])
    subprocess.run(['python3', '/home/arijan/catkin_ws/src/rpg_trajectory_evaluation/scripts/dataset_tools/bag_to_pose.py', '/tmp/integrated_to_init.bag', 'trajectory_0', '--msg_type=TransformStamped', '--output=%s' % traj_filename])

def run_rpg_ate(gt_filename, traj_filename):
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
    array = [16]

    # Path to the output file on Desktop
    output_file = "/home/arijan/Desktop/rmse_results_seq55.txt"

    with open(output_file, "a") as f:   # "w" = overwrite each run, use "a" to append
        for i in array:
            seq_id = i  # Example sequence ID, change as needed
            optimal_conf_filename = '/home/arijan/Documents/Diplomski_rad/automatic_tuning/cartographer_all_parameters_bag5_real/log/optimal.lua'

            rmse = run(optimal_conf_filename, seq_id)
            
            # Format output line
            line = f'RMSE for sequence {seq_id}: {rmse}\n'
            
            # Print to terminal
            print(line.strip())
            
            # Save to file
            f.write(line)

            # Clean up temp folder
            if os.path.exists("/tmp/results"):
                shutil.rmtree("/tmp/results")

    print(f"\n✅ Results saved to {output_file}")

if __name__ == '__main__':
    main()