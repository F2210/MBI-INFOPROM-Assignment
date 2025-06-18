#!/usr/bin/env python3
"""
Handover Analysis Visualizations

This script creates various visualizations to illustrate the relationship
between handovers and case duration in the purchase-to-pay process.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats
from scipy import stats

# Set style for better-looking plots
plt.style.use('seaborn-v0_8')
sns.set_theme(style="whitegrid")

# Input/Output settings
ANALYSIS_DIR = './data/analysis'
OUTPUT_DIR = './data/analysis/visualizations'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Categories for analysis
ITEM_CATEGORIES = {
    "3_way_after": "3-way match, invoice after GR",
    "3_way_before": "3-way match, invoice before GR",
    "2_way": "2-way match"
}

def load_data(category):
    """Load analysis data for a category."""
    data = {}
    
    # Load handover data
    handovers_file = os.path.join(ANALYSIS_DIR, 'handovers', f'handovers_{category}.csv')
    duration_file = os.path.join(ANALYSIS_DIR, 'handover_duration', f'duration_{category}_role_level.csv')
    
    try:
        data['handovers'] = pd.read_csv(handovers_file)
        data['duration'] = pd.read_csv(duration_file)
    except Exception as e:
        print(f"Error loading data for {category}: {e}")
        return None
    
    return data

def create_role_impact_heatmap(category_data, category_name):
    """Create heatmap showing impact of role handovers on duration."""
    if 'handovers' not in category_data:
        return
    
    df = category_data['handovers']
    
    # Create pivot table for role handovers
    pivot = df.pivot_table(
        values='percentage',
        index='from_role',
        columns='to_role',
        aggfunc='sum',
        fill_value=0
    )
    
    plt.figure(figsize=(12, 8))
    sns.heatmap(pivot, annot=True, fmt='.1f', cmap='YlOrRd')
    plt.title(f'Role Handover Frequency (%) - {ITEM_CATEGORIES[category_name]}')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'{category_name}_role_heatmap.png'))
    plt.close()

def create_duration_distribution(category_data, category_name):
    """Create violin plot showing duration distribution by number of handovers."""
    if 'duration' not in category_data:
        return
    
    df = category_data['duration']
    
    plt.figure(figsize=(12, 6))
    sns.violinplot(x='total_handovers', y='duration', data=df)
    plt.title(f'Case Duration Distribution by Number of Handovers - {ITEM_CATEGORIES[category_name]}')
    plt.xlabel('Number of Handovers')
    plt.ylabel('Case Duration (hours)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'{category_name}_duration_distribution.png'))
    plt.close()

def create_top_handovers_impact(category_data, category_name):
    """Create bar plot showing impact of top handover patterns."""
    if 'handovers' not in category_data:
        return
    
    df = category_data['handovers']
    top_10 = df.nlargest(10, 'count')
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(range(len(top_10)), top_10['count'])
    plt.title(f'Top 10 Most Frequent Handovers - {ITEM_CATEGORIES[category_name]}')
    plt.xlabel('Handover Pattern')
    plt.ylabel('Frequency')
    
    # Add role labels
    labels = [f"{row['from_role']}\n→\n{row['to_role']}" for _, row in top_10.iterrows()]
    plt.xticks(range(len(labels)), labels, rotation=45, ha='right')
    
    # Add percentage labels on top of bars
    for idx, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{top_10.iloc[idx]["percentage"]:.1f}%',
                ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'{category_name}_top_handovers.png'))
    plt.close()

def create_system_handover_comparison():
    """Create comparison of system handovers across categories."""
    system_stats = []
    
    for category in ITEM_CATEGORIES:
        data = load_data(category)
        if not data or 'handovers' not in data:
            continue
            
        df = data['handovers']
        system_handovers = df[
            (df['from_role'].str.contains('BATCH|SYS|AUTO', na=False)) |
            (df['to_role'].str.contains('BATCH|SYS|AUTO', na=False))
        ]
        
        total_handovers = df['count'].sum()
        system_total = system_handovers['count'].sum()
        
        system_stats.append({
            'category': ITEM_CATEGORIES[category],
            'system_percentage': (system_total / total_handovers) * 100,
            'manual_percentage': 100 - (system_total / total_handovers) * 100
        })
    
    if system_stats:
        df = pd.DataFrame(system_stats)
        
        plt.figure(figsize=(10, 6))
        df.plot(
            x='category',
            y=['system_percentage', 'manual_percentage'],
            kind='bar',
            stacked=True
        )
        plt.title('System vs Manual Handovers by Category')
        plt.xlabel('Process Category')
        plt.ylabel('Percentage of Handovers')
        plt.legend(['System Handovers', 'Manual Handovers'])
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, 'system_handover_comparison.png'))
        plt.close()

def create_duration_correlation_plot():
    """Create plot comparing handover-duration correlations across categories."""
    correlations = []
    
    for category in ITEM_CATEGORIES:
        data = load_data(category)
        if not data or 'duration' not in data:
            continue
            
        df = data['duration']
        corr = df['total_handovers'].corr(df['duration'])
        
        correlations.append({
            'category': ITEM_CATEGORIES[category],
            'correlation': corr
        })
    
    if correlations:
        df = pd.DataFrame(correlations)
        
        plt.figure(figsize=(10, 6))
        bars = plt.bar(df['category'], df['correlation'])
        plt.title('Correlation between Handovers and Case Duration')
        plt.xlabel('Process Category')
        plt.ylabel('Correlation Coefficient')
        
        # Add correlation values on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.3f}',
                    ha='center', va='bottom')
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, 'duration_correlation.png'))
        plt.close()

def create_three_way_scatter_comparison():
    """Create scatter plots comparing 3-way before and after handover patterns with regression lines."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Load data for 3-way after GR
    after_data = load_data('3_way_after')
    if after_data and 'duration' in after_data:
        df_after = after_data['duration']
        
        # Create scatter plot
        ax1.scatter(df_after['total_handovers'], df_after['duration'], 
                   color='#00838f', alpha=0.5)
        
        # Add regression line
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            df_after['total_handovers'], df_after['duration']
        )
        line_x = np.array([df_after['total_handovers'].min(), df_after['total_handovers'].max()])
        line_y = slope * line_x + intercept
        ax1.plot(line_x, line_y, color='red', linestyle='-', linewidth=2)
        
        ax1.set_title('3-way match (invoice after GR)')
        ax1.set_xlabel('Number of Handovers')
        ax1.set_ylabel('Case Duration (hours)')
        
        # Add correlation and significance
        significance = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
        p_value_str = f"{p_value:.2e}" if p_value < 0.0001 else f"{p_value:.4f}"
        ax1.text(0.05, 0.95, 
                f'Correlation: {r_value:.3f} {significance}\np-value: {p_value_str}', 
                transform=ax1.transAxes, 
                bbox=dict(facecolor='white', alpha=0.8),
                verticalalignment='top')
    
    # Load data for 3-way before GR
    before_data = load_data('3_way_before')
    if before_data and 'duration' in before_data:
        df_before = before_data['duration']
        
        # Create scatter plot
        ax2.scatter(df_before['total_handovers'], df_before['duration'], 
                   color='#00838f', alpha=0.5)
        
        # Add regression line
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            df_before['total_handovers'], df_before['duration']
        )
        line_x = np.array([df_before['total_handovers'].min(), df_before['total_handovers'].max()])
        line_y = slope * line_x + intercept
        ax2.plot(line_x, line_y, color='red', linestyle='-', linewidth=2)
        
        ax2.set_title('3-way match (invoice before GR)')
        ax2.set_xlabel('Number of Handovers')
        ax2.set_ylabel('Case Duration (hours)')
        
        # Add correlation and significance
        significance = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
        p_value_str = f"{p_value:.2e}" if p_value < 0.0001 else f"{p_value:.4f}"
        ax2.text(0.05, 0.95, 
                f'Correlation: {r_value:.3f} {significance}\np-value: {p_value_str}', 
                transform=ax2.transAxes, 
                bbox=dict(facecolor='white', alpha=0.8),
                verticalalignment='top')
    
    # Add significance legend at the bottom
    fig.text(0.99, 0.01, 
             'Significance levels: *** p<0.001, ** p<0.01, * p<0.05, ns: not significant',
             ha='right', fontsize=8, style='italic')
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'three_way_scatter_comparison.png'))
    plt.close()

