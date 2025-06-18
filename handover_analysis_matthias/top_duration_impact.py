import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

# Set style for better-looking plots
plt.style.use('default')

# Input/Output settings
INPUT_DIR = './data/analysis/handover_duration'
OUTPUT_DIR = './handover_keypoints_visualisations'

def load_and_process_data(category):
    """Load and process data for a specific category."""
    file_path = os.path.join(INPUT_DIR, f"duration_{category}_role_level.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")
    
    df = pd.read_csv(file_path)
    
    # Calculate average duration for each handover pair
    handover_stats = df.groupby('most_frequent_handover').agg({
        'duration': ['mean', 'count']
    }).reset_index()
    
    # Sort by mean duration and get top 10
    top_handovers = handover_stats.sort_values(('duration', 'mean'), ascending=False).head(10)
    
    return top_handovers['most_frequent_handover'].tolist(), top_handovers[('duration', 'mean')].tolist()

def create_comparison_plot(before_handovers, before_durations, after_handovers, after_durations):
    """Create the comparison plot."""
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

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save the plot
    plt.savefig(os.path.join(OUTPUT_DIR, 'top_10_duration_impact_comparison.png'), dpi=300, bbox_inches='tight')
    plt.close()

def main():
    try:
        # Load data for both categories
        before_handovers, before_durations = load_and_process_data('3_way_before')
        after_handovers, after_durations = load_and_process_data('3_way_after')
        
        # Create the comparison plot
        create_comparison_plot(before_handovers, before_durations, after_handovers, after_durations)
        print("Plot has been generated successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 
def main():
    try:
        # Load data for both categories
        before_handovers, before_durations = load_and_process_data('3_way_before')
        after_handovers, after_durations = load_and_process_data('3_way_after')
        
        # Create the comparison plot
        create_comparison_plot(before_handovers, before_durations, after_handovers, after_durations)
        print("Plot has been generated successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 