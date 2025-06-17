#!/usr/bin/env python3
"""
Activity-based Handover Analysis

This script analyzes handovers between different activities/roles in the process,
rather than between specific users.
"""

import os
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from xml.etree import ElementTree as ET
from collections import defaultdict

# Input/Output settings
INPUT_DIR = './data/filtered'
OUTPUT_DIR = './data/analysis/visualizations'

def extract_activity_handovers(xes_file):
    """Extract handovers between activities from XES file."""
    tree = ET.parse(xes_file)
    root = tree.getroot()
    
    # Remove namespace for easier parsing
    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]
    
    handovers = defaultdict(int)
    
    # Process each trace
    for trace in root.findall('.//trace'):
        events = []
        for event in trace.findall('event'):
            activity = event.find("./string[@key='concept:name']").get('value')
            events.append(activity)
        
        # Record handovers in this trace
        for i in range(len(events)-1):
            handover = (events[i], events[i+1])
            handovers[handover] += 1
    
    return handovers

def create_handover_df():
    """Create DataFrame of handovers between activities."""
    all_handovers = defaultdict(int)
    
    # Process each XES file
    for file in os.listdir(INPUT_DIR):
        if file.endswith('.xes'):
            file_path = os.path.join(INPUT_DIR, file)
            print(f"\nProcessing {file}...")
            try:
                trace_handovers = extract_activity_handovers(file_path)
                for handover, count in trace_handovers.items():
                    all_handovers[handover] += count
            except Exception as e:
                print(f"Error processing {file}: {str(e)}")
    
    # Convert to DataFrame
    handover_data = []
    for (from_activity, to_activity), count in all_handovers.items():
        handover_data.append({
            'from_role': from_activity,
            'to_role': to_activity,
            'count': count
        })
    
    df = pd.DataFrame(handover_data)
    df['percentage'] = df['count'] / df['count'].sum() * 100
    return df.sort_values('count', ascending=False)

def create_ego_network(handover_metrics, central_activity, n_neighbors=5):
    """Create ego network visualization centered on specified activity."""
    print(f"\nCreating ego network for activity: {central_activity}")
    
    # Create directed graph
    G = nx.DiGraph()
    
    # Filter handovers involving central activity
    ego_handovers = handover_metrics[
        (handover_metrics['from_role'] == central_activity) |
        (handover_metrics['to_role'] == central_activity)
    ].nlargest(n_neighbors, 'count')
    
    print(f"\nFound {len(ego_handovers)} handovers:")
    print(ego_handovers)
    
    if len(ego_handovers) == 0:
        print(f"No handovers found for {central_activity}")
        return
    
    # Add edges with weights
    max_count = ego_handovers['count'].max()
    for _, row in ego_handovers.iterrows():
        G.add_edge(
            row['from_role'],
            row['to_role'],
            weight=row['count'],
            width=3 * row['count'] / max_count,
            count=row['count']
        )
    
    # Create layout
    pos = nx.spring_layout(G, k=1, seed=42)
    
    # Create figure with a specific size and add subplot
    fig, ax = plt.subplots(figsize=(15, 10))
    
    # Draw edges with varying thickness and color based on frequency
    edges = G.edges(data=True)
    edge_colors = [plt.cm.YlOrRd(data['count']/max_count) for _, _, data in edges]
    edge_widths = [data['width'] for _, _, data in edges]
    
    # Draw the network
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=edge_widths, alpha=0.7, ax=ax)
    
    # Draw nodes
    node_colors = ['lightcoral' if node == central_activity else 'lightblue' for node in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_size=2000, node_color=node_colors, alpha=0.7, ax=ax)
    
    # Draw labels with smaller font and word wrapping
    labels = {node: '\n'.join(node.split()) for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, font_weight='bold', ax=ax)
    
    # Add edge labels showing handover counts
    edge_labels = nx.get_edge_attributes(G, 'count')
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8)
    
    # Add title
    ax.set_title(f'Activity Handovers: {central_activity}\nTop {n_neighbors} Most Frequent Transitions', pad=20)
    
    # Add colorbar legend
    sm = plt.cm.ScalarMappable(cmap=plt.cm.YlOrRd, norm=plt.Normalize(vmin=0, vmax=max_count))
    plt.colorbar(sm, ax=ax, label='Handover Frequency')
    
    # Remove axis
    ax.set_axis_off()
    
    # Save visualization
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f'activity_network_{central_activity.lower().replace(" ", "_")}.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nSaved visualization to: {output_path}")
    plt.close()

def main():
    """Main function to create activity-based handover visualizations."""
    print("\nAnalyzing activity-based handovers...")
    handover_metrics = create_handover_df()
    
    print("\nTop 10 Activity Handovers:")
    print("-" * 50)
    print(handover_metrics.head(10))
    
    # Create ego networks for key activities
    key_activities = [
        'Create Purchase Order Item',
        'Record Invoice Receipt',
        'Clear Invoice'
    ]
    
    for activity in key_activities:
        create_ego_network(handover_metrics, activity)

if __name__ == "__main__":
    main() 