def create_summary_dashboard():
    """Create a summary dashboard combining key metrics."""
    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(2, 2)
    
    # # Top left: Correlation comparison
    # ax1 = fig.add_subplot(gs[0, 0])
    # correlations = []
    # for category in ITEM_CATEGORIES:
    #     data = load_data(category)
    #     if data and 'duration' in data:
    #         corr = data['duration']['total_handovers'].corr(data['duration']['duration'])
    #         correlations.append((category, corr))
    
    # if correlations:
    #     categories, corrs = zip(*correlations)
    #     ax1.bar([ITEM_CATEGORIES[c] for c in categories], corrs)
    #     ax1.set_title('Handover-Duration Correlation')
    #     ax1.set_xticklabels([ITEM_CATEGORIES[c] for c in categories], rotation=45, ha='right')
    
    # # Top right: System vs Manual handovers
    # ax2 = fig.add_subplot(gs[0, 1])
    # system_stats = []
    # for category in ITEM_CATEGORIES:
    #     data = load_data(category)
    #     if data and 'handovers' in data:
    #         df = data['handovers']
    #         system_handovers = df[
    #             (df['from_role'].str.contains('BATCH|SYS|AUTO', na=False)) |
    #             (df['to_role'].str.contains('BATCH|SYS|AUTO', na=False))
    #         ]
    #         total = df['count'].sum()
    #         system_total = system_handovers['count'].sum()
    #         system_stats.append((category, system_total/total*100))
    
    # if system_stats:
    #     categories, percentages = zip(*system_stats)
    #     ax2.bar([ITEM_CATEGORIES[c] for c in categories], percentages)
    #     ax2.set_title('System Handover Percentage')
    #     ax2.set_xticklabels([ITEM_CATEGORIES[c] for c in categories], rotation=45, ha='right')
    
    # Bottom: Average case duration by number of handovers
    ax3 = fig.add_subplot(gs[1, :])
    for category in ITEM_CATEGORIES:
        data = load_data(category)
        if data and 'duration' in data:
            df = data['duration']
            avg_duration = df.groupby('total_handovers')['duration'].mean()
            ax3.plot(avg_duration.index, avg_duration.values, 
                    label=ITEM_CATEGORIES[category], marker='o')
    
    ax3.set_title('Average Case Duration by Number of Handovers')
    ax3.set_xlabel('Number of Handovers')
    ax3.set_ylabel('Average Duration (hours)')
    ax3.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'summary_dashboard.png'))
    plt.close()

def main():
    """Main function to create all visualizations."""
    print("Creating visualizations...")
    
    # Create individual category visualizations
    for category in ITEM_CATEGORIES:
        print(f"\nProcessing {category}...")
        data = load_data(category)
        if data:
            create_role_impact_heatmap(data, category)
            create_duration_distribution(data, category)
            create_top_handovers_impact(data, category)
    
    # Create cross-category comparisons
    print("\nCreating comparison visualizations...")
    create_system_handover_comparison()
    create_duration_correlation_plot()
    create_three_way_scatter_comparison()
    
    # Create summary dashboard
    print("\nCreating summary dashboard...")
    create_summary_dashboard()
    
    print(f"\nVisualizations have been saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    main() 