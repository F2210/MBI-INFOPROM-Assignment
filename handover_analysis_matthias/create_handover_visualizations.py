import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# Set output directory
OUTPUT_DIR = 'handover_analysis_matthias/output/visualizations'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Set style for scientific publication
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = [12, 8]
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 16

# Define custom colors
PRIMARY_COLOR = '#00838f'
SECONDARY_COLOR = '#025162'
COLOR_PALETTE = [PRIMARY_COLOR, SECONDARY_COLOR] + sns.color_palette("Blues_r", 6)

# Read the data
handovers_df = pd.read_csv('data/analysis/handovers/handovers_all_categories_new.csv')

# Read all keypoints data
keypoints_data = {}
for category in ['3_way_after', '3_way_before', '2_way', 'consignment']:
    try:
        file_path = f'data/analysis/handover_keypoints/keypoints_{category}_transitions.csv'
        keypoints_data[category] = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Warning: Could not find keypoints data for {category}")

# 1. Top Handover Pairs Across Categories
def create_top_handovers_plot():
    plt.figure(figsize=(15, 8))
    
    # Get top 5 handovers for each category
    top_handovers = []
    for category in handovers_df['category'].unique():
        category_data = handovers_df[handovers_df['category'] == category].head(5)
        top_handovers.append(category_data)
    
    top_handovers_df = pd.concat(top_handovers)
    
    # Create the plot with custom colors
    sns.barplot(data=top_handovers_df, 
                x='percentage', 
                y='category',
                hue='from_role',
                palette=COLOR_PALETTE)
    
    plt.title('Top Handover Pairs by Process Category')
    plt.xlabel('Percentage of Total Handovers')
    plt.ylabel('Process Category')
    plt.legend(title='From Role', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'handover_pairs_by_category.png'), dpi=300, bbox_inches='tight')
    plt.close()

# New function: Detailed bar plots for frequent pairs
def create_frequent_pairs_barplots():
    # Create subplots for each category
    for category in handovers_df['category'].unique():
        plt.figure(figsize=(15, 10))
        
        # Get top 10 handovers for this category
        category_data = handovers_df[handovers_df['category'] == category].head(10)
        
        # Create pair labels
        pair_labels = [f"{row['from_role']}\n→\n{row['to_role']}" 
                      for _, row in category_data.iterrows()]
        
        # Create bars using count instead of percentage
        bars = plt.bar(range(len(pair_labels)), 
                      category_data['count'],
                      color=PRIMARY_COLOR)
        
        # Add percentage labels on top of bars
        for bar in bars:
            height = bar.get_height()
            percentage = (height / category_data['count'].sum()) * 100
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'Count: {int(height)}\n({percentage:.1f}%)',
                    ha='center', va='bottom')
        
        # Customize plot
        category_name = category.replace('_', ' ').title()
        plt.title(f'Top 10 Most Frequent Handover Pairs\n{category_name} Process')
        plt.xlabel('Role Pairs')
        plt.ylabel('Number of Handovers')
        plt.xticks(range(len(pair_labels)), pair_labels, rotation=45, ha='right')
        
        # Add grid for better readability
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Format y-axis with comma separator for thousands
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, f'frequent_pairs_barplot_{category}.png'), dpi=300, bbox_inches='tight')
        plt.close()

# 2. Critical Handover Points Visualization for all variants
def create_keypoints_visualization():
    for category, data in keypoints_data.items():
        plt.figure(figsize=(15, 8))
        
        # Get top 6 transitions
        top_transitions = data.head(6)
        
        # Create labels for better readability
        labels = [f"{row['from_activity']}\n→\n{row['to_activity']}" 
                 for _, row in top_transitions.iterrows()]
        
        # Create the plot with primary color
        bars = plt.bar(range(len(labels)), top_transitions['percentage'], color=PRIMARY_COLOR)
        
        # Add percentage labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%',
                    ha='center', va='bottom')
        
        category_name = category.replace('_', ' ').title()
        plt.title(f'Critical Handover Points in {category_name} Process')
        plt.xlabel('Activity Transition')
        plt.ylabel('Percentage of Handovers')
        plt.xticks(range(len(labels)), labels, rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, f'critical_handover_points_{category}.png'), dpi=300, bbox_inches='tight')
        plt.close()

# 3. Role Interaction Network for all variants
def create_role_interaction_heatmap():
    for category in handovers_df['category'].unique():
        plt.figure(figsize=(12, 10))
        
        # Create matrix of role interactions
        role_matrix = pd.pivot_table(
            handovers_df[handovers_df['category'] == category],
            values='percentage',
            index='from_role',
            columns='to_role',
            fill_value=0
        )
        
        # Create custom colormap from secondary to primary color
        custom_cmap = sns.light_palette(PRIMARY_COLOR, as_cmap=True)
        
        # Create heatmap
        sns.heatmap(role_matrix, 
                    annot=True, 
                    fmt='.1f',
                    cmap=custom_cmap,
                    cbar_kws={'label': 'Percentage of Handovers'})
        
        category_name = category.replace('_', ' ').title()
        plt.title(f'Role Interaction Heatmap ({category_name})')
        plt.xlabel('To Role')
        plt.ylabel('From Role')
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, f'role_interaction_heatmap_{category}.png'), dpi=300, bbox_inches='tight')
        plt.close()

# 4. Process Flow Comparison
def create_process_flow():
    # Create subplots for each category
    fig, axes = plt.subplots(2, 2, figsize=(20, 16))
    axes = axes.flatten()
    
    for idx, (category, data) in enumerate(keypoints_data.items()):
        ax = axes[idx]
        
        # Get top transitions for visualization
        top_transitions = data.head(6)
        
        # Create flow visualization
        y_positions = np.arange(len(top_transitions)) * 0.5
        
        # Create gradient colors
        colors = sns.color_palette([PRIMARY_COLOR, SECONDARY_COLOR], n_colors=len(top_transitions))
        
        for pos_idx, (_, row) in enumerate(top_transitions.iterrows()):
            ax.barh(y_positions[pos_idx], row['percentage'], height=0.3, color=colors[pos_idx])
            ax.text(row['percentage'] + 0.5, y_positions[pos_idx], 
                    f"{row['percentage']:.1f}%",
                    va='center')
        
        category_name = category.replace('_', ' ').title()
        ax.set_title(f'Process Flow: {category_name}')
        ax.set_xlabel('Percentage of Handovers')
        ax.set_ylim(-0.5, max(y_positions) + 0.5)
        ax.set_yticks([])
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'process_flow_comparison.png'), dpi=300, bbox_inches='tight')
    plt.close()

if __name__ == "__main__":
    create_top_handovers_plot()
    create_frequent_pairs_barplots()
    create_keypoints_visualization()
    create_role_interaction_heatmap()
    create_process_flow()
    print("Visualizations have been created successfully!") 