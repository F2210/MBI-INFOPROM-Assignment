import os
import pandas as pd
from collections import Counter
from statistics import mean, median, mode
import matplotlib.pyplot as plt
from pm4py.objects.log.importer.xes import importer as xes_importer
import glob
from collections import defaultdict

# Paths
INPUT_FOLDER = 'data/filtered/preprocessed_handover/preprocessed_categorized_logs'
OUTPUT_FOLDER = 'data/business_question_2'
WHOLE_PROCESS = False

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def calculate_handovers(trace):
    roles = [event['userRole'] for event in trace if 'userRole' in event]
    if len(roles) < 2:
        print(len(roles))
    handovers_between_roles = 0
    handovers_in_roles = 0
    for i in range(1, len(roles)):
        if roles[i-1] != roles[i]:
            handovers_between_roles += 1
        elif roles[i-1] == 'unclear' or roles[i] == 'unclear':
            # If either role is 'unclear', we count it as an out-role handover
            handovers_between_roles += 1
        else :
            handovers_in_roles += 1
    return handovers_between_roles, handovers_in_roles

def calculate_case_duration(trace):
    if len(trace) < 2:
        return 0, 1
    else:
        timestamps = [event['time:timestamp'] for event in trace if 'time:timestamp' in event]
        if len(timestamps) < 2:
             0, 1
        else:
            start_time = min(timestamps)
            end_time = max(timestamps)
            duration = (end_time - start_time).total_seconds() / 3600  # convert seconds to hours
            return duration, 0

def calculations_per_category():
    between_handovers_per_category = {}
    inside_handovers_per_category = {}
    duration_null_counts = {}
    duration_per_category = {}
    number_of_events_per_category = {}
    one_activity_per_category = []

    for filename in os.listdir(INPUT_FOLDER):
        if filename.endswith('.xes'):
            process_type = os.path.splitext(filename)[0]
            file_path = os.path.join(INPUT_FOLDER, filename)
            log = xes_importer.apply(file_path)
            one_activity_in_trace = []
            between_handovers_per_case = {}
            inside_handovers_per_case = {}
            durations_per_case = {}
            number_of_events = []
            for trace in log:
                case_id = trace.attributes.get('concept:name', None)
                number_of_events.append(len(trace))
                if len(trace) <= 1:
                    one_activity_in_trace.append(case_id)
                    continue
                # print(f"Processing case_id: {case_id} for process type: {process_type}")
                handovers_between_roles, handovers_in_roles = calculate_handovers(trace)
                between_handovers_per_case[case_id] = handovers_between_roles
                inside_handovers_per_case[case_id] = handovers_in_roles

                case_duration, extra_null = calculate_case_duration(trace)
                durations_per_case[case_id] = case_duration
            
            # Save Handover counts to CSV
            output_path = os.path.join(OUTPUT_FOLDER, f'{process_type}_handovers.csv')
            if not os.path.exists(output_path):
                # Combine case_id, between_handover_count, and inside_handover_count into a DataFrame
                df = pd.DataFrame([
                    {
                        'case_id': case_id,
                        'between_handover_count': between_handovers_per_case[case_id],
                        'inside_handover_count': inside_handovers_per_case[case_id]
                    }
                    for case_id in between_handovers_per_case
                ])
                df.to_csv(output_path, index=False)
            
            # Save Case Durations to CSV
            between_handovers_per_category[process_type] = list(between_handovers_per_case.values())
            inside_handovers_per_category[process_type] = list(inside_handovers_per_case.values())

            output_path = os.path.join(OUTPUT_FOLDER, f'{process_type}_case_durations.csv')
            if not os.path.exists(output_path):
                # Convert durations to seconds and handle None values
                pd.DataFrame(list(durations_per_case.items()), columns=['case_id', 'case_duration_seconds']).to_csv(output_path, index=False)
            duration_null_counts[process_type] = len(one_activity_in_trace)
            duration_per_category[process_type] = list(durations_per_case.values())

            number_of_events_per_category[process_type] = number_of_events

            one_activity_per_category.append(f"found {len(one_activity_in_trace)} cases with only one activity, from the {len(log)} in {process_type}")
            print(f"found {len(one_activity_in_trace)} cases with only one activity, from the {len(log)} in {process_type}")

    # Store the list one_activity_per_category in a txt file
    one_activity_path = os.path.join(OUTPUT_FOLDER, 'one_activity_cases.txt')
    with open(one_activity_path, 'w') as f:
        for line in one_activity_per_category:
            f.write(line + '\n')

    number_of_events_path = os.path.join(OUTPUT_FOLDER, 'events_average.txt')
    with open(number_of_events_path, 'w') as f:
        for process_type, activity_numbers in number_of_events_per_category.items():
            line = f"{process_type}: {sum(activity_numbers) / len(activity_numbers) if activity_numbers else 0} average number of events"
            f.write(line + '\n')
            filtered_activity_numbers = [num for num in activity_numbers if num > 1]
            second_line = f"{process_type}: {sum(filtered_activity_numbers) / len(filtered_activity_numbers) if activity_numbers else 0} average number of events (excluding cases with one activity)"
            f.write(second_line + '\n')
            median_val = median(activity_numbers) if activity_numbers else 0
            mode_val = mode(activity_numbers) if activity_numbers else 0
            f.write(f"{process_type}: {median_val} median number of events\n")
            f.write(f"{process_type}: {mode_val} mode number of events\n")
            filtered_median_val = median(filtered_activity_numbers) if filtered_activity_numbers else 0
            filtered_mode_val = mode(filtered_activity_numbers) if filtered_activity_numbers else 0
            f.write(f"{process_type}: {filtered_median_val} median number of events (excluding cases with one activity)\n")
            f.write(f"{process_type}: {filtered_mode_val} mode number of events (excluding cases with one activity)\n")
            f.write('\n')
            

    return duration_per_category, inside_handovers_per_category, between_handovers_per_category, duration_null_counts, one_activity_per_category

