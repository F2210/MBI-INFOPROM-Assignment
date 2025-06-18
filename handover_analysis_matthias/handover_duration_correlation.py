#!/usr/bin/env python3
"""
Handover Duration Correlation Analysis

This script analyzes the correlation between number of handovers and case duration
for 3-way match cases (before and after GR).
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Set style for better-looking plots
plt.style.use('seaborn-v0_8')
sns.set_theme(style="whitegrid")

# Input/Output settings
ANALYSIS_DIR = './data/analysis/handover_duration'
OUTPUT_DIR = './data/analysis/correlation'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_data():
    """Load duration data for 3-way before and after cases."""
    data = {}
    
    # Load 3-way before data
    before_file = os.path.join(ANALYSIS_DIR, 'duration_3_way_before_role_level.csv')
    data['before'] = pd.read_csv(before_file)
    
    # Load 3-way after data
    after_file = os.path.join(ANALYSIS_DIR, 'duration_3_way_after_role_level.csv')
    data['after'] = pd.read_csv(after_file)
    
    return data

def analyze_correlation(df, category):
    """Calculate correlation between handovers and duration."""
    correlation, p_value = stats.pearsonr(df['total_handovers'], df['duration'])
    return {
        'category': category,
        'correlation': correlation,
        'p_value': p_value,
        'mean_duration': df['duration'].mean(),
        'mean_handovers': df['total_handovers'].mean()
    }

def create_regression_plot(df_before, df_after):
    """Create regression plots for both categories."""
    # Set up the plot with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot data points and regression line for 3-way before
    sns.regplot(data=df_before, x='total_handovers', y='duration',
                scatter_kws={'alpha':0.5}, 
                line_kws={'color': 'red'},
                color='#00838f',
                ax=ax1,
                label='3-way before GR')
    
    # Plot data points and regression line for 3-way after
    sns.regplot(data=df_after, x='total_handovers', y='duration',
                scatter_kws={'alpha':0.5}, 
                line_kws={'color': 'red'},
                color='#00838f',
                ax=ax2,
                label='3-way after GR')
    
    # Calculate correlations
    corr_before = stats.pearsonr(df_before['total_handovers'], df_before['duration'])
    corr_after = stats.pearsonr(df_after['total_handovers'], df_after['duration'])
    
    # Add correlation information to each subplot
    ax1.text(0.05, 0.95, 
             f'Correlation: {corr_before[0]:.3f}\np-value: {corr_before[1]:.3e}',
             transform=ax1.transAxes,
             bbox=dict(facecolor='white', alpha=0.8))
    
    ax2.text(0.05, 0.95,
             f'Correlation: {corr_after[0]:.3f}\np-value: {corr_after[1]:.3e}',
             transform=ax2.transAxes,
             bbox=dict(facecolor='white', alpha=0.8))
    
    # Set titles and labels
    ax1.set_title('3-way before GR')
    ax2.set_title('3-way after GR')
    ax1.set_xlabel('Number of Handovers')
    ax2.set_xlabel('Number of Handovers')
    ax1.set_ylabel('Case Duration (hours)')
    ax2.set_ylabel('Case Duration (hours)')
    
    # Adjust layout
    plt.tight_layout()
    
    # Save plot
    plt.savefig(os.path.join(OUTPUT_DIR, 'handover_duration_correlation.png'))
    plt.close()

def main():
    """Main function to perform correlation analysis."""
    print("Loading data...")
    data = load_data()
    
    # Analyze correlations
    results = []
    results.append(analyze_correlation(data['before'], '3-way before GR'))
    results.append(analyze_correlation(data['after'], '3-way after GR'))
    
    # Print results
    print("\nCorrelation Analysis Results:")
    for result in results:
        print(f"\n{result['category']}:")
        print(f"Correlation coefficient: {result['correlation']:.3f}")
        print(f"P-value: {result['p_value']:.10e}")
        print(f"Mean duration: {result['mean_duration']:.2f} hours")
        print(f"Mean handovers: {result['mean_handovers']:.2f}")
    
    # Create visualization
    print("\nCreating regression plot...")
    create_regression_plot(data['before'], data['after'])
    print(f"Plot saved to {os.path.join(OUTPUT_DIR, 'handover_duration_correlation.png')}")

if __name__ == "__main__":
    main() 