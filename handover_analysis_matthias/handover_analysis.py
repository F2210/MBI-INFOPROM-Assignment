#!/usr/bin/env python3
"""
Handover Pairs Analysis

This script analyzes handovers between roles in the process mining event log.
It identifies and counts role-to-role handovers within each process category.
"""

import os
import logging
import time
from collections import defaultdict, Counter
import pandas as pd
import pm4py
from pm4py.objects.log.importer.xes import importer as xes_importer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Input/Output settings
INPUT_DIR = './data/filtered/preprocessed_handover/preprocessed_categorized_logs'
OUTPUT_DIR = './data/analysis/handovers'

# Item categories for analysis - only 2_way for testing
ITEM_CATEGORIES = {
    "3_way_after": ["3-way match, invoice after GR"],
    "3_way_before": ["3-way match, invoice before GR"],
    "2_way": ["2-way match"],
    "consignment": ["Consignment"]
}

def analyze_handover_pairs(log, category_name):
    """
    Analyze handover pairs in a log for a specific category.
    
    Args:
        log: PM4Py event log
        category_name: Name of the category being analyzed
        
    Returns:
        DataFrame containing handover pair frequencies
    """
    start_time = time.time()
    logger.info(f"Starting handover analysis for {category_name}")
    logger.info(f"Number of cases in log: {len(log)}")
    
    handover_counts = Counter()
    total_handovers = 0
    
    # Process each case
    for case_idx, case in enumerate(log):
        if case_idx % 10 == 0:  # Log progress every 10 cases
            elapsed_time = time.time() - start_time
            logger.info(f"Processing case {case_idx} of {len(log)} (elapsed time: {elapsed_time:.2f}s)")
            
        # Get all events in the case
        events = list(case)
        logger.info(f"Case {case_idx} has {len(events)} events")
        
        # Compare consecutive events for role changes
        for i in range(len(events) - 1):
            current_event = events[i]
            next_event = events[i + 1]
            
            # Get roles from events using userRole attribute
            current_role = current_event.get("userRole", "UNKNOWN")
            next_role = next_event.get("userRole", "UNKNOWN")
            
            # If roles are different, record the handover
            if current_role != next_role or current_role == "unclear" or next_role != "unclear":
                handover_pair = (current_role, next_role)
                handover_counts[handover_pair] += 1
                total_handovers += 1
    
    logger.info(f"Found {total_handovers} total handovers in {len(handover_counts)} unique pairs")
    
    # Convert to DataFrame
    if handover_counts:
        df = pd.DataFrame([
            {
                'from_role': pair[0],
                'to_role': pair[1],
                'count': count,
                'percentage': (count / total_handovers) * 100
            }
            for pair, count in handover_counts.items()
        ])
        df = df.sort_values('count', ascending=False)
        df['category'] = category_name
        return df
    else:
        return pd.DataFrame(columns=['from_role', 'to_role', 'count', 'percentage', 'category'])

def main():
    """Main function to analyze handovers across all categories."""
    start_time = time.time()
    logger.info("Starting handover analysis")
    logger.info(f"Input directory: {INPUT_DIR}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Store results for all categories
    category_results = {}
    
    for category_name, category_values in ITEM_CATEGORIES.items():
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
            
            # Analyze handovers
            results_df = analyze_handover_pairs(log, category_name)
            
            # Save category results
            output_file = os.path.join(OUTPUT_DIR, f"handovers_{category_name}.csv")
            results_df.to_csv(output_file, index=False)
            logger.info(f"Saved results to {output_file}")
            
            category_results[category_name] = results_df
            
        except Exception as e:
            logger.error(f"Error processing {category_name}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Combine all results
    if category_results:
        combined_df = pd.concat(category_results.values(), ignore_index=True)
        combined_output = os.path.join(OUTPUT_DIR, "handovers_all_categories_new.csv")
        combined_df.to_csv(combined_output, index=False)
        logger.info(f"Saved combined results to {combined_output}")
        
        # Print summary statistics
        logger.info("\nHandover Analysis Summary:")
        for category, df in category_results.items():
            total_handovers = df['count'].sum()
            unique_pairs = len(df)
            logger.info(f"\n{category}:")
            logger.info(f"  Total handovers: {total_handovers}")
            logger.info(f"  Unique handover pairs: {unique_pairs}")
            logger.info("  Top 5 most frequent handovers:")
            for _, row in df.head().iterrows():
                logger.info(f"    {row['from_role']} -> {row['to_role']}: {row['count']} ({row['percentage']:.1f}%)")
    else:
        logger.warning("No results were generated for any category")
    
    total_time = time.time() - start_time
    logger.info(f"\nTotal execution time: {total_time:.2f} seconds")

if __name__ == "__main__":
    main() 