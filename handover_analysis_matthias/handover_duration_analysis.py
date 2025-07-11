#!/usr/bin/env python3
"""
Handover Duration Analysis

This script analyzes the correlation between handovers and case durations in the purchase-to-pay process.
It aims to identify whether specific handover patterns are associated with longer case durations.
"""

import os
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from scipy import stats
import seaborn as sns
import matplotlib.pyplot as plt
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.util import constants

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Input/Output settings
INPUT_DIR = './data/filtered'
OUTPUT_DIR = './data/analysis/handover_duration'

# Item categories for analysis - updated to match actual file names
ITEM_CATEGORIES = {
    "3_way_after": ["group_3_way_after.xes"],
    "3_way_before": ["group_3_way_before.xes"],
    "2_way": ["group_2_way.xes"],
    "consignment": ["group_consignment.xes"]
}

def calculate_case_duration(case):
    """Calculate the duration of a case in hours."""
    timestamps = [event["time:timestamp"] for event in case]
    duration = max(timestamps) - min(timestamps)
    return duration.total_seconds() / 3600  # Convert to hours

def get_role(resource):
    """Extract role from resource identifier."""
    if resource == "NONE" or not resource:
        return "NONE"
    if resource.startswith("batch"):
        return "BATCH"
    if resource.startswith("user"):
        # Extract the role number (first 2 digits after 'user_')
        try:
            role_num = resource.split('_')[1][:2]  # Take first two digits
            return f"ROLE_{role_num}"
        except:
            return "UNKNOWN"
    return resource

def analyze_handovers_and_duration(log, category_name):
    """
    Analyze handovers and their relationship with case duration.
    
    Args:
        log: PM4Py event log
        category_name: Name of the category being analyzed
        
    Returns:
        Tuple of DataFrames containing handover and duration information per case
        (user_level_df, role_level_df)
    """
    logger.info(f"Analyzing handovers and duration for {category_name}")
    
    user_case_data = []
    role_case_data = []
    
    for case_idx, case in enumerate(log):
        if case_idx % 1000 == 0:
            logger.info(f"Processing case {case_idx} of {len(log)}")
        
        case_id = case.attributes["concept:name"]
        duration = calculate_case_duration(case)
        
        # Debug logging for first few cases
        if case_idx < 3:
            logger.info(f"\nDebug - Case {case_id}:")
            logger.info(f"Duration: {duration:.2f} hours")
            logger.info("First few events:")
            for i, event in enumerate(list(case)[:5]):
                logger.info(f"Event {i}: Resource={event.get('org:resource', 'NONE')}, Role={event.get('userRole', 'UNKNOWN')}")
        
        # Analyze handovers in the case
        user_handovers = []
        role_handovers = []
        events = list(case)
        
        for i in range(len(events) - 1):
            current_user = events[i].get("org:resource", "NONE")
            next_user = events[i + 1].get("org:resource", "NONE")
            
            # Get role from resource if not directly available
            current_role = get_role(current_user)
            next_role = get_role(next_user)
            
            if current_user != next_user and current_user != "NONE" and next_user != "NONE":
                user_handovers.append((current_user, next_user))
            
            if current_role != next_role and current_role != "NONE" and next_role != "NONE":
                role_handovers.append((current_role, next_role))
        
        # Debug logging for first few cases
        if case_idx < 3:
            logger.info(f"User handovers: {user_handovers}")
            logger.info(f"Role handovers: {role_handovers}")
        
        # User-level analysis
        user_total_handovers = len(user_handovers)
        user_unique_handovers = len(set(user_handovers))
        
        if user_handovers:
            from collections import Counter
            most_common = Counter(user_handovers).most_common(1)[0]
            user_most_freq_handover = f"{most_common[0][0]}->{most_common[0][1]}"
            user_most_freq_count = most_common[1]
        else:
            user_most_freq_handover = "NONE"
            user_most_freq_count = 0
        
        # Role-level analysis
        role_total_handovers = len(role_handovers)
        role_unique_handovers = len(set(role_handovers))
        
        if role_handovers:
            most_common = Counter(role_handovers).most_common(1)[0]
            role_most_freq_handover = f"{most_common[0][0]}->{most_common[0][1]}"
            role_most_freq_count = most_common[1]
        else:
            role_most_freq_handover = "NONE"
            role_most_freq_count = 0
        
        user_case_data.append({
            'case_id': case_id,
            'duration': duration,
            'total_handovers': user_total_handovers,
            'unique_handovers': user_unique_handovers,
            'most_frequent_handover': user_most_freq_handover,
            'most_frequent_count': user_most_freq_count
        })
        
        role_case_data.append({
            'case_id': case_id,
            'duration': duration,
            'total_handovers': role_total_handovers,
            'unique_handovers': role_unique_handovers,
            'most_frequent_handover': role_most_freq_handover,
            'most_frequent_count': role_most_freq_count
        })
    
    return pd.DataFrame(user_case_data), pd.DataFrame(role_case_data)

