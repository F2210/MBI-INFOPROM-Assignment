#!/usr/bin/env python3
import pm4py
from pm4py.objects.log.importer.xes import importer as xes_importer
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test file path
xes_file = './data/filtered/preprocessed_handover/processed_group_2_way.xes'

logger.info(f"Attempting to read file: {xes_file}")

try:
    # Try to read the file
    log = xes_importer.apply(xes_file)
    logger.info(f"Successfully loaded log with {len(log)} cases")
    
    # Print first case info
    if len(log) > 0:
        first_case = log[0]
        logger.info(f"First case has {len(first_case)} events")
        logger.info(f"First event attributes: {first_case[0].keys()}")
except Exception as e:
    logger.error(f"Error reading file: {str(e)}")
    import traceback
    logger.error(traceback.format_exc()) 