#!/usr/bin/env python3
"""
Top Duration Impact Analysis

This script analyzes and visualizes the top 10 handovers with the highest duration impact
for different categories (3-way before/after GR, 2-way, and consignment).
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

# Set style for better-looking plots
plt.style.use('default')

# Input/Output settings
INPUT_DIR = './data/analysis/handover_duration'
OUTPUT_DIR = './handover_keypoints_visualisations'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_base_roles(handover_str):
    """Extract base roles from a handover string (e.g., 'ROLE_01->ROLE_02' -> ['ROLE_01', 'ROLE_02'])."""
    if pd.isna(handover_str) or handover_str == 'NONE':
        return []
    return [role.strip() for role in handover_str.split('->')]

def load_and_process_data(category):
    """Load data from CSV and process to get top handovers."""
    file_path = os.path.join(INPUT_DIR, f'duration_{category}_role_level.csv')
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    df = pd.read_csv(file_path)
    
    # Extract all unique base roles
    all_roles = set()
    for handover in df['most_frequent_handover'].dropna():
        roles = extract_base_roles(handover)
        all_roles.update(roles)
    
    # Filter for base roles (ROLE_01 through ROLE_16)
    base_roles = {role for role in all_roles if role.startswith('ROLE_') and 
                 role[5:].isdigit() and 1 <= int(role[5:]) <= 16}
    
    # Add special roles
    base_roles.update(['BATCH', 'NONE'])
    
    # Calculate average duration for each base role
    role_durations = {}
    for role in base_roles:
        # Find all handovers where this role appears
        role_handovers = df[df['most_frequent_handover'].str.contains(role, na=False)]
        if not role_handovers.empty:
            role_durations[role] = role_handovers['duration'].mean()
    
    # Sort roles by duration
    sorted_roles = sorted(role_durations.items(), key=lambda x: x[1], reverse=True)
    
    # Get top 10 roles
    top_roles = [role for role, _ in sorted_roles[:10]]
    top_durations = [duration for _, duration in sorted_roles[:10]]
    
    return top_roles, top_durations

def create_comparison_plot(before_roles, before_durations, after_roles, after_durations):
    """Create a bar plot comparing durations before and after."""
    # Set up the plot
    plt.figure(figsize=(15, 8))
    
    # Set positions of bars
    x = np.arange(len(before_roles))
    width = 0.35
    
    # Create bars
    plt.bar(x - width/2, before_durations, width, label='3-way before GR', color='#00838f')
    plt.bar(x + width/2, after_durations, width, label='3-way after GR', color='#ff6d00')
    
    # Add labels and title
    plt.xlabel('Role')
    plt.ylabel('Average Duration (hours)')
    plt.title('Top 10 Roles by Duration Impact')
    plt.xticks(x, before_roles, rotation=45, ha='right')
    plt.legend()
    
    # Add value labels on top of bars
    for i, v in enumerate(before_durations):
        plt.text(i - width/2, v, f'{v:.1f}h\n({v/24:.1f}d)', 
                ha='center', va='bottom')
    for i, v in enumerate(after_durations):
        plt.text(i + width/2, v, f'{v:.1f}h\n({v/24:.1f}d)', 
                ha='center', va='bottom')
    
    # Add grid for better readability
    plt.grid(True, axis='y', linestyle='--', alpha=0.7)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save plot
    plt.savefig(os.path.join(OUTPUT_DIR, 'top_10_duration_impact_comparison.png'))
    plt.close()

def main():
    """Main function to perform the analysis."""
    try:
        # Load and process data for both categories
        before_roles, before_durations = load_and_process_data('3_way_before')
        after_roles, after_durations = load_and_process_data('3_way_after')
        
        # Create comparison plot
        create_comparison_plot(before_roles, before_durations, after_roles, after_durations)
        
        print("Plot has been generated successfully!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 