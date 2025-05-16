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
START_ACTIVITY_FILTER = ["Create Purchase Order Item"]
END_ACTIVITY_FILTER = []
TIME_RANGE_FILTER = {
    "start_date": "2018-01-01 00:00:00",
    "end_date": "2025-05-15 00:00:00",
    "mode": "traces_contained",
    "case_id_key": "concept:name",
    "timestamp_key": "time:timestamp"
}

# Case attribute settings
CATEGORY_ATTRIBUTE = "Item Category" # for some reason: do not include "case:" in the name
CASE_ID_ATTRIBUTE = "concept:name"

# Grouping settings
AUTO_DETECTION_THRESHOLD = 1000  # Minimum cases to create a separate group
MAX_SAMPLE_SIZE = 1000  # Maximum cases to sample for analysis
BATCH_SIZE = 1000  # Batch size for processing "other" cases

# Item categories for grouping - modify these as needed
ITEM_CATEGORIES = {
    "group_3_way_before": ["3-way match, invoice before GR"],
    "group_3_way_after": ["3-way match, invoice after GR"],
    "group_2_way": ["2-way match"],
    "group_consignment": ["Consignment"]
}

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_xes_file(input_file, output_dir, analyze_only=False):
    """
    Process XES file with memory-efficient operations
    
    Args:
        input_file: Path to the input XES file
        output_dir: Directory to store output files
        analyze_only: If True, only analyze without grouping/exporting
    """
    os.makedirs(output_dir, exist_ok=True)
    
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
            filtered_log,
            TIME_RANGE_FILTER["start_date"],
            TIME_RANGE_FILTER["end_date"],
            mode=TIME_RANGE_FILTER["mode"],
            case_id_key=TIME_RANGE_FILTER["case_id_key"],
            timestamp_key=TIME_RANGE_FILTER["timestamp_key"]
        )

        # Filter for cases that start with the specified activity since we are interested in those that actually start with the activity
        filtered_log = pm4py.filter_start_activities(log, START_ACTIVITY_FILTER, retain=True)

        # filter for cases that also end with the specified activity currently not used
        # filtered_log = pm4py.filter_end_activities(filtered_log, END_ACTIVITY_FILTER, retain=True)
        
        filtered_case_count = len(filtered_log)
        filtered_event_count = count_events(filtered_log)
        logger.info(f"Filtered log has {filtered_case_count} cases and {filtered_event_count} events")
        
        # For analysis-only mode, stop here
        if analyze_only:
            logger.info("Analysis completed, skipping grouping and export as requested.")
            return
        
        # Step 3: Determine grouping strategy
        item_categories = ITEM_CATEGORIES
        logger.info(f"Using configured grouping with {len(item_categories)} groups")

        # Track grouped case IDs
        grouped_case_ids = set()

        # Step 4: Process each group one by one
        for group_name, category_values in item_categories.items():
            logger.info(f"Processing group: {group_name}")

            group = None

            # Filter the log for this group
            try:
                # Use case filtering since category is a case attribute
                group = pm4py.filter_trace_attribute_values(
                    filtered_log,
                    CATEGORY_ATTRIBUTE, 
                    category_values, 
                    retain=True,
                    case_id_key=CASE_ID_ATTRIBUTE
                )
                
                # Report stats
                group_case_count = len(group)
                logger.info(f"Group {group_name} has {group_case_count} cases")
                
                # Export to XES file if group is not empty
                if group_case_count > 0:
                    output_path = os.path.join(output_dir, f"{group_name}.xes")
                    pm4py.write_xes(group, output_path)
                    logger.info(f"Exported group to {output_path}")
                    
                    # Add case IDs to the grouped set
                    for case in group:
                        grouped_case_ids.add(case.attributes[CASE_ID_ATTRIBUTE])
            except Exception as e:
                logger.error(f"Error processing group {group_name}: {str(e)}")
                logger.error(traceback.format_exc())
            finally:
                # Clear the group to free memory
                if group is not None:
                    del group
                    gc.collect()
        
        # Step 5: Process "other" cases (those not in any group)
        logger.info("Processing 'other' cases (not matching any category)")
        
        # Memory-efficient filtering using batches
        other_cases = []
        other_count = 0
        
        # Process in batches to reduce memory usage
        case_batch = []
        for case in filtered_log:
            if case.attributes[CASE_ID_ATTRIBUTE] not in grouped_case_ids:
                case_batch.append(case)
                other_count += 1
                
                # Process batch when it reaches the threshold
                if len(case_batch) >= BATCH_SIZE:
                    other_cases.extend(case_batch)
                    logger.info(f"Processed batch of {len(case_batch)} 'other' cases (total so far: {len(other_cases)})")
                    case_batch = []
                    # Force garbage collection to free memory
                    gc.collect()
        
        # Add any remaining cases in the last batch
        if case_batch:
            other_cases.extend(case_batch)
            logger.info(f"Processed final batch of {len(case_batch)} 'other' cases")
        
        logger.info(f"Total 'other' cases identified: {other_count}")
        
        # Create log for "other" cases
        if other_cases:
            # Convert to PM4Py log object
            other_log = EventLog(other_cases)
            
            # Export to XES file
            output_path = os.path.join(output_dir, "group_other.xes")
            pm4py.write_xes(other_log, output_path)
            logger.info(f"Exported 'other' group with {len(other_log)} cases to {output_path}")
            
            # Clear to free memory
            del other_log
        
        del other_cases
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
        process_xes_file(INPUT_FILE, OUTPUT_DIR, analyze_only=ANALYZE_ONLY)
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        logger.error(traceback.format_exc())
        
    end_time = datetime.now()
    processing_time = end_time - start_time
    logger.info(f"Processing completed in {processing_time}")
