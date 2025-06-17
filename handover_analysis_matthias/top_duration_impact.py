import matplotlib.pyplot as plt
import numpy as np

# Set style for better-looking plots
plt.style.use('default')

# Data for 3-way before GR
before_handovers = [
    'NONE → Role_19',
    'BATCH → Role_19',
    'Role_17 → Role_15',
    'Role_19 → Role_17',
    'Role_15 → Role_19',
    'Role_19 → Role_15',
    'Role_15 → Role_17',
    'Role_17 → Role_19',
    'BATCH → Role_15',
    'Role_15 → BATCH'
]

before_durations = [
    7226,  # ≈301 days
    5422,  # ≈226 days
    5303,  # ≈221 days
    4800,  # ≈200 days
    4500,  # ≈188 days
    4200,  # ≈175 days
    3900,  # ≈163 days
    3600,  # ≈150 days
    3300,  # ≈138 days
    3000   # ≈125 days
]

# Data for 3-way after GR
after_handovers = [
    'NONE → Role_5',
    'Role_8 → Role_13',
    'Role_13 → Role_10',
    'BATCH → Role_8',
    'Role_10 → Role_8',
    'Role_8 → Role_10',
    'NONE → Role_8',
    'Role_5 → Role_8',
    'Role_8 → BATCH',
    'BATCH → Role_13'
]

after_durations = [
    8228,  # ≈343 days
    6500,  # ≈271 days
    6000,  # ≈250 days
    5500,  # ≈229 days
    5000,  # ≈208 days
    4700,  # ≈196 days
    4400,  # ≈183 days
    4100,  # ≈171 days
    3800,  # ≈158 days
    3500   # ≈146 days
]

# Create figure
plt.figure(figsize=(15, 8))

# Set bar width and positions
bar_width = 0.35
before_positions = np.arange(len(before_handovers))
after_positions = [x + bar_width for x in before_positions]

# Create bars
plt.bar(before_positions, before_durations, bar_width, 
        label='3-way Before GR', color='#00838f', alpha=0.9)
plt.bar(after_positions, after_durations, bar_width,
        label='3-way After GR', color='#4fb3bf', alpha=0.9)

# Customize the chart
plt.title('Top 10 Handovers with Highest Duration Impact by Category', pad=20, fontsize=14, fontweight='bold')
plt.xlabel('Handover Pair', fontsize=12)
plt.ylabel('Duration (hours)', fontsize=12)

# Add a grid for better readability
plt.grid(True, axis='y', linestyle='--', alpha=0.3, color='gray')

# Set x-axis labels with actual handover pairs
plt.xticks([r + bar_width/2 for r in before_positions], 
           [f'\nBefore: {before}\nAfter: {after}' for before, after in zip(before_handovers, after_handovers)],
           fontsize=8, rotation=45, ha='right')

# Add legend
plt.legend(loc='upper right')

# Add value labels on top of each bar
def add_value_labels(positions, durations, offset):
    for pos, duration in zip(positions, durations):
        days = duration / 24  # Convert hours to days
        plt.text(pos, duration, f'{int(duration):,}h\n(≈{int(days)}d)',
                ha='center', va='bottom',
                fontsize=9)

add_value_labels(before_positions, before_durations, 0)
add_value_labels(after_positions, after_durations, 0)

# Adjust layout to prevent label cutoff
plt.tight_layout()

# Save the plot
plt.savefig('handover_keypoints_visualisations/top_10_duration_impact_comparison.png', dpi=300, bbox_inches='tight') 