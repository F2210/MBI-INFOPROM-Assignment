import os
import xml.etree.ElementTree as ET
from pm4py.objects.log.obj import EventLog
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.exporter.xes import exporter as xes_exporter
from collections import defaultdict
import numpy as np
import pandas as pd
# from pm4py.algo.organizational_mining.roles import algorithm as roles_miner
# from pm4py.objects.org.roles.obj import Role
from sklearn.cluster import AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
# Visualize the clusters using pandas and matplotlib
import matplotlib.pyplot as plt

FILTERED_INPUT_FILES = [
    # "data/filtered/group_2_way.xes",
    "data/filtered/group_3_way_after.xes",
#     "data/filtered/group_3_way_before.xes",
#     "data/filtered/group_consignment.xes",
]

NUMBER_ROLES = 4  # Number of roles to discover

OUTPUT_DIR = "data/filtered/preprocessed_handover"


def get_resource_type(resource):
    if resource == "NONE":
        return "NONE"
    elif resource.startswith("batch_"):
        return "Batch"
    elif resource.startswith("user_"):
        return "User"
    else:
        return "Other"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def preprocess_xes_file(input_file):
    tree = ET.parse(input_file)
    # root = tree.getroot()
    log_name = os.path.splitext(os.path.basename(input_file))[0]

    # Prepare sublogs for each resource type
    sublogs = {"NONE": [], "Batch": [], "User": []}

    # Import the log using pm4py
    log = xes_importer.apply(input_file)

    # Prepare sublogs for each resource type
    sublogs = {"NONE": EventLog(), "Batch": EventLog(), "User": EventLog()}
    other_count = 0

    for trace in log:
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
        
        # print(f"Processed trace with {len(trace)} events, split into {len(events_by_type['NONE'])} NONE, "
        #     f"{len(events_by_type['Batch'])} Batch, {len(events_by_type['User'])} User, "
        #     f"{len(events_by_type['Other'])} Other events.")

    print(f"Processed {len(log)} traces, found {other_count} events with unknown resource type.")

    # Export sublogs to XES
    for rtype, sublog in sublogs.items():
        if len(sublog) > 0:
            output_file = os.path.join(OUTPUT_DIR, f"{log_name}_{rtype}.xes")
            xes_exporter.apply(sublog, output_file)
            print(f"Exported {len(sublog)} traces with {sum(len(trace) for trace in sublog)} events to {output_file}")

def create_resource_activity_matrix_and_assign_roles(input_file):
    # Import the log using pm4py
    log = xes_importer.apply(input_file)
    # Build resource-activity matrix
    resources = set()
    activities = set()
    for trace in log:
        for event in trace:
            resource = event.get("org:resource", "NONE")
            activity = event.get("concept:name", "UNKNOWN")
            resources.add(resource)
            activities.add(activity)
    resources = sorted(resources)
    activities = sorted(activities)
    matrix = pd.DataFrame(0, index=resources, columns=activities)
    for trace in log:
        for event in trace:
            resource = event.get("org:resource", "NONE")
            activity = event.get("concept:name", "UNKNOWN")
            matrix.loc[resource, activity] += 1

    # Use the resource-activity matrix to calculate roles using clustering

    n_roles = NUMBER_ROLES  # Number of roles to discover

    labels, matrix_norm = cluster_agglomerative(matrix, n_clusters=n_roles)
 
    labels_1, corr_matrix = cluster_by_correlation(matrix, n_clusters=n_roles)

    create_scatterplot(matrix, matrix_norm, labels)
    create_scatterplot(matrix, corr_matrix, labels_1)

    # Group resources by cluster label
    roles = []
    for role_idx in range(n_roles):
        members = matrix.index[labels == role_idx].tolist()
        roles.append(members)

    print(f"Calculated {n_roles} roles using clustering on the resource-activity matrix.")
    
    # Export roles as CSV
    # export_roles(roles, input_file)

    resource_to_role = {}
    # print(f"Discovered roles: {len(roles)}", roles)
    for idx, members in enumerate(roles):        
        for member in members:
            resource_to_role[member] = f"UserRole_{idx+1}"

    # Assign userRole to each event and write new log
    print(f"Resource-activity matrix:\n{matrix}")

    # Export the new log
    create_log_with_roles(input_file, log, resource_to_role)

    # Export the resource-activity matrix as CSV in the roles folder
    export_resource_activity_matrix(matrix, input_file)
    return matrix
    # return matrix, output_file

def export_roles(roles, output_file):
    """
    Export roles to a CSV file.
    
    Args:
        roles: Dictionary of roles and their members
        output_file: Path to the output CSV file
    """
    # Create the roles directory inside OUTPUT_DIR if it doesn't exist
    roles_dir = os.path.join(OUTPUT_DIR, "roles")
    os.makedirs(roles_dir, exist_ok=True)
    roles_csv_file = os.path.join(roles_dir, f"{os.path.splitext(os.path.basename(output_file))[0]}_roles.csv")
    
    roles_list = []
    for idx, role in enumerate(roles):
        print(f"Role {idx+1}: {role}")

    roles_df = pd.DataFrame(roles_list)
    roles_df.to_csv(roles_csv_file, index=False)
    print(f"Exported roles to {roles_csv_file}")

def describe_logs(input_file):
    """
    Describe the log by printing key statistics.
    
    Args:
        input_file: Path to the XES file
    """
    for rtype in ["NONE", "Batch", "User"]:
        output_file = os.path.join(OUTPUT_DIR, f"{os.path.splitext(os.path.basename(input_file))[0]}_{rtype}.xes")
        if not os.path.exists(output_file):
            print(f"Output file {output_file} does not exist. Skipping description.")
            continue

        log = xes_importer.apply(input_file)
        num_traces = len(log)
        num_events = sum(len(trace) for trace in log)
        
        print(f"Log: {os.path.basename(input_file)}")
        print(f"  - Number of traces: {num_traces}")
        print(f"  - Number of events: {num_events}")
        
        # Print unique resources and activities
        resources = set()
        activities = set()
        for trace in log:
            for event in trace:
                resources.add(event.get("org:resource", "NONE"))
                activities.add(event.get("concept:name", "UNKNOWN"))
        
        print(f"  - Unique resources: {len(resources)}")
        print(f"  - Unique activities: {len(activities)}")

def create_scatterplot(matrix, matrix_norm, labels):
    if matrix.shape[1] >= 2:
        # Use the first two principal components for visualization
        pca = PCA(n_components=2)
        matrix_pca = pca.fit_transform(matrix_norm)
        df_vis = pd.DataFrame(matrix_pca, columns=["PC1", "PC2"])
        df_vis["Cluster"] = labels
        plt.figure(figsize=(8, 6))
        scatter = plt.scatter(df_vis["PC1"], df_vis["PC2"], c=df_vis["Cluster"], cmap="tab10", s=100, edgecolor='k')
        plt.title("Resource Clusters (PCA projection)")
        plt.xlabel("PC1")
        plt.ylabel("PC2")
        plt.legend(*scatter.legend_elements(), title="Cluster")
        plt.tight_layout()
        plt.show()
    else:
        print("Not enough activities for scatterplot visualization.")

def cluster_agglomerative(matrix, n_clusters=4):
    """
    Perform agglomerative clustering on the resource-activity matrix.
    
    Args:
        matrix: Resource-activity matrix
        n_clusters: Number of clusters to form
    
    Returns:
        labels: Cluster labels for each resource
    """
    # Normalize the matrix (optional, but helps clustering)
    matrix_norm = StandardScaler().fit_transform(matrix.values)

    clustering = AgglomerativeClustering(n_clusters=n_clusters)
    labels = clustering.fit_predict(matrix_norm)
    
    return labels, matrix_norm

def cluster_by_correlation(matrix, n_clusters=4):
    """
    Cluster resources based on the correlation of their activity profiles.

    Args:
        matrix: Resource-activity matrix (pandas DataFrame)
        n_clusters: Number of clusters to form

    Returns:
        labels: Cluster labels for each resource
        corr_matrix: Correlation matrix used for clustering
    """
    # Compute the correlation matrix (resources x resources)
    corr_matrix = matrix.T.corr().fillna(0)
    # Convert correlation to distance (1 - correlation)
    distance_matrix = 1 - corr_matrix.values

    # Perform clustering on the distance matrix
    clustering = AgglomerativeClustering(
        n_clusters=n_clusters,
        affinity='precomputed',
        linkage='average'
    )
    labels = clustering.fit_predict(distance_matrix)
    return labels, corr_matrix

def export_resource_activity_matrix(matrix, input_file):
    """
    Export the resource-activity matrix to a CSV file.
    
    Args:
        matrix: Resource-activity matrix (pandas DataFrame)
        output_file: Path to the output CSV file
    """
    roles_dir = os.path.join(OUTPUT_DIR, "roles")
    os.makedirs(roles_dir, exist_ok=True)
    matrix_csv_file = os.path.join(roles_dir, f"{os.path.splitext(os.path.basename(input_file))[0]}_resource_activity_matrix.csv")
    matrix.to_csv(matrix_csv_file)
    print(f"Exported resource-activity matrix to {matrix_csv_file}")

def create_log_with_roles(input_file, log, resource_to_role):
    """
    Create a new log with user roles assigned based on the resource-activity matrix.
    
    Args:
        input_file: Path to the input XES file
        resource_to_role: Dictionary mapping resources to roles
    
    Returns:
        new_log: EventLog with user roles assigned
    """
    new_log = EventLog()
    for trace in log:
        new_trace = trace.__class__()
        for attr in trace.attributes:
            new_trace.attributes[attr] = trace.attributes[attr]
        for event in trace:
            new_event = dict(event)
            resource = event.get("org:resource", "NONE")
            new_event["userRole"] = resource_to_role.get(resource, "UserRole_UNKNOWN")
            new_trace.append(new_event)
        new_log.append(new_trace)

    output_file = os.path.join(OUTPUT_DIR, f"{os.path.splitext(os.path.basename(input_file))[0]}_userRole.xes")
    xes_exporter.apply(new_log, output_file)
    print(f"Exported log with userRole to {output_file}")
    return new_log

if __name__ == "__main__":
    for input_file in FILTERED_INPUT_FILES:
        if os.path.exists(input_file):
            # preprocess_xes_file(input_file)
            # describe_logs(input_file)

            # Create resource-activity matrix and assign roles
            for rtype in ["User"]:
                output_file = os.path.join(OUTPUT_DIR, f"{os.path.splitext(os.path.basename(input_file))[0]}_{rtype}.xes")
                if os.path.exists(output_file):
                    create_resource_activity_matrix_and_assign_roles(output_file)
        else:
            print(f"Input file {input_file} does not exist. Skipping.")
    
    print(f"Preprocessing complete. Sublogs saved to {OUTPUT_DIR}")
