#!/usr/bin/env python3
"""
Handover Key Points Analysis

This script analyzes activity transitions where handovers between roles occur,
identifying critical points in the process where work transfers between different roles.
"""

import os
import logging
from collections import Counter, defaultdict
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.util import constants
import scipy.stats as stats
from scipy import stats
from datetime import datetime
import networkx as nx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Input/Output settings
INPUT_DIR = './data/filtered'
OUTPUT_DIR = './data/analysis/handover_keypoints'

# Process categories
ITEM_CATEGORIES = {
    '3_way_after': 'Record Invoice Receipt (After GR)',
    '3_way_before': 'Record Invoice Receipt (Before GR)',
    '2_way': '2-way match',
    'consignment': 'Consignment'
}

# File mapping
FILE_MAPPING = {
    '3_way_after': 'group_3_way_after.xes',
    '3_way_before': 'group_3_way_before.xes',
    '2_way': 'group_2_way.xes',
    'consignment': 'group_consignment.xes'
}

def get_role(resource):
    """Extract role from resource identifier."""
    if resource == "NONE" or not resource:
        return "NONE"
    if resource.startswith("batch"):
        return "BATCH"
    if resource.startswith("user"):
        try:
            role_num = resource.split('_')[1][:2]  # Take first two digits
            return f"ROLE_{role_num}"
        except:
            return "UNKNOWN"
    return resource

def analyze_handover_keypoints(log, category_name):
    """
    Analyze activity transitions where handovers occur between roles.
    
    Args:
        log: PM4Py event log
        category_name: Name of the process category
        
    Returns:
        DataFrame containing handover keypoint information
    """
    logger.info(f"Analyzing handover keypoints for {category_name}")
    
    # Store handover transitions
    handover_transitions = []
    handover_details = defaultdict(lambda: {'total': 0, 'roles': defaultdict(int)})
    
    for case_idx, case in enumerate(log):
        if case_idx % 1000 == 0:
            logger.info(f"Processing case {case_idx} of {len(log)}")
        
        events = list(case)
        for i in range(len(events) - 1):
            current_event = events[i]
            next_event = events[i + 1]
            
            # Get activities and roles
            current_activity = current_event["concept:name"]
            next_activity = next_event["concept:name"]
            current_role = get_role(current_event.get("org:resource", "NONE"))
            next_role = get_role(next_event.get("org:resource", "NONE"))
            
            # Record transition if there's a role handover
            if current_role != next_role:
                transition = (current_activity, next_activity)
                handover_transitions.append({
                    'from_activity': current_activity,
                    'to_activity': next_activity,
                    'from_role': current_role,
                    'to_role': next_role
                })
                
                # Store detailed information
                key = f"{current_activity} → {next_activity}"
                role_key = f"{current_role} → {next_role}"
                handover_details[key]['total'] += 1
                handover_details[key]['roles'][role_key] += 1
    
    # Convert to DataFrame
    df = pd.DataFrame(handover_transitions)
    
    if len(df) == 0:
        logger.warning(f"No handover transitions found for {category_name}")
        return pd.DataFrame(), pd.DataFrame(), handover_details
    
    # Calculate frequencies and percentages
    total_handovers = len(df)
    transition_counts = df.groupby(['from_activity', 'to_activity']).size().reset_index(name='frequency')
    transition_counts['percentage'] = (transition_counts['frequency'] / total_handovers * 100).round(2)
    
    # Calculate role combinations for each transition
    role_combinations = df.groupby(['from_activity', 'to_activity', 'from_role', 'to_role']).size().reset_index(name='role_frequency')
    
    # Sort by frequency
    transition_counts = transition_counts.sort_values('frequency', ascending=False)
    
    return transition_counts, role_combinations, handover_details

def create_visualizations(transition_counts, role_combinations, category_name):
    """Create visualizations for handover keypoints analysis."""
    logger.info(f"Creating visualizations for {category_name}")
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Bar plot of top 5 handover transitions
    plt.figure(figsize=(10, 5))
    top_5 = transition_counts.head(5)
    
    # Create labels for x-axis
    labels = [f"{row['from_activity']}\n→\n{row['to_activity']}" 
             for _, row in top_5.iterrows()]
    
    plt.bar(range(len(top_5)), top_5['frequency'], color='#00838f')
    plt.xticks(range(len(top_5)), labels, rotation=45, ha='right')
    plt.title(f'Top 5 Handover Activity Transitions ({category_name})')
    plt.xlabel('Activity Transition')
    plt.ylabel('Frequency')
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'{category_name}_top5_transitions.png'))
    plt.close()
    
    return top_5

def calculate_case_duration(case):
    """Calculate the duration of a case in hours."""
    timestamps = []
    for event in case:
        timestamp_str = event["time:timestamp"]
        if isinstance(timestamp_str, str):
            try:
                # Try different timestamp formats
                if 'Z' in timestamp_str:
                    timestamp_str = timestamp_str.replace('Z', '+00:00')
                elif '+' not in timestamp_str and '-' not in timestamp_str[-6:]:
                    timestamp_str = timestamp_str + '+00:00'
                
                # Parse the timestamp
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S%z')
                    except ValueError:
                        timestamp = datetime.strptime(timestamp_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                
                timestamps.append(timestamp)
            except Exception as e:
                logger.debug(f"Error parsing timestamp: {timestamp_str} - {str(e)}")
                continue
        elif isinstance(timestamp_str, datetime):
            timestamps.append(timestamp_str)
    
    if len(timestamps) < 2:
        return None
    
    duration = (max(timestamps) - min(timestamps)).total_seconds() / 3600
    return duration if duration > 0 else None

def analyze_handover_duration_correlation(log, category_name):
    """Analyze correlation between handovers and case duration."""
    case_stats = []
    total_cases = len(log)
    valid_cases = 0
    invalid_cases = 0
    
    for case in log:
        # Calculate number of handovers
        handovers = 0
        events = list(case)
        for i in range(len(events) - 1):
            current_role = events[i].get("userRole", "UNKNOWN")
            next_role = events[i + 1].get("userRole", "UNKNOWN")
            if current_role != next_role:
                handovers += 1
        
        # Calculate case duration
        duration = calculate_case_duration(case)
        
        if duration is not None and handovers > 0:
            case_stats.append({
                'handovers': handovers,
                'duration': duration
            })
            valid_cases += 1
        else:
            invalid_cases += 1
    
    if len(case_stats) < 2:
        logger.warning(f"Not enough valid cases for correlation analysis in {category_name}")
        logger.warning(f"Total cases: {total_cases}, Valid: {valid_cases}, Invalid: {invalid_cases}")
        return None, None, 0
    
    df = pd.DataFrame(case_stats)
    
    try:
        # Calculate correlation and p-value
        correlation, p_value = stats.pearsonr(df['handovers'], df['duration'])
        
        # Create scatter plot
        plt.figure(figsize=(10, 6))
        plt.scatter(df['handovers'], df['duration'], color='#00838f', alpha=0.5)
        
        # Add regression line
        z = np.polyfit(df['handovers'], df['duration'], 1)
        p = np.poly1d(z)
        plt.plot(df['handovers'], p(df['handovers']), "r-", linewidth=2)
        
        plt.title(f'Handover-Duration Correlation - {ITEM_CATEGORIES[category_name]}')
        plt.xlabel('Number of Handovers')
        plt.ylabel('Case Duration (hours)')
        
        # Add correlation and p-value information
        significance = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
        p_value_str = f"{p_value:.2e}" if p_value < 0.0001 else f"{p_value:.4f}"
        plt.text(0.05, 0.95, 
                f'Correlation: {correlation:.3f} {significance}\np-value: {p_value_str}\nn = {len(df)}', 
                transform=plt.gca().transAxes,
                bbox=dict(facecolor='white', alpha=0.8),
                verticalalignment='top')
        
        # Add descriptive statistics
        plt.text(0.05, 0.80,
                f'Mean duration: {df["duration"].mean():.1f} hours\n'
                f'Median duration: {df["duration"].median():.1f} hours\n'
                f'Mean handovers: {df["handovers"].mean():.1f}\n'
                f'Median handovers: {df["handovers"].median():.1f}',
                transform=plt.gca().transAxes,
                bbox=dict(facecolor='white', alpha=0.8),
                verticalalignment='top')
        
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, f'{category_name}_handover_duration_correlation.png'))
        plt.close()
        
        return correlation, p_value, len(df)
    
    except Exception as e:
        logger.error(f"Error in correlation analysis for {category_name}: {str(e)}")
        return None, None, len(df)

def create_dfg(transition_counts, handover_details, category_name, threshold=5.0):
    """Create and visualize a Directly-Follows Graph (DFG) for a given category."""
    logger.info(f"Creating DFG for {category_name}")
    
    # Create a directed graph
    G = nx.DiGraph()
    
    # Add nodes and edges
    for _, row in transition_counts.iterrows():
        from_activity = row['from_activity']
        to_activity = row['to_activity']
        frequency = row['frequency']
        
        # Add nodes if they don't exist
        if from_activity not in G:
            G.add_node(from_activity)
        if to_activity not in G:
            G.add_node(to_activity)
        
        # Add edge with frequency as weight
        G.add_edge(from_activity, to_activity, weight=frequency)
    
    # Highlight handover transitions
    for edge in G.edges():
        from_activity, to_activity = edge
        key = f"{from_activity} → {to_activity}"
        if key in handover_details and handover_details[key]['total'] > 0:
            G[from_activity][to_activity]['handover'] = True
    
    # Filter edges based on threshold
    edges_to_remove = [(u, v) for u, v, d in G.edges(data=True) if d['weight'] < threshold]
    G.remove_edges_from(edges_to_remove)
    
    # Visualize the graph
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G)
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=500)
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, edge_color='gray', width=1.0)
    
    # Highlight handover edges
    handover_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('handover', False)]
    nx.draw_networkx_edges(G, pos, edgelist=handover_edges, edge_color='red', width=2.0)
    
    # Draw labels
    nx.draw_networkx_labels(G, pos)
    
    plt.title(f'Directly-Follows Graph for {category_name}')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'{category_name}_dfg.png'))
    plt.close()

def main():
    """Main function to analyze handover keypoints across all categories."""
    logger.info("Starting handover keypoints analysis")
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Store results for all categories
    all_results = {}
    correlation_results = []
    
    for category_name, category_desc in ITEM_CATEGORIES.items():
        logger.info(f"\nProcessing category: {category_name}")
        
        # Find and load the XES file
        xes_file = os.path.join(INPUT_DIR, FILE_MAPPING[category_name])
        logger.info(f"Looking for file: {xes_file}")
        
        if not os.path.exists(xes_file):
            logger.warning(f"File not found: {xes_file}")
            continue
        
        try:
            # Load and analyze the log
            logger.info(f"Loading log file: {xes_file}")
            log = xes_importer.apply(xes_file)
            logger.info(f"Successfully loaded log with {len(log)} cases")
            
            # Analyze handover keypoints
            transition_counts, role_combinations, handover_details = analyze_handover_keypoints(log, category_name)
            
            # Analyze correlation
            correlation, p_value, n_cases = analyze_handover_duration_correlation(log, category_name)
            correlation_results.append({
                'category': category_desc,
                'correlation': correlation,
                'p_value': p_value,
                'n_cases': n_cases
            })
            
            # Save results
            transition_counts.to_csv(os.path.join(OUTPUT_DIR, f"keypoints_{category_name}_transitions.csv"), index=False)
            role_combinations.to_csv(os.path.join(OUTPUT_DIR, f"keypoints_{category_name}_roles.csv"), index=False)
            
            all_results[category_name] = {
                'transition_counts': transition_counts,
                'role_combinations': role_combinations,
                'handover_details': handover_details
            }
            
            # Create visualizations
            create_visualizations(transition_counts, role_combinations, category_name)
            
            # Create DFG
            create_dfg(transition_counts, handover_details, category_name)
            
        except Exception as e:
            logger.error(f"Error processing {category_name}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Print correlation summary
    logger.info("\nCorrelation Analysis Summary:")
    for result in correlation_results:
        logger.info(f"\n{result['category']}:")
        if result['correlation'] is not None and result['p_value'] is not None:
            logger.info(f"  Correlation coefficient: {result['correlation']:.3f}")
            logger.info(f"  P-value: {result['p_value']:.2e}")
        else:
            logger.info("  Correlation coefficient: N/A")
            logger.info("  P-value: N/A")
        logger.info(f"  Number of cases: {result['n_cases']}")
    
    # Generate summary report for handover keypoints
    logger.info("\nHandover Keypoints Summary:")
    for category, results in all_results.items():
        logger.info(f"\n{category}:")
        
        # Get top 5 handover keypoints
        top_5 = results['transition_counts'].head(5)
        logger.info("Top 5 handover keypoints:")
        
        for _, row in top_5.iterrows():
            transition = f"{row['from_activity']} → {row['to_activity']}"
            logger.info(f"  {transition}:")
            logger.info(f"    Frequency: {row['frequency']} ({row['percentage']}%)")
            
            # Get role combinations for this transition
            transition_roles = results['role_combinations'][
                (results['role_combinations']['from_activity'] == row['from_activity']) &
                (results['role_combinations']['to_activity'] == row['to_activity'])
            ]
            
            # Show top 3 role combinations for this transition
            top_roles = transition_roles.nlargest(3, 'role_frequency')
            for _, role_row in top_roles.iterrows():
                role_transition = f"{role_row['from_role']} → {role_row['to_role']}"
                percentage = round((role_row['role_frequency'] / row['frequency'] * 100), 2)
                logger.info(f"      {role_transition}: {role_row['role_frequency']} times ({percentage}%)")

if __name__ == "__main__":
    main() 