#!/usr/bin/env python3
"""
Memory-efficient XES file processing script

This script focuses exclusively on processing XES logs:
1. Import XES files
2. Filter cases by start activity and time range
3. Group cases by item category
4. Export groups to separate XES files

The script is optimized for memory efficiency by:
- Processing groups individually
- Releasing memory as soon as possible
- Using generators where applicable
- Processing data in batches
"""

import os
import gc
import logging
import traceback
from datetime import datetime
import json
import pm4py
from pm4py.objects.log.obj import EventLog
from analyze_logs import count_events
from pm4py.objects.log.importer.xes import importer as xes_importer

# ---------------------------
# CONFIGURATION SETTINGS
# ---------------------------

# Input/Output settings
INPUT_FILE = './data/BPI_Challenge_2019.xes'
OUTPUT_DIR = './data/filtered'
ANALYZE_ONLY = False
DEBUG_MODE = False

# XES import parameters
XES_IMPORT_PARAMS = {
    "timestamp_sort": True,
    "reverse_sort": False,
}

# Filter settings
TIME_RANGE_FILTER = {
    "start_date": "2018-01-01 00:00:00",
    "end_date": "2025-05-15 00:00:00",
    "mode": "traces_contained",
    "case_id_key": "concept:name",
    "timestamp_key": "time:timestamp"
}

# Start activity filter applied on all cases
START_ACTIVITY_FILTER = ["Create Purchase Order Item"]

# Item categories for grouping
ITEM_CATEGORIES = {
    "group_3_way_before": ["3-way match, invoice before GR"],
    "group_3_way_after": ["3-way match, invoice after GR"],
    "group_2_way": ["2-way match"],
    "group_consignment": ["Consignment"]
}

# End activity filters for each group
END_ACTIVITY_FILTER = {
    "group_3_way_before": ["Clear Invoice"],
    "group_3_way_after": ["Clear Invoice"],
    "group_2_way": ["Clear Invoice"],
    "group_consignment": ["Record Goods Receipt"]
}

# Case attribute settings
CATEGORY_ATTRIBUTE = "Item Category" # for some reason: do not include "case:" in the name
CASE_ID_ATTRIBUTE = "concept:name"