def create_visualizations(df, category_name):
    """Create visualizations for the handover-duration analysis."""
    logger.info(f"Creating visualizations for {category_name}")
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Scatter plot: Total handovers vs Duration
    plt.figure(figsize=(10, 6))
    plt.scatter(df['total_handovers'], df['duration'], alpha=0.5)
    plt.title(f'Case Duration vs Total Handovers ({category_name})')
    plt.xlabel('Number of Handovers')
    plt.ylabel('Case Duration (hours)')
    
    # Add correlation line
    corr = stats.pearsonr(df['total_handovers'], df['duration'])[0]
    plt.text(0.05, 0.95, f'Correlation: {corr:.2f}', 
             transform=plt.gca().transAxes, 
             bbox=dict(facecolor='white', alpha=0.8))
    
    plt.savefig(os.path.join(OUTPUT_DIR, f'{category_name}_scatter.png'))
    plt.close()
    
    # 2. Box plot: Duration distribution for different numbers of unique handovers
    plt.figure(figsize=(12, 6))
    df_grouped = df.groupby('unique_handovers')['duration'].apply(list)
    plt.boxplot(df_grouped.values, labels=df_grouped.index)
    plt.title(f'Case Duration Distribution by Unique Handovers ({category_name})')
    plt.xlabel('Number of Unique Handovers')
    plt.ylabel('Case Duration (hours)')
    plt.xticks(rotation=45)
    plt.savefig(os.path.join(OUTPUT_DIR, f'{category_name}_boxplot.png'), 
                bbox_inches='tight')
    plt.close()
    
    # 3. Top 10 most frequent handovers and their average durations
    top_handovers = df.groupby('most_frequent_handover').agg({
        'duration': ['mean', 'count']
    }).sort_values(('duration', 'count'), ascending=False).head(10)
    
    plt.figure(figsize=(12, 6))
    plt.bar(range(len(top_handovers)), top_handovers[('duration', 'mean')])
    plt.title(f'Average Duration for Top 10 Most Frequent Handovers ({category_name})')
    plt.xlabel('Handover Pattern')
    plt.ylabel('Average Duration (hours)')
    plt.xticks(range(len(top_handovers)), top_handovers.index, rotation=45, ha='right')
    plt.savefig(os.path.join(OUTPUT_DIR, f'{category_name}_top_handovers.png'),
                bbox_inches='tight')
    plt.close()
    
    return top_handovers

def perform_statistical_analysis(df):
    """Perform statistical analysis on the handover-duration relationship."""
    # Calculate correlations
    correlations = {}
    
    # Only calculate correlations if we have valid data
    if len(df) > 1 and not df['total_handovers'].isna().any() and not df['duration'].isna().any():
        correlations['total_handovers'] = stats.pearsonr(df['total_handovers'], df['duration'])
    else:
        correlations['total_handovers'] = (np.nan, np.nan)
    
    if len(df) > 1 and not df['unique_handovers'].isna().any() and not df['duration'].isna().any():
        correlations['unique_handovers'] = stats.pearsonr(df['unique_handovers'], df['duration'])
    else:
        correlations['unique_handovers'] = (np.nan, np.nan)
    
    # Group cases by number of handovers and perform ANOVA
    # Only perform ANOVA if we have enough groups with data
    groups = [group['duration'].values for name, group in df.groupby('unique_handovers') if len(group) > 1]
    if len(groups) >= 2:
        f_stat, p_value = stats.f_oneway(*groups)
    else:
        f_stat, p_value = np.nan, np.nan
    
    return {
        'correlations': correlations,
        'anova': (f_stat, p_value)
    }