def calculate_statistics(between_handovers_per_category, inside_handovers_per_category, duration_per_category, duration_null_counts=None):
    # Calculate mean, median, mode for each process type
    between_handover_stats = calculate_stats(between_handovers_per_category, 'between_handover_count')
    inside_handover_stats = calculate_stats(inside_handovers_per_category, 'inside_handover_count')
    duration_stats = calculate_stats(duration_per_category)

    # Merge all stats into one DataFrame
    stats_df = pd.DataFrame(between_handover_stats)
    if not stats_df.empty and 'process_type' in stats_df.columns:
        stats_df = stats_df.rename(columns={
            'mean': 'between_handover_mean',
            'median': 'between_handover_median',
            'mode': 'between_handover_mode'
        })
    else:
        stats_df = pd.DataFrame(columns=['process_type', 'between_handover_mean', 'between_handover_median', 'between_handover_mode'])

    inside_df = pd.DataFrame(inside_handover_stats)
    if not inside_df.empty and 'process_type' in inside_df.columns:
        inside_df = inside_df.rename(columns={
            'mean': 'inside_handover_mean',
            'median': 'inside_handover_median',
            'mode': 'inside_handover_mode'
        })
    else:
        inside_df = pd.DataFrame(columns=['process_type', 'inside_handover_mean', 'inside_handover_median', 'inside_handover_mode'])

    duration_df = pd.DataFrame(duration_stats)
    if not duration_df.empty and 'process_type' in duration_df.columns:
        duration_df = duration_df.rename(columns={
            'mean': 'duration_mean',
            'median': 'duration_median',
            'mode': 'duration_mode'
        })
    else:
        duration_df = pd.DataFrame(columns=['process_type', 'duration_mean', 'duration_median', 'duration_mode'])

    null_counts_df = None
    if duration_null_counts is not None:
        null_counts_df = pd.DataFrame(list(duration_null_counts.items()), columns=['process_type', 'traces_with_one_activity'])

    # Merge all on process_type
    merged = stats_df.merge(inside_df, on='process_type', how='outer') \
                     .merge(duration_df, on='process_type', how='outer')
    
    if null_counts_df is not None:
        merged = merged.merge(null_counts_df, on='process_type', how='outer')

    merged.to_csv(os.path.join(OUTPUT_FOLDER, 'handover_and_duration_statistics.csv'), index=False)
    print(merged)


    # Create boxplots for each process type
    for process_type in duration_per_category:
        durations = duration_per_category[process_type]
        between_handovers = between_handovers_per_category[process_type]
        inside_handovers = inside_handovers_per_category[process_type]

        fig, ax1 = plt.subplots(figsize=(8, 6))
        fig.suptitle(f'Boxplots for {process_type}', y=0.9)

        # Boxplot for durations on left y-axis
        bp1 = ax1.boxplot([durations], positions=[1], widths=0.6, patch_artist=True,
                  boxprops=dict(facecolor='lightblue'), medianprops=dict(color='black'))
        ax1.set_ylabel('Duration (hours)', color='blue')
        xtick_positions = [1, 2, 3]
        xtick_labels = ['Duration (hours)', 'Handovers\nBetween Roles', 'Handovers\nWithin Roles']

        ax1.set_xticks(xtick_positions)
        ax1.set_xticklabels(xtick_labels)

        # Boxplots for handovers on right y-axis
        ax2 = ax1.twinx()
        bp2 = ax2.boxplot([between_handovers, inside_handovers], positions=[2, 3], widths=0.6, patch_artist=True,
                  boxprops=dict(facecolor='lightgreen'), medianprops=dict(color='black'))
        ax2.set_ylabel('Handovers Count', color='green')
        ax2.set_xticks(xtick_positions)
        ax2.set_xticklabels(xtick_labels)

        plt.tight_layout(rect=[0, 0.05, 1, 0.93])  # Adjust layout to reduce top margin
        plot_path = os.path.join(OUTPUT_FOLDER, f'{process_type}_boxplots.png')
        plt.savefig(plot_path)
        # plt.show()

    create_line_graphs(between_handovers_per_category, duration_per_category, postfix='duration_vs_between_handovers_line')
    create_line_graphs(inside_handovers_per_category, duration_per_category, postfix='duration_vs_inside_handovers_line')

def create_line_graphs(handovers_per_category, duration_per_category, postfix=''): 
    # Create line graphs: x = between handovers, y = case duration, for each process type
    for process_type in duration_per_category:
        durations = duration_per_category[process_type]
        handovers = handovers_per_category[process_type]
        # Aggregate durations by handovers (x value)
        x_to_ys = defaultdict(list)
        for x, y in zip(handovers, durations):
            x_to_ys[x].append(y)
        x_vals_average = sorted(x_to_ys.keys())
        y_vals_average = [sum(x_to_ys[x]) / len(x_to_ys[x]) for x in x_vals_average]
        # Ensure equal lengths
        if len(durations) != len(handovers):
            print(f"Skipping line graph for {process_type} due to unequal lengths.")
            continue
        # Sort by handovers for the "normal" line
        sorted_pairs = sorted(zip(handovers, durations), key=lambda x: x[0])
        x_vals, y_vals = zip(*sorted_pairs) if sorted_pairs else ([], [])
        plt.figure(figsize=(8, 6))
        # Plot the "normal" line (blue)
        plt.plot(x_vals, y_vals, marker='o', linestyle='-', color='blue', label='Individual Cases')
        # Plot the average line (red)
        plt.plot(x_vals_average, y_vals_average, marker='o', linestyle='-', color='red', label='Average')
        plt.xlabel('Handovers')
        plt.ylabel('Case Duration (hours)')
        plt.title(f'Case Duration vs. Handovers for {process_type}')
        plt.legend()
        plt.tight_layout()
        line_path = os.path.join(OUTPUT_FOLDER, f'{process_type}_{postfix}.png')
        plt.savefig(line_path)
        plt.close()

def calculate_stats(list_counts, information_name=None):
    stats = []
    for process_type, numbers in list_counts.items():
        if numbers:
            try:
                mode_val = mode(numbers)
            except:
                mode_val = 'No unique mode'

            percentage = percentage_with_median_value(numbers)
            stats.append({
                'process_type': process_type,
                'mean': mean(numbers),
                'median': median(numbers),
                'mode': mode_val,
                'percentage_of_cases_with_median': percentage
            })
            if(information_name):
                # Create and save histogram for this process_type (integer bins)
                plt.figure(figsize=(8, 6))
                min_val, max_val = min(numbers), max(numbers)
                bins = range(int(min_val), int(max_val) + 2)  # +2 to include max value as right edge
                counts, bins, patches = plt.hist(numbers, bins=bins, color='skyblue', edgecolor='black', align='left', rwidth=0.8)
                plt.title(f'Histogram for {process_type}', pad=8)  # Reduce space above plot
                plt.xlabel('Value')
                plt.ylabel('Frequency')
                # Set x-ticks to a reasonable number for readability
                max_num_ticks = 15
                num_bins = len(bins) - 1
                if num_bins > max_num_ticks:
                    step = max(1, num_bins // max_num_ticks)
                    xticks = bins[:-1][::step]
                else:
                    xticks = bins[:-1]
                plt.xticks(xticks)
                # Annotate each bar with its frequency
                for count, bin_left, bin_right in zip(counts, bins[:-1], bins[1:]):
                    if count > 0:
                        plt.text(bin_left, count, f'{int(count)}', ha='center', va='bottom', fontsize=8)
                hist_path = os.path.join(OUTPUT_FOLDER, f'{process_type}_{information_name}_histogram.png')
                plt.savefig(hist_path)
                plt.close() 

    return stats

def get_top_10_from_csv(csv_path, sort_column, number_of_items, ascending=False):
    """
    Returns the top 10 rows from a CSV file sorted by the specified column.

    Args:
        csv_path (str): Path to the CSV file.
        sort_column (str): Column name to sort by.
        ascending (bool): Sort order. False for descending (default), True for ascending.

    Returns:
        pd.DataFrame: Top 10 rows sorted by the given column.
    """
    df = pd.read_csv(csv_path)
    if sort_column not in df.columns:
        raise ValueError(f"Column '{sort_column}' not found in CSV.")
    return df.sort_values(by=sort_column, ascending=ascending).head(number_of_items)

def calculate_worst_cases():
    csv_files = [f for f in os.listdir(OUTPUT_FOLDER) if f.endswith('.csv')]
    for csv_file in csv_files:
        csv_path = os.path.join(OUTPUT_FOLDER, csv_file)
        print(f"Top 10 from {csv_file}:")
        try:
            if 'combined' in csv_file:
                column_to_sort = 'duration'
            elif 'handovers' in csv_file:
                column_to_sort = 'between_handover_count'
            else:
                column_to_sort = 'case_duration_seconds'
            top_10_df = get_top_10_from_csv(csv_path, column_to_sort, 10)

            # Save the top 10 DataFrame to a new file in the "top_tens" folder
            top_tens_folder = os.path.join(OUTPUT_FOLDER, "top_tens")
            os.makedirs(top_tens_folder, exist_ok=True)
            top_10_path = os.path.join(top_tens_folder, f"top10_{csv_file}")
            top_10_df.to_csv(top_10_path, index=False)
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")

def combine_calculations_per_category(between_handovers_per_category, inside_handovers_per_category, duration_per_category):
    # For each process_type, combine the three dictionaries into a DataFrame per process_type
    print("Combining calculations per category...")
    for process_type in between_handovers_per_category:
        # Get the per-case dictionaries for this process_type
        between_handovers = between_handovers_per_category[process_type]
        inside_handovers = inside_handovers_per_category[process_type]
        durations = duration_per_category[process_type]

        # If the values are lists, convert to dicts with case_id as key (for backward compatibility)
        if isinstance(between_handovers, list):
            print(f"Converting lists to dicts for {process_type}...")
            # Try to load the corresponding CSVs to get case_ids
            handover_file = os.path.join(OUTPUT_FOLDER, f"{process_type}_handovers.csv")
            duration_file = os.path.join(OUTPUT_FOLDER, f"{process_type}_case_durations.csv")
            # Convert between_handovers and inside_handovers
            if os.path.exists(handover_file):
                df_handovers = pd.read_csv(handover_file)
                between_handovers = dict(zip(df_handovers['case_id'], df_handovers['between_handover_count']))
                inside_handovers = dict(zip(df_handovers['case_id'], df_handovers['inside_handover_count']))
            else:
                print(f"Missing handover file for {process_type}, skipping.")
                continue
            # Convert durations
            if os.path.exists(duration_file):
                df_durations = pd.read_csv(duration_file)
                duration_col = 'case_duration_seconds' if 'case_duration_seconds' in df_durations.columns else 'case_duration'
                durations = dict(zip(df_durations['case_id'], df_durations[duration_col]))
            else:
                print(f"Missing duration file for {process_type}, skipping.")
                continue

        # Combine by case_id
        case_ids = set(between_handovers.keys()) | set(inside_handovers.keys()) | set(durations.keys())
        rows = []
        print(f"Combining calculations for {process_type} with {len(case_ids)} case_ids...")
        for case_id in case_ids:
            rows.append({
                'case_id': case_id,
                'between_handovers': between_handovers.get(case_id, None),
                'inside_handovers': inside_handovers.get(case_id, None),
                'duration': durations.get(case_id, None)
            })
        df = pd.DataFrame(rows)
        output_path = os.path.join(OUTPUT_FOLDER, f'{process_type}_combined_calculations.csv')
        df.to_csv(output_path, index=False)
        print(f"Combined calculations for {process_type} saved to {output_path}")
    # output_path = os.path.join(OUTPUT_FOLDER, 'combined_calculations_per_category.csv')
    # df.to_csv(output_path, index=False)

def percentage_with_median_value(values):
    med = median(values)
    count_with_median = values.count(med)
    total = len(values)
    percentage = (count_with_median / total) * 100
    return round(percentage, 2)

if __name__ == "__main__":
    # Check if the required files exist in the OUTPUT_FOLDER

    duration_files = glob.glob(os.path.join(OUTPUT_FOLDER, '*_case_durations.csv'))
    handover_files = glob.glob(os.path.join(OUTPUT_FOLDER, '*_handovers.csv'))

    duration_per_category = {}
    inside_handovers_per_category = {}
    between_handovers_per_category = {}
    print(f"Duration files found: {duration_files}")
    print(f"Handover files found: {handover_files}")
    if duration_files and handover_files and not WHOLE_PROCESS:
        # Extract durations
        for file in duration_files:
            print(f"Processing duration file: {file}")
            process_type = os.path.basename(file).replace('_case_durations.csv', '')
            df = pd.read_csv(file)
            # Some files may have 'case_duration_seconds' or 'case_duration' as column
            duration_col = 'case_duration_seconds' if 'case_duration_seconds' in df.columns else 'case_duration'
            duration_per_category[process_type] = df[duration_col].tolist()
        # Extract handovers
        for file in handover_files:
            print(f"Processing handover file: {file}")
            process_type = os.path.basename(file).replace('_handovers.csv', '')
            df = pd.read_csv(file)
            between_handovers_per_category[process_type] = df['between_handover_count'].tolist()
            inside_handovers_per_category[process_type] = df['inside_handover_count'].tolist()

        calculate_statistics(between_handovers_per_category, inside_handovers_per_category, duration_per_category)
    else:
        print("No preprocessed files found, starting calculations...")
        duration_per_category, inside_handovers_per_category, between_handovers_per_category, duration_null_counts, one_activity_per_category  = calculations_per_category()
        calculate_statistics(between_handovers_per_category, inside_handovers_per_category, duration_per_category, duration_null_counts)

    print("Handover frequency calculation completed.")

    # combine_calculations_per_category(between_handovers_per_category, inside_handovers_per_category, duration_per_category)

    # calculate_worst_cases()