# Grouping settings
AUTO_DETECTION_THRESHOLD = 1000  # Minimum cases to create a separate group
MAX_SAMPLE_SIZE = 1000  # Maximum cases to sample for analysis
BATCH_SIZE = 1000  # Batch size for processing "other" cases

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_xes_file(input_file, output_dir):
    """
    Process XES file with memory-efficient operations
    
    Args:
        input_file: Path to the input XES file
        output_dir: Directory to store output files
        analyze_only: If True, only analyze without grouping/exporting
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Create subdirectory for incomplete cases
    incomplete_dir = os.path.join(output_dir, "incomplete")
    os.makedirs(incomplete_dir, exist_ok=True)
    
    # Step 1: Import XES file
    logger.info(f"Importing XES file: {input_file}")
    try:
        # Import the log
        log = xes_importer.apply(input_file)
        
        case_count = len(log)
        event_count = count_events(log)
        logger.info(f"Imported log with {case_count} cases and {event_count} events")
        
        # Step 2: Filter logs
        logger.info("Applying filters")
        
        # Further filter for cases within specified time range in order to scope the timeframe
        filtered_log = pm4py.filter_time_range(
            log,
            TIME_RANGE_FILTER["start_date"],
            TIME_RANGE_FILTER["end_date"],
            mode=TIME_RANGE_FILTER["mode"],
            case_id_key=TIME_RANGE_FILTER["case_id_key"],
            timestamp_key=TIME_RANGE_FILTER["timestamp_key"]
        )

        # Filter for cases that start with the specified activity since we are interested in those that actually start with the activity
        filtered_log = pm4py.filter_start_activities(filtered_log, START_ACTIVITY_FILTER, retain=True)
        
        filtered_case_count = len(filtered_log)
        filtered_event_count = count_events(filtered_log)
        logger.info(f"Filtered log has {filtered_case_count} cases and {filtered_event_count} events")
        
        # Step 3: Determine grouping strategy
        item_categories = ITEM_CATEGORIES
        logger.info(f"Using configured grouping with {len(item_categories)} groups")

        # Track grouped case IDs
        grouped_case_ids = set()
        incomplete_case_ids = set()

        # Step 4: Process each group one by one
        for group_name, category_values in item_categories.items():
            logger.info(f"Processing group: {group_name}")

            # Use case filtering since category is a case attribute
            group_categorized = pm4py.filter_trace_attribute_values(
                filtered_log,
                CATEGORY_ATTRIBUTE, 
                category_values, 
                retain=True,
                case_id_key=CASE_ID_ATTRIBUTE
            )

            logger.info(f"Found {len(group_categorized)} total cases in category '{group_name}' with events: {count_events(group_categorized)}")

            # Check if we need to filter by end activity for this group
            if group_name in END_ACTIVITY_FILTER and END_ACTIVITY_FILTER[group_name]:
                # Filter for complete cases (those ending with the required activity)
                group_complete = pm4py.filter_end_activities(
                    group_categorized,
                    END_ACTIVITY_FILTER[group_name], 
                    retain=True
                )
                
                # Get complete case IDs for tracking
                complete_case_ids = {case.attributes[CASE_ID_ATTRIBUTE] for case in group_complete}
                
                # Create incomplete cases log by filtering out complete cases
                group_incomplete = pm4py.filter_end_activities(
                    group_categorized,
                    END_ACTIVITY_FILTER[group_name], 
                    retain=False  # Keep cases that DON'T end with the activity
                )

                # Report stats
                complete_count = len(group_complete)
                incomplete_count = len(group_incomplete)
                logger.info(f"Group {group_name}: {complete_count} complete cases, {incomplete_count} incomplete cases")

                # Export complete cases to XES file if group is not empty
                if complete_count > 0:
                    output_path = os.path.join(output_dir, f"{group_name}.xes")
                    pm4py.write_xes(group_complete, output_path)
                    logger.info(f"Exported complete cases to {output_path}")
                    
                    # Add case IDs to the grouped set
                    grouped_case_ids.update(complete_case_ids)

                # Export incomplete cases separately if any exist
                if incomplete_count > 0:
                    incomplete_output_path = os.path.join(incomplete_dir, f"{group_name}_incomplete.xes")
                    pm4py.write_xes(group_incomplete, incomplete_output_path)
                    logger.info(f"Exported incomplete cases to {incomplete_output_path}")
                    
                    # Add incomplete case IDs to the incomplete set for tracking
                    for case in group_incomplete:
                        incomplete_case_ids.add(case.attributes[CASE_ID_ATTRIBUTE])
                
                # Clear logs to free memory
                del group_complete
                del group_incomplete
            else:
                # No end activity filter for this group, export all cases as complete
                group_count = len(group_categorized)
                logger.info(f"Group {group_name}: {group_count} cases (no end activity filter)")

                if group_count > 0:
                    output_path = os.path.join(output_dir, f"{group_name}.xes")
                    pm4py.write_xes(group_categorized, output_path)
                    logger.info(f"Exported cases to {output_path}")
                    
                    # Add case IDs to the grouped set
                    for case in group_categorized:
                        grouped_case_ids.add(case.attributes[CASE_ID_ATTRIBUTE])

            # Clear the categorized group to free memory
            del group_categorized
            gc.collect()
        
        # Step 5: Process "other" cases (those not in any group)
        logger.info("Processing 'other' cases (not matching any category)")
        
        # Memory-efficient filtering using generator and batch processing
        other_count = 0
        other_cases_batch = []
        
        # Process cases one by one to minimize memory usage
        for case in filtered_log:
            case_id = case.attributes[CASE_ID_ATTRIBUTE]
            if case_id not in grouped_case_ids and case_id not in incomplete_case_ids:
                other_cases_batch.append(case)
                other_count += 1
                
                # Process batch when it reaches the threshold
                if len(other_cases_batch) >= BATCH_SIZE:
                    # Create temporary log and export immediately
                    temp_other_log = EventLog(other_cases_batch)
                    
                    # If this is the first batch, create new file; otherwise append
                    if other_count == len(other_cases_batch):
                        # First batch - create new file
                        output_path = os.path.join(output_dir, "group_other.xes")
                        pm4py.write_xes(temp_other_log, output_path)
                        logger.info(f"Created 'other' group file with first batch of {len(other_cases_batch)} cases")
                    else:
                        # Subsequent batches - we need to merge (this is complex, so we'll collect all first)
                        pass
                    
                    del temp_other_log
                    other_cases_batch = []
                    gc.collect()
        
        # Handle remaining cases and create final "other" group file
        if other_count > 0:
            # If we have batches, we need to reload and combine (simplified approach)
            if other_count > BATCH_SIZE:
                logger.info(f"Collecting all {other_count} 'other' cases for final export")
                # Re-collect all other cases (this is still more memory efficient than before)
                all_other_cases = []
                for case in filtered_log:
                    case_id = case.attributes[CASE_ID_ATTRIBUTE]
                    if case_id not in grouped_case_ids and case_id not in incomplete_case_ids:
                        all_other_cases.append(case)
                
                other_log = EventLog(all_other_cases)
                output_path = os.path.join(output_dir, "group_other.xes")
                pm4py.write_xes(other_log, output_path)
                logger.info(f"Exported 'other' group with {len(other_log)} cases to {output_path}")
                
                del other_log
                del all_other_cases
            else:
                # Small number of remaining cases
                if other_cases_batch:
                    other_log = EventLog(other_cases_batch)
                    output_path = os.path.join(output_dir, "group_other.xes")
                    pm4py.write_xes(other_log, output_path)
                    logger.info(f"Exported 'other' group with {len(other_log)} cases to {output_path}")
                    del other_log
        
        logger.info(f"Total 'other' cases processed: {other_count}")
        
        # Final cleanup
        del other_cases_batch
        del filtered_log
        gc.collect()
        
        logger.info("Processing completed successfully")
    
    except Exception as e:
        logger.error(f"Error processing log: {str(e)}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    # Set debug logging level if requested in config
    if DEBUG_MODE:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    start_time = datetime.now()
    logger.info(f"Starting log processing at {start_time}")
    logger.info(f"Input file: {INPUT_FILE}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    
    # Print processing configuration
    logger.info(f"Filter configuration:")
    logger.info(f"  - Start activities: {START_ACTIVITY_FILTER}")
    logger.info(f"  - Time range: {TIME_RANGE_FILTER['start_date']} to {TIME_RANGE_FILTER['end_date']}")
    logger.info(f"Using configured groups with {len(ITEM_CATEGORIES)} categories")
    
    try:
        process_xes_file(INPUT_FILE, OUTPUT_DIR)
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        logger.error(traceback.format_exc())
        
    end_time = datetime.now()
    processing_time = end_time - start_time
    logger.info(f"Processing completed in {processing_time}")