def main():
    """Main function to analyze handovers and their relationship with case duration."""
    logger.info("Starting handover-duration analysis")
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Store results for all categories
    all_results = {}
    
    for category_name, category_files in ITEM_CATEGORIES.items():
        logger.info(f"\nProcessing category: {category_name}")
        
        # Find and load the XES file
        xes_file = os.path.join(INPUT_DIR, category_files[0])
        
        if not os.path.exists(xes_file):
            logger.warning(f"File not found: {xes_file}")
            continue
            
        try:
            # Load and analyze the log
            logger.info(f"Loading log file: {xes_file}")
            log = xes_importer.apply(xes_file)
            logger.info(f"Successfully loaded log with {len(log)} cases")
            
            # Print some debug information about the first case
            if len(log) > 0:
                first_case = log[0]
                logger.info("\nDebug - First case attributes:")
                for key, value in first_case.attributes.items():
                    logger.info(f"{key}: {value}")
                logger.info("\nDebug - First case events:")
                for i, event in enumerate(list(first_case)[:5]):
                    logger.info(f"Event {i}:")
                    for key, value in event.items():
                        logger.info(f"  {key}: {value}")
            
            # Analyze handovers and duration
            user_level_df, role_level_df = analyze_handovers_and_duration(log, category_name)
            
            # Print summary of the dataframes
            logger.info("\nUser-level DataFrame Summary:")
            logger.info(user_level_df.describe())
            logger.info("\nRole-level DataFrame Summary:")
            logger.info(role_level_df.describe())
            
            # Create visualizations
            create_visualizations(user_level_df, f"{category_name}_user_level")
            create_visualizations(role_level_df, f"{category_name}_role_level")
            
            # Save results
            user_level_df.to_csv(os.path.join(OUTPUT_DIR, f"duration_{category_name}_user_level.csv"), index=False)
            role_level_df.to_csv(os.path.join(OUTPUT_DIR, f"duration_{category_name}_role_level.csv"), index=False)
            
            # Print summary statistics
            logger.info(f"\nSummary for {category_name}:")
            
            # User-level summary
            logger.info("\nUser-level analysis:")
            logger.info(f"Total cases analyzed: {len(user_level_df)}")
            logger.info(f"Average case duration: {user_level_df['duration'].mean():.2f} hours")
            logger.info(f"Average handovers per case: {user_level_df['total_handovers'].mean():.2f}")
            logger.info(f"Average unique handovers per case: {user_level_df['unique_handovers'].mean():.2f}")
            
            # Role-level summary
            logger.info("\nRole-level analysis:")
            logger.info(f"Total cases analyzed: {len(role_level_df)}")
            logger.info(f"Average case duration: {role_level_df['duration'].mean():.2f} hours")
            logger.info(f"Average handovers per case: {role_level_df['total_handovers'].mean():.2f}")
            logger.info(f"Average unique handovers per case: {role_level_df['unique_handovers'].mean():.2f}")
            
            # Perform statistical analysis
            stats_results = perform_statistical_analysis(user_level_df)
            logger.info("\nStatistical Analysis:")
            logger.info(f"Correlation between total handovers and duration: {stats_results['correlations']['total_handovers'][0]:.3f} (p-value: {stats_results['correlations']['total_handovers'][1]:.3f})")
            logger.info(f"Correlation between unique handovers and duration: {stats_results['correlations']['unique_handovers'][0]:.3f} (p-value: {stats_results['correlations']['unique_handovers'][1]:.3f})")
            logger.info(f"ANOVA F-statistic: {stats_results['anova'][0]:.3f} (p-value: {stats_results['anova'][1]:.3f})")
            
            all_results[category_name] = {
                'user_level': user_level_df,
                'role_level': role_level_df,
                'statistics': stats_results
            }
            
        except Exception as e:
            logger.error(f"Error processing {category_name}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 