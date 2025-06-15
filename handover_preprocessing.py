
import os
import gc
import logging
import traceback
from datetime import datetime
import json
import pm4py
from pm4py.objects.log.obj import EventLog
from analyze_logs import count_events
from resources_handover_preprocessing import get_resource_type, describe_log, compare_activities_in_folder, import_user_roles_from_txt, export_user_roles_to_txt, devide_on_category_item
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.exporter.xes import exporter as xes_exporter
from pm4py.algo.organizational_mining.roles import algorithm as roles_algo
from pm4py.objects.org.roles.obj import Role
import pandas as pd

import re
from sklearn.cluster import KMeans
import numpy as np
from collections import defaultdict


INPUT_FILE = './data/BPI_Challenge_2019.xes'
INPUT_DIR = './data/filtered'
OUTPUT_DIR = './data/filtered/preprocessed_handover'
ROLE_FILES_DIR = './data/filtered/preprocessed_handover/roles'
RESOURCE_FILES_DIR = './data/filtered/preprocessed_handover/splitted_roletype_logs'

COMPLETE_FILTERED_LOG = 'complete_filtered_log.xes'
SPLITTED_LOG_PREFIX = 'filtered_log_'

RESOURCE_TYPES = ["NONE", "Batch", "User"]

# Case attribute settings
CATEGORY_ATTRIBUTE = "Item Category" # for some reason: do not include "case:" in the name
CASE_ID_ATTRIBUTE = "concept:name"

# Item categories for grouping - modify these as needed
ITEM_CATEGORIES = {
    "group_3_way_before": ["3-way match, invoice before GR"],
    "group_3_way_after": ["3-way match, invoice after GR"],
    "group_2_way": ["2-way match"],
    "group_consignment": ["Consignment"]
}


# Merge all XES logs in OUTPUT_DIR into a single EventLog
def merge_xes_logs(input_dir, output_file=COMPLETE_FILTERED_LOG):
    merged_log = EventLog()
    for filename in os.listdir(input_dir):
        if filename.endswith('.xes'):
            file_path = os.path.join(input_dir, filename)
            try:
                log = xes_importer.apply(file_path)
                for trace in log:
                    merged_log.append(trace)
            except Exception as e:
                logging.error(f"Error reading {file_path}: {e}\n{traceback.format_exc()}")
    output_path = os.path.join(input_dir, output_file)
    pm4py.write_xes(merged_log, output_path)
    return merged_log

def split_on_resource_type(input_log, output_dir, output_log_name=COMPLETE_FILTERED_LOG):
    # Prepare sublogs for each resource type
    sublogs = {"NONE": [], "Batch": [], "User": []}


    # Prepare sublogs for each resource type
    sublogs = {"NONE": EventLog(), "Batch": EventLog(), "User": EventLog()}
    other_count = 0

    for trace in input_log:
        # Collect events by resource type for this trace
        events_by_type = {"NONE": [], "Batch": [], "User": [] , "Other": []}
        for event in trace:
            resource = event.get("org:resource", "NONE")
            rtype = get_resource_type(resource)
            if rtype in events_by_type:
                events_by_type[rtype].append(event)
            else:
                events_by_type["Other"].append(event)
                other_count += 1
        # For each resource type, if there are events, create a trace
        for rtype, events in events_by_type.items():
            if events:
                # Copy trace attributes
                new_trace = trace.__class__()
                for attr in trace.attributes:
                    new_trace.attributes[attr] = trace.attributes[attr]
                for event in events:
                    new_event = dict(event)
                    new_trace.append(new_event)
                sublogs[rtype].append(new_trace)
        
    print(f"Processed {len(input_log)} traces, found {other_count} events with unknown resource type.")

    # Export sublogs to XES
    for rtype, sublog in sublogs.items():
        if len(sublog) > 0:
            output_file = os.path.join(output_dir, f"{SPLITTED_LOG_PREFIX}{rtype}.xes")
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True) 
            xes_exporter.apply(sublog, output_file)
            print(f"Exported {len(sublog)} traces with {sum(len(trace) for trace in sublog)} events to {output_file}")

    return sublogs["User"]

def describe_logs():
    for rtype in RESOURCE_TYPES:
        input_file = os.path.join(OUTPUT_DIR, f"{SPLITTED_LOG_PREFIX}{rtype}.xes")
        if os.path.exists(input_file):
            print(f"Describing log for resource type: {rtype}")
            describe_log(input_file)
        else:
            print(f"Log file for resource type {rtype} does not exist. Skipping description.")

def apply_organizational_roles(log):
    """
    Applies pm4py's organizational_mining.roles function to the given XES log file.
    Returns the roles dictionary.
    """
    
    # Transform the xes_log_path to a list of (resource, activity) couples with their occurrence counts
    res_act_couples = {}
    for trace in log:
        for event in trace:
            resource = event.get("org:resource")
            activity = event.get("concept:name")
            if resource and activity:
                key = (resource, activity)
                res_act_couples[key] = res_act_couples.get(key, 0) + 1

    roles = roles_algo.apply(log)
    # Save roles to userRole.txt in ROLE_FILES_DIR
    roles_txt_path = os.path.join(ROLE_FILES_DIR, "userRoles.txt")
    os.makedirs(os.path.dirname(roles_txt_path), exist_ok=True)
    with open(roles_txt_path, "w", encoding="utf-8") as f:
        for idx, role in enumerate(roles):
            f.write(f"Role_{idx}: {role}\n")
    print(f"Roles exported to {roles_txt_path}, extracted {len(roles)} roles")
    return roles

def add_user_roles_to_log(log_path, resource_roles_list):
    """
    Adds a 'userRole' attribute to each event in the log based on the provided resource_roles_list.
    resource_roles_list: List of tuples/lists [(resource, role), ...]
    """

    user_to_role = {}

    for role_index, user_list in enumerate(resource_roles_list):
        for user in user_list:
            user_to_role[user] = role_index


    # Load the log
    log = xes_importer.apply(log_path)

    # Add 'userRole' attribute to each event
    for trace in log:
        for event in trace:
            resource = event.get("org:resource")
            if resource and resource in user_to_role:
                event["userRole"] = f"role_{user_to_role[resource]}"
            else:
                event["userRole"] = "Unknown"

    # Export the modified log
    output_file = os.path.splitext(log_path)[0] + "_with_UserRole.xes"
    xes_exporter.apply(log, output_file)
    print(f"Added userRole attribute to events and exported to {output_file}")

def extract_users_from_roles(roles):
    """
    Extracts user IDs from the roles list, which is expected to be a list of strings.
    Each string should contain a pattern like "Originators importance {user1, user2, ...}".
    Returns a list of user IDs.
    """
    user_ids = []
    for role in roles:
        if not isinstance(role, str):
            role = str(role)
        match = re.search(r"Originators importance\s*{([^}]*)}", role)
        if match:
            users_str = match.group(1)
            users_split = [user.strip() for user in users_str.split(",")]
            user_ids.append(users_split)
    print(f"Extracted {len(user_ids)} user lists from roles.")
    return user_ids

def copy_resource_to_userrole(input_file_path, output_file_path):
    """
    Imports a log from the given XES file, copies the value of the 'org:resource' attribute
    to a new attribute 'userRole' for each event, and exports the modified log to a new XES file.
    """
    log = xes_importer.apply(input_file_path)
    for trace in log:
        for event in trace:
            resource = event.get("org:resource", "Unknown")
            event["userRole"] = resource
    xes_exporter.apply(log, output_file_path)

def combine_logs(user_log):
    combined_log = EventLog()
    for rtype in RESOURCE_TYPES:
        log_path = os.path.join(ROLE_FILES_DIR, f"{SPLITTED_LOG_PREFIX}{rtype}_with_UserRole.xes")
        if os.path.exists(log_path):
            if rtype == "User":
                log = user_log  # Use the user log directly
            else:
                log = xes_importer.apply(log_path)
            for trace in log:
                combined_log.append(trace)
        else:
            print(f"Log file {log_path} does not exist. Skipping.")

    # Export the combined log
    combined_output_path = os.path.join(OUTPUT_DIR, "combined_with_roles.xes")
    xes_exporter.apply(combined_log, combined_output_path)
    print(f"Combined log with roles exported to {combined_output_path}")
    return combined_log

def assign_dominant_roles(roles, threshold: float = 0.3):
    """
    Assigns a significantly dominant role per user and returns:
    - A DataFrame with 'user_id' and 'dominant_role' (only where one is significantly dominant)
    - A list of users without a significantly dominant role

    :param roles: List of roles as returned by apply_organizational_roles (list of dicts with 'role' and 'users')
    :param threshold: Required margin between top role and next (e.g., 0.3 means 30%)
    :return: (dominant_roles_df, ambiguous_users)
    """
    # Build a mapping: user_id -> {role: importance}
    user_role_importance = {}
    # roles is a list of lists of dicts: [{user_id: importance, ...}, ...]
    for role_idx, role_dict in enumerate(roles):
        for item in role_dict:
            # Remove possible surrounding whitespace and quotes
            item = item.strip().strip('"').strip("'")
            if ':' in item:
                user, importance = item.split(':', 1)
                user = user.strip().strip("'").strip('"')
                importance = float(importance.strip())
            else:
                print('Warning: Item does not contain a colon, skipping:', item)
            if user not in user_role_importance:
                user_role_importance[user] = {}
            user_role_importance[user][role_idx] = importance

    print(f"Extracted user-role importance mapping: {user_role_importance["user_359"]}")

    dominant_roles = []
    ambiguous_users = []

    for user, role_importances in user_role_importance.items():
        sorted_roles = sorted(role_importances.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_roles) < 2:
            # Only one role - automatically dominant
            dominant_roles.append({'user_id': user, 'dominant_role': f'role_{sorted_roles[0][0]}'})
            continue

        top_role, top_importance = sorted_roles[0]
        next_role, next_importance = sorted_roles[1]

        if top_importance == 0:
            ambiguous_users.append(user)
            continue

        if (top_importance - next_importance) / top_importance >= threshold:
            dominant_roles.append({'user_id': user, 'dominant_role': f'role_{top_role}'})
        else:
            ambiguous_users.append({
                'user_id': user,
                'ambiguous_role_num': len(sorted_roles),
                'ambiguous_roles': [
                    {'role': f'role_{r[0]}', 'importance': r[1]} for r in sorted_roles
                ]
            })

    # Export dominant_roles in the requested format
    role_to_users = defaultdict(list)
    for entry in dominant_roles:
        role_to_users[entry['dominant_role']].append(entry['user_id'])

        dominant_roles_path = os.path.join(f"{ROLE_FILES_DIR}/txt", "dominant_roles_export.txt")
        os.makedirs(os.path.dirname(dominant_roles_path), exist_ok=True)
        with open(dominant_roles_path, "w", encoding="utf-8") as f:
                for role, users in role_to_users.items():
                    f.write(f"{role} ({len(users)}): [{', '.join(users)}]\n")
    print(f"Dominant roles exported to {dominant_roles_path} with {len(dominant_roles)} entries.")

    # Export ambiguous_users, each line is an item in the list as it is
    ambiguous_users_path = os.path.join(f"{ROLE_FILES_DIR}/txt", "ambiguous_users_export.txt")
    os.makedirs(os.path.dirname(ambiguous_users_path), exist_ok=True)
    with open(ambiguous_users_path, "w", encoding="utf-8") as f:
        for item in ambiguous_users:
            f.write(f"{str(item)}\n")
    print(f"Ambiguous users exported to {ambiguous_users_path} with {len(ambiguous_users)} entries.")

    return pd.DataFrame(dominant_roles), ambiguous_users

def assign_user_roles_in_log(log, dominant_roles_df, ambiguous_users):
    """
    Assigns 'userRole' attribute to each event in the log:
    - If the user has a dominant role, assign that role.
    - If the user is in ambiguous_users, assign 'unclear'.
    """
    # Build lookup for dominant roles
    dominant_roles = dict(zip(dominant_roles_df['user_id'], dominant_roles_df['dominant_role']))
    # Build set of ambiguous user_ids
    ambiguous_user_ids = set()
    for entry in ambiguous_users:
        if isinstance(entry, dict):
            ambiguous_user_ids.add(entry['user_id'])
        elif isinstance(entry, str):
            ambiguous_user_ids.add(entry)
    # Assign userRole in log
    for trace in log:
        for event in trace:
            resource = event.get("org:resource")
            if resource in dominant_roles:
                event["userRole"] = dominant_roles[resource]
            elif resource in ambiguous_user_ids:
                event["userRole"] = "unclear"
            else:
                event["userRole"] = "Unknown"
    # Export the modified log
    output_file = os.path.join(ROLE_FILES_DIR, "filtered_log_User_with_UserRole.xes")
    xes_exporter.apply(log, output_file)
    print(f"Exported log with user roles to {output_file}")
    return log


if __name__ == "__main__":
    # MERGE CATEGORIZED LOGS FROM PREPROCESSING
    user_log_path = os.path.join(RESOURCE_FILES_DIR, f"filtered_log_User.xes")


    if not os.path.exists(user_log_path):
        combined_filtered_log = os.path.join(INPUT_DIR, COMPLETE_FILTERED_LOG)
        if os.path.exists(combined_filtered_log):
            print(f"1. Using existing merged log: {combined_filtered_log}")
            merged_log = xes_importer.apply(combined_filtered_log)
        else:   
            print(f"1. Merging logs in {INPUT_DIR} into {COMPLETE_FILTERED_LOG}")
            merged_log = merge_xes_logs(INPUT_DIR)

        # 1. SPLIT ON RESOURCE TYPE
        user_log = split_on_resource_type(merged_log, RESOURCE_FILES_DIR, SPLITTED_LOG_PREFIX)

    else:
        print(f"1. Using existing user log: {user_log_path}")
        user_log = xes_importer.apply(user_log_path)
  
    # describe_logs()

    # 2. CLUSTER ON USER ROLES
    userRoles_log_path = os.path.join(ROLE_FILES_DIR, "userRoles.txt")
    if os.path.exists(userRoles_log_path):
        print(f"2. Importing user roles from {userRoles_log_path}")
        roles = import_user_roles_from_txt(userRoles_log_path)
    else:
        print("2. Applying organizational roles mining on user log")
        roles = apply_organizational_roles(user_log)

    # 3. ADD USER ROLES TO LOGS
    userRole_log_path = os.path.join(ROLE_FILES_DIR, "filtered_log_User_with_UserRole.xes")
    if os.path.exists(userRole_log_path):
        print(f"3. User roles already assigned in log: {userRole_log_path}")
        userRole_log = xes_importer.apply(userRole_log_path)
    else:
        print("3. Assigning user roles in log")
        resources_per_role = extract_users_from_roles(roles)
        dominant_df, ambiguous_users = assign_dominant_roles(resources_per_role, threshold=0.3)
        userRole_log = assign_user_roles_in_log(
            user_log,
            dominant_df,
            ambiguous_users
        )
    # print(f"Assigned user roles in log. Dominant roles: {len(dominant_df)}, Ambiguous users: {len(ambiguous_users)}")

    # 4. COPY RESOURCE TO USERROLE
    for output_path, input_path in [
        (os.path.join(ROLE_FILES_DIR, f"{SPLITTED_LOG_PREFIX}Batch_with_UserRole.xes"), os.path.join(RESOURCE_FILES_DIR, f"{SPLITTED_LOG_PREFIX}Batch.xes")),
        (os.path.join(ROLE_FILES_DIR, f"{SPLITTED_LOG_PREFIX}NONE_with_UserRole.xes"), os.path.join(RESOURCE_FILES_DIR, f"{SPLITTED_LOG_PREFIX}NONE.xes"))
    ]:
        if not os.path.exists(output_path):
            print(f"4. Copying 'org:resource' to 'userRole' in {output_path}")
            copy_resource_to_userrole(input_path, output_path)

    # 5. COMBINE LOGS
    print("5. Combining logs with user roles")
    combined_logs_with_userrole = combine_logs(userRole_log)
    print("Combining resources log completed")

    categorized_items_dir = os.path.join(OUTPUT_DIR, "preprocessed_categorized_logs")
    if not os.path.exists(categorized_items_dir):
        os.makedirs(categorized_items_dir)

    # 6. DIVIDE ON ITEM CATEGORIES
    print("6. Dividing logs on item categories")
    devide_on_category_item(combined_logs_with_userrole, categorized_items_dir, ITEM_CATEGORIES)
    