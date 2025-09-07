import re
import matplotlib.pyplot as plt

# Path to your log file
log_file_path = '/home/arijan/Documents/Diplomski_rad/automatic_tuning/cartographer_all_parameters_bag16_real/log/log_00.log'

# Regex pattern to extract trial number and value
pattern = r"Trial (\d+) finished with value: ([0-9.]+)"

# Containers for all trials
trial_numbers = []
trial_values = []

# Read and parse the log file
with open(log_file_path, 'r') as file:
    for line in file:
        match = re.search(pattern, line)
        if match:
            trial_num = int(match.group(1))
            value = float(match.group(2))
            trial_numbers.append(trial_num)
            trial_values.append(value)

# Filter every 2nd trial
filtered_x = [n for i, n in enumerate(trial_numbers) if n % 2 != 0]
filtered_y = [v for i, v in enumerate(trial_values) if trial_numbers[i] % 2 != 0]

# Find best trial (lowest value)
min_val = min(trial_values)
min_index = trial_values.index(min_val)
best_trial = trial_numbers[min_index]

# Plotting
plt.figure(figsize=(10, 6))
plt.plot(filtered_x, filtered_y, marker='o', linestyle='-', label='Every 2nd Trial')

# Highlight best trial
plt.plot(best_trial, min_val, 'go', markersize=10, label=f'Best Trial {best_trial} = {min_val:.3f}')

# Plot settings
plt.title("Optimization Value (Every 2nd Trial)")
plt.xlabel("Trial Number")
plt.ylabel("Optimization Value")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
