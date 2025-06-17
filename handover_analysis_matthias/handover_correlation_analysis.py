#!/usr/bin/env python3
"""
Handover Correlation Analysis

This script analyzes the correlation between handovers and case duration across different categories.
It combines data from handover pairs, keypoints, and duration analysis to identify patterns and relationships.
"""

import os
import logging
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Input/Output settings
ANALYSIS_DIR = './data/analysis'
OUTPUT_DIR = './data/analysis/correlations'

# Categories for analysis
ITEM_CATEGORIES = {
    "3_way_after": "3-way match, invoice after GR",
    "3_way_before": "3-way match, invoice before GR",
    "2_way": "2-way match",
    "consignment": "Consignment"
}

def load_category_data(category):
    """Load all analysis data for a specific category."""
    data = {}
    
    # Load duration data
    duration_path = os.path.join(ANALYSIS_DIR, 'handover_duration')
    try:
        data['duration_role'] = pd.read_csv(os.path.join(duration_path, f'duration_{category}_role_level.csv'))
        data['duration_user'] = pd.read_csv(os.path.join(duration_path, f'duration_{category}_user_level.csv'))
    except Exception as e:
        logger.warning(f"Could not load duration data for {category}: {e}")
        return None

    # Load keypoints data
    keypoints_path = os.path.join(ANALYSIS_DIR, 'handover_keypoints')
    try:
        data['keypoints_roles'] = pd.read_csv(os.path.join(keypoints_path, f'keypoints_{category}_roles.csv'))
        data['keypoints_transitions'] = pd.read_csv(os.path.join(keypoints_path, f'keypoints_{category}_transitions.csv'))
    except Exception as e:
        logger.warning(f"Could not load keypoints data for {category}: {e}")
    
    # Load handover pairs data
    handovers_path = os.path.join(ANALYSIS_DIR, 'handovers')
    try:
        data['handovers'] = pd.read_csv(os.path.join(handovers_path, f'handovers_{category}.csv'))
    except Exception as e:
        logger.warning(f"Could not load handovers data for {category}: {e}")
    
    return data

def analyze_duration_correlation(data, category):
    """Analyze correlation between handovers and duration for a category."""
    results = {}
    
    if 'duration_role' in data:
        df = data['duration_role']
        
        # Calculate correlations
        correlations = {
            'total_handovers': stats.pearsonr(df['total_handovers'], df['duration']),
            'unique_handovers': stats.pearsonr(df['unique_handovers'], df['duration'])
        }
        
        # Basic statistics
        stats_dict = {
            'mean_duration': df['duration'].mean(),
            'median_duration': df['median'].median() if 'median' in df else None,
            'mean_handovers': df['total_handovers'].mean(),
            'mean_unique_handovers': df['unique_handovers'].mean()
        }
        
        results['correlations'] = correlations
        results['statistics'] = stats_dict
        
        # Create visualization
        plt.figure(figsize=(10, 6))
        plt.scatter(df['total_handovers'], df['duration'], alpha=0.5)
        plt.title(f'Case Duration vs Total Handovers ({ITEM_CATEGORIES[category]})')
        plt.xlabel('Number of Handovers')
        plt.ylabel('Case Duration (hours)')
        
        # Add correlation line
        z = np.polyfit(df['total_handovers'], df['duration'], 1)
        p = np.poly1d(z)
        plt.plot(df['total_handovers'], p(df['total_handovers']), "r--", alpha=0.8)
        
        # Add correlation coefficient
        corr = correlations['total_handovers'][0]
        plt.text(0.05, 0.95, f'Correlation: {corr:.2f}', 
                transform=plt.gca().transAxes, 
                bbox=dict(facecolor='white', alpha=0.8))
        
        # Save plot
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        plt.savefig(os.path.join(OUTPUT_DIR, f'{category}_correlation.png'))
        plt.close()
    
    return results

def analyze_keypoint_impact(data, category):
    """Analyze how different handover keypoints affect duration."""
    results = {}
    
    if all(k in data for k in ['duration_role', 'keypoints_transitions']):
        # Group cases by number of unique handover points
        df = data['duration_role']
        keypoints = data['keypoints_transitions']
        
        # Get top 5 most frequent handover points
        top_keypoints = keypoints.nlargest(5, 'frequency')
        results['top_keypoints'] = top_keypoints.to_dict('records')
        
        # Calculate average duration for cases with different numbers of unique handovers
        duration_by_unique = df.groupby('unique_handovers')['duration'].agg(['mean', 'count', 'std']).reset_index()
        results['duration_by_unique_handovers'] = duration_by_unique.to_dict('records')
    
    return results

def main():
    """Main function to analyze correlations across all categories."""
    logger.info("Starting correlation analysis")
    
    all_results = {}
    category_comparisons = []
    
    for category in ITEM_CATEGORIES:
        logger.info(f"\nAnalyzing category: {category}")
        
        # Load data for category
        data = load_category_data(category)
        if not data:
            continue
        
        # Analyze correlations
        correlation_results = analyze_duration_correlation(data, category)
        keypoint_results = analyze_keypoint_impact(data, category)
        
        all_results[category] = {
            'correlation_analysis': correlation_results,
            'keypoint_analysis': keypoint_results
        }
        
        # Collect data for category comparison
        if 'correlations' in correlation_results:
            category_comparisons.append({
                'category': category,
                'correlation_total': correlation_results['correlations']['total_handovers'][0],
                'correlation_unique': correlation_results['correlations']['unique_handovers'][0],
                'mean_duration': correlation_results['statistics']['mean_duration'],
                'mean_handovers': correlation_results['statistics']['mean_handovers']
            })
    
    # Create category comparison visualization
    if category_comparisons:
        comparison_df = pd.DataFrame(category_comparisons)
        
        plt.figure(figsize=(12, 6))
        x = range(len(comparison_df))
        width = 0.35
        
        plt.bar([i - width/2 for i in x], comparison_df['correlation_total'], width, 
                label='Total Handovers Correlation', color='skyblue')
        plt.bar([i + width/2 for i in x], comparison_df['correlation_unique'], width,
                label='Unique Handovers Correlation', color='lightgreen')
        
        plt.xlabel('Process Category')
        plt.ylabel('Correlation Coefficient')
        plt.title('Handover-Duration Correlation by Category')
        plt.xticks(x, comparison_df['category'], rotation=45)
        plt.legend()
        plt.tight_layout()
        
        plt.savefig(os.path.join(OUTPUT_DIR, 'category_comparison.png'))
        plt.close()
        
        # Save comparison results
        comparison_df.to_csv(os.path.join(OUTPUT_DIR, 'category_comparison.csv'), index=False)
    
    # Print summary
    logger.info("\nAnalysis Summary:")
    for category, results in all_results.items():
        logger.info(f"\n{ITEM_CATEGORIES[category]}:")
        if 'correlation_analysis' in results and 'correlations' in results['correlation_analysis']:
            corr = results['correlation_analysis']['correlations']['total_handovers'][0]
            logger.info(f"  Correlation with total handovers: {corr:.3f}")
            
            stats = results['correlation_analysis']['statistics']
            logger.info(f"  Average duration: {stats['mean_duration']:.2f} hours")
            logger.info(f"  Average handovers per case: {stats['mean_handovers']:.2f}")
        
        if 'keypoint_analysis' in results and 'top_keypoints' in results['keypoint_analysis']:
            logger.info("  Top handover keypoints:")
            for kp in results['keypoint_analysis']['top_keypoints'][:3]:
                logger.info(f"    {kp['from_activity']} → {kp['to_activity']}: {kp['frequency']} times")

if __name__ == "__main__":
    main() 