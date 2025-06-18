#!/usr/bin/env python3
"""
Role-based Handover Duration Analysis

This script analyzes how specific handovers between user roles and systems
correlate with case durations in the purchase-to-pay process.
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
OUTPUT_DIR = './data/analysis/role_correlations'

ITEM_CATEGORIES = {
    "3_way_after": "3-way match, invoice after GR",
    "3_way_before": "3-way match, invoice before GR",
    "2_way": "2-way match"
}

def analyze_role_handover_impact(category):
    """Analyze how specific role handovers impact case duration."""
    results = {}
    
    # Load handover and duration data
    handovers_file = os.path.join(ANALYSIS_DIR, 'handovers', f'handovers_{category}.csv')
    duration_file = os.path.join(ANALYSIS_DIR, 'handover_duration', f'duration_{category}_role_level.csv')
    
    try:
        handovers_df = pd.read_csv(handovers_file)
        duration_df = pd.read_csv(duration_file)
        
        # Analyze specific role combinations
        role_pairs = handovers_df.groupby(['from_role', 'to_role']).agg({
            'count': 'sum',
            'percentage': 'mean'
        }).reset_index()
        
        # Sort by frequency
        role_pairs = role_pairs.sort_values('count', ascending=False)
        
        # Calculate average duration for cases with each role pair
        role_pair_stats = []
        
        for _, row in role_pairs.iterrows():
            from_role = row['from_role']
            to_role = row['to_role']
            
            # Find cases with this handover pattern
            cases_with_pair = duration_df[
                (duration_df['most_frequent_handover'].str.contains(f"{from_role}->{to_role}", na=False))
            ]
            
            if not cases_with_pair.empty:
                avg_duration = cases_with_pair['duration'].mean()
                median_duration = cases_with_pair['duration'].median()
                case_count = len(cases_with_pair)
                
                role_pair_stats.append({
                    'from_role': from_role,
                    'to_role': to_role,
                    'handover_count': row['count'],
                    'handover_percentage': row['percentage'],
                    'avg_case_duration': avg_duration,
                    'median_case_duration': median_duration,
                    'affected_cases': case_count
                })
        
        results['role_pair_stats'] = pd.DataFrame(role_pair_stats)
        
        # Calculate correlation between handover frequency and duration
        if role_pair_stats:
            stats_df = pd.DataFrame(role_pair_stats)
            correlation = stats.pearsonr(
                stats_df['handover_count'],
                stats_df['avg_case_duration']
            )
            results['correlation'] = correlation[0]
            results['p_value'] = correlation[1]
            
            # Create visualization
            plt.figure(figsize=(12, 6))
            plt.scatter(stats_df['handover_count'], stats_df['avg_case_duration'], alpha=0.5)
            plt.xlabel('Number of Handovers')
            plt.ylabel('Average Case Duration (hours)')
            plt.title(f'Handover Frequency vs Case Duration - {ITEM_CATEGORIES[category]}')
            
            # Add trend line
            z = np.polyfit(stats_df['handover_count'], stats_df['avg_case_duration'], 1)
            p = np.poly1d(z)
            plt.plot(stats_df['handover_count'], p(stats_df['handover_count']), "r--", alpha=0.8)
            
            # Add correlation coefficient
            plt.text(0.05, 0.95, f'Correlation: {correlation[0]:.2f}\np-value: {correlation[1]:.3f}',
                    transform=plt.gca().transAxes,
                    bbox=dict(facecolor='white', alpha=0.8))
            
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            plt.savefig(os.path.join(OUTPUT_DIR, f'{category}_role_correlation.png'))
            plt.close()
            
            # Create heatmap of role handovers
            pivot_df = stats_df.pivot_table(
                values='avg_case_duration',
                index='from_role',
                columns='to_role',
                aggfunc='mean'
            )
            
            plt.figure(figsize=(12, 8))
            sns.heatmap(pivot_df, annot=True, fmt='.0f', cmap='YlOrRd')
            plt.title(f'Average Case Duration by Role Handover - {ITEM_CATEGORIES[category]}')
            plt.tight_layout()
            plt.savefig(os.path.join(OUTPUT_DIR, f'{category}_role_heatmap.png'))
            plt.close()
            
    except Exception as e:
        logger.error(f"Error analyzing {category}: {str(e)}")
        return None
    
    return results

def analyze_system_handovers(category):
    """Analyze handovers involving automated systems (batch processes)."""
    results = {}
    
    try:
        # Load handover data
        handovers_file = os.path.join(ANALYSIS_DIR, 'handovers', f'handovers_{category}.csv')
        handovers_df = pd.read_csv(handovers_file)
        
        # Identify system handovers (involving BATCH or automated processes)
        system_handovers = handovers_df[
            (handovers_df['from_role'].str.contains('BATCH|SYS|AUTO', na=False)) |
            (handovers_df['to_role'].str.contains('BATCH|SYS|AUTO', na=False))
        ]
        
        if not system_handovers.empty:
            # Calculate statistics for system handovers
            results['system_handover_count'] = len(system_handovers)
            results['system_handover_percentage'] = (len(system_handovers) / len(handovers_df)) * 100
            
            # Group by type of system handover
            system_stats = system_handovers.groupby(['from_role', 'to_role']).agg({
                'count': 'sum',
                'percentage': 'mean'
            }).reset_index()
            
            results['system_stats'] = system_stats.to_dict('records')
            
    except Exception as e:
        logger.error(f"Error analyzing system handovers for {category}: {str(e)}")
        return None
    
    return results

def main():
    """Main function to analyze role-based handovers across categories."""
    logger.info("Starting role-based handover analysis")
    
    all_results = {}
    
    for category in ITEM_CATEGORIES:
        logger.info(f"\nAnalyzing category: {category}")
        
        # Analyze role handovers
        role_results = analyze_role_handover_impact(category)
        system_results = analyze_system_handovers(category)
        
        if role_results and system_results:
            all_results[category] = {
                'role_analysis': role_results,
                'system_analysis': system_results
            }
            
            # Print summary statistics
            logger.info(f"\nResults for {ITEM_CATEGORIES[category]}:")
            
            if 'correlation' in role_results:
                logger.info(f"Overall correlation between handover frequency and duration: {role_results['correlation']:.3f}")
                logger.info(f"P-value: {role_results['p_value']:.3f}")
            
            if 'role_pair_stats' in role_results:
                stats_df = role_results['role_pair_stats']
                top_impact = stats_df.nlargest(3, 'avg_case_duration')
                
                logger.info("\nTop 3 handovers with highest average case duration:")
                for _, row in top_impact.iterrows():
                    logger.info(f"  {row['from_role']} → {row['to_role']}:")
                    logger.info(f"    Average duration: {row['avg_case_duration']:.2f} hours")
                    logger.info(f"    Frequency: {row['handover_count']} ({row['handover_percentage']:.1f}%)")
            
            if system_results.get('system_handover_count'):
                logger.info(f"\nSystem handovers:")
                logger.info(f"  Total system handovers: {system_results['system_handover_count']}")
                logger.info(f"  Percentage of all handovers: {system_results['system_handover_percentage']:.1f}%")
    
    # Save detailed results
    if all_results:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Create comparison of correlations across categories
        correlations = {
            category: results['role_analysis']['correlation']
            for category, results in all_results.items()
            if 'correlation' in results['role_analysis']
        }
        
        plt.figure(figsize=(10, 6))
        plt.bar(correlations.keys(), correlations.values())
        plt.title('Role Handover-Duration Correlation by Category')
        plt.ylabel('Correlation Coefficient')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, 'category_role_correlations.png'))
        plt.close()

if __name__ == "__main__":
    main() 