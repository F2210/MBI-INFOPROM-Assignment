#!/usr/bin/env python3
"""
Activity Transition Analysis

This script analyzes activity transitions where handovers occur, identifying critical points
where role shifts are located. For each category, each pair of consecutive events is evaluated
to record activity-to-activity handovers and their frequencies.
"""

import os
import logging
from collections import Counter, defaultdict
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from pm4py.objects.log.importer.xes import importer as xes_importer
import networkx as nx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Input/Output settings
INPUT_DIR = './data/filtered'
OUTPUT_DIR = './data/analysis/activity_transitions'

# Process categories
ITEM_CATEGORIES = {
    # '3_way_after': 'Record Invoice Receipt (After GR)',
    # '3_way_before': 'Record Invoice Receipt (Before GR)',
    # '2_way': '2-way match',
    'consignment': 'Consignment'
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

def analyze_activity_transitions(log, category_name):
    """
    Analyze activity transitions where handovers occur.
    
    Args:
        log: PM4Py event log
        category_name: Name of the process category
        
    Returns:
        DataFrame containing transition information and handover details
    """
    logger.info(f"Analyzing activity transitions for {category_name}")
    
    # Store transitions and handovers
    transitions = []
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
            
            # Record transition
            transition = {
                'from_activity': current_activity,
                'to_activity': next_activity,
                'from_role': current_role,
                'to_role': next_role,
                'is_handover': current_role != next_role and current_role != "NONE" and next_role != "NONE" and current_role != "BATCH" and next_role != "BATCH"
            }
            transitions.append(transition)
            
            # If it's a handover, record detailed information
            if current_role != next_role and current_role != "NONE" and next_role != "NONE" and current_role != "BATCH" and next_role != "BATCH":
                key = f"{current_activity} → {next_activity}"
                role_key = f"{current_role} → {next_role}"
                handover_details[key]['total'] += 1
                handover_details[key]['roles'][role_key] += 1
    
    # Convert to DataFrame
    df = pd.DataFrame(transitions)
    
    if len(df) == 0:
        logger.warning(f"No transitions found for {category_name}")
        return pd.DataFrame(), pd.DataFrame(), handover_details
    
    # Calculate frequencies and percentages
    total_transitions = len(df)
    transition_counts = df.groupby(['from_activity', 'to_activity']).size().reset_index(name='frequency')
    transition_counts['percentage'] = (transition_counts['frequency'] / total_transitions * 100).round(2)
    
    # Calculate handover frequencies
    handover_counts = df[df['is_handover']].groupby(['from_activity', 'to_activity']).size().reset_index(name='handover_frequency')
    handover_counts['handover_percentage'] = (handover_counts['handover_frequency'] / len(df[df['is_handover']]) * 100).round(2)
    
    # Merge handover information
    transition_counts = transition_counts.merge(handover_counts, on=['from_activity', 'to_activity'], how='left')
    transition_counts['handover_frequency'] = transition_counts['handover_frequency'].fillna(0)
    transition_counts['handover_percentage'] = transition_counts['handover_percentage'].fillna(0)
    
    # Sort by handover frequency
    transition_counts = transition_counts.sort_values('handover_frequency', ascending=False)
    
    return transition_counts, handover_details

def create_visualizations(transition_counts, handover_details, category_name):
    """Create visualizations for activity transitions analysis."""
    logger.info(f"Creating visualizations for {category_name}")
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Bar plot of top 5 handover transitions
    plt.figure(figsize=(12, 6))
    top_5 = transition_counts.head(5)
    
    # Create labels for x-axis
    labels = [f"{row['from_activity']}\n→\n{row['to_activity']}" 
             for _, row in top_5.iterrows()]
    
    plt.bar(range(len(top_5)), top_5['handover_frequency'], color='#00838f')
    plt.xticks(range(len(top_5)), labels, rotation=45, ha='right')
    plt.title(f'Top 5 Handover Activity Transitions ({category_name})')
    plt.xlabel('Activity Transition')
    plt.ylabel('Handover Frequency')
    
    # Add percentage labels
    for i, row in enumerate(top_5.itertuples()):
        plt.text(i, row.handover_frequency, f'{row.handover_percentage:.1f}%', 
                ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'{category_name}_top5_transitions.png'))
    plt.close()
    
    # 2. Create transition network visualization
    # Only show the top 20 most frequent handover transitions
    top_n = 20
    top_transitions = transition_counts.sort_values('handover_frequency', ascending=False).head(top_n)
    G = nx.DiGraph()
    
    # Add nodes and edges for top transitions only
    for _, row in top_transitions.iterrows():
        from_activity = row['from_activity']
        to_activity = row['to_activity']
        handover_freq = row['handover_frequency']
        
        if from_activity not in G:
            G.add_node(from_activity)
        if to_activity not in G:
            G.add_node(to_activity)
        if handover_freq > 0:
            G.add_edge(from_activity, to_activity, weight=handover_freq)
    
    # Create visualization
    plt.figure(figsize=(20, 15))
    if category_name == 'consignment':
        pos = nx.spring_layout(G, k=20, scale=5)
    else:
        pos = nx.kamada_kawai_layout(G, scale=2)
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=10000, alpha=0.7)
    edge_weights = [G[u][v]['weight'] for u, v in G.edges()]
    max_weight = max(edge_weights) if edge_weights else 1
    edge_widths = [1 + 4 * (w / max_weight) for w in edge_weights]
    nx.draw_networkx_edges(G, pos, width=edge_widths, edge_color='gray', arrows=True, arrowsize=20, connectionstyle='arc3,rad=0.2', alpha=0.6)
    labels = {node: node.replace(' ', '\n') for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=13, font_weight='bold', bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=3))
    plt.title(f'Activity Transition Network ({category_name})\nTop 20 handover transitions', pad=20, fontsize=12)
    plt.axis('off')
    edge_legend = plt.Line2D([0], [0], color='gray', linewidth=1 + 4 * (max_weight/max_weight), label=f'Max handovers: {max_weight:.0f}')
    plt.legend(handles=[edge_legend], loc='upper right', bbox_to_anchor=(1.1, 1.1))
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'{category_name}_transition_network.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Create heatmap of role transitions
    role_transitions = defaultdict(int)
    for key, details in handover_details.items():
        for role_key, count in details['roles'].items():
            role_transitions[role_key] += count
    
    # Convert to DataFrame for heatmap
    role_pairs = [pair.split(' → ') for pair in role_transitions.keys()]
    from_roles = [pair[0] for pair in role_pairs]
    to_roles = [pair[1] for pair in role_pairs]
    counts = list(role_transitions.values())
    
    role_df = pd.DataFrame({
        'from_role': from_roles,
        'to_role': to_roles,
        'count': counts
    })
    
    # Create pivot table for heatmap
    heatmap_data = role_df.pivot_table(
        values='count',
        index='from_role',
        columns='to_role',
        fill_value=0
    )
    
    plt.figure(figsize=(12, 8))
    sns.heatmap(heatmap_data, annot=True, fmt='.0f', cmap='YlOrRd')
    plt.title(f'Role Transition Heatmap ({category_name})')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'{category_name}_role_heatmap.png'))
    plt.close()

def main():
    """Main function to analyze activity transitions across all categories."""
    logger.info("Starting activity transition analysis")
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Store results for all categories
    all_results = {}
    
    for category_name, category_desc in ITEM_CATEGORIES.items():
        logger.info(f"\nProcessing category: {category_name}")
        
        # Find and load the XES file
        xes_file = os.path.join(INPUT_DIR, f"group_{category_name}.xes")
        logger.info(f"Looking for file: {xes_file}")
        
        if not os.path.exists(xes_file):
            logger.warning(f"File not found: {xes_file}")
            continue
        
        try:
            # Load and analyze the log
            logger.info(f"Loading log file: {xes_file}")
            log = xes_importer.apply(xes_file)
            logger.info(f"Successfully loaded log with {len(log)} cases")
            
            # Analyze activity transitions
            transition_counts, handover_details = analyze_activity_transitions(log, category_name)
            
            # Save results
            transition_counts.to_csv(os.path.join(OUTPUT_DIR, f"transitions_{category_name}.csv"), index=False)
            
            all_results[category_name] = {
                'transition_counts': transition_counts,
                'handover_details': handover_details
            }
            
            # Create visualizations
            create_visualizations(transition_counts, handover_details, category_name)
            
        except Exception as e:
            logger.error(f"Error processing {category_name}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Generate summary report
    logger.info("\nActivity Transition Analysis Summary:")
    for category, results in all_results.items():
        logger.info(f"\n{category}:")
        
        # Get top 5 handover transitions
        top_5 = results['transition_counts'].head(5)
        logger.info("Top 5 handover transitions:")
        
        for _, row in top_5.iterrows():
            transition = f"{row['from_activity']} → {row['to_activity']}"
            logger.info(f"  {transition}:")
            logger.info(f"    Handover frequency: {row['handover_frequency']} ({row['handover_percentage']}%)")
            logger.info(f"    Total transitions: {row['frequency']} ({row['percentage']}%)")

if __name__ == "__main__":
    main() 