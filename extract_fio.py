import sqlite3
import json
import csv
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import math
import seaborn as sns
import adjustText

# Connect to the sqlite database
connection = sqlite3.connect('fio.db')
cursor = connection.cursor()

# Arrays to store rows and columns for dataframe from json database
headers = [] # stores keys
vals = [] # stores dictionaries (keys and values)

# General (non-job) values to extract
targets = ['fio version', 'timestamp']

# Method to extract target values from nested JSON
def extract(data, targets, saved):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                extract(value, targets, saved)
            elif key in targets:
                saved[key] = value
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                extract(item, targets, saved)

# Methods to extract job values from nested JSON
def helper(list, job_name, saved, job_type):
    clat_ns = list.get('clat_ns')
    if 'percentile' in clat_ns:
        log_percentiles = {100 - float(k): v for k, v in clat_ns['percentile'].items()} # taking the 1 - p probability
        iops = list.get('iops')
        return {**saved, 'job_name': f'{job_name}', 'job_type': job_type, 'iops': iops, **log_percentiles} # final dictionary entry for vals
    # If percentile is not present i.e. IOPS = 0
    file_name = saved['filename']
    print(f'{file_name} - {job_name} - {job_type} has no percentile (iops = 0)')
    return {} # returns empty dictionary

def extract_job(data, vals, saved):
    if isinstance(data, dict):
        for key, value in data.items():
            if key == 'jobs' and isinstance(value, list):
                for job in value:
                    if isinstance(job, dict):
                        job_name = job.get('jobname')
                        read = job.get('read')
                        write = job.get('write')
                        trim = job.get('trim')
                        vals.append(helper(read, job_name, saved, 'read'))
                        vals.append(helper(write, job_name, saved, 'write'))
                        vals.append(helper(trim, job_name, saved, 'trim'))
    vals[:] = list(filter(None, vals)) # filters out the empty dictionaries in vals array

# Main method to extract from db and store into arrays (calls the other methods)
def export_db(query):
    data = cursor.execute(query)
    for row in data:
        saved = {} # temp dictionary to hold target values to be added to vals array
        for i in range(len(row)- 1):
            saved[data.description[i][0]] = row[i] # value i matches the column name to value from db
        content = json.loads(row[-1]) # fio file content is last column in db
        extract(content, targets, saved)
        extract_job(content, vals, saved)
    headers.extend(list(vals[0].keys())) # extracting keys from first array entry since all entrys have same key

# Parser values
parser = argparse.ArgumentParser(description = 'Export sqlite3 table in JSON form into csv file')
parser.add_argument('-f', '--file_name', help='Name for csv file')
parser.add_argument('-q', '--query', help='Query select statement')
args = parser.parse_args()

if not all(vars(args).values()):
    parser.print_help()
    exit(1)

# Calling main method
export_db(args.query)

# Saving extracted values into a csv file
with open(args.file_name, 'w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames = headers)
    writer.writeheader()
    writer.writerows(vals)

connection.close()

# Creating dataframe from array of dictionaries using 'from_record' for graphing
df = pd.DataFrame.from_records(vals)

# Get the unique drive_model values
unique_drive_models = df['drive_model'].unique()

# Generate a color map using Seaborn's color_palette
num_drive_models = len(unique_drive_models)
colors = sns.color_palette("hls", num_drive_models)

# Create a color mapping for drive_model values
drive_model_colors = {model: color for model, color in zip(unique_drive_models, colors)}

# Iterating through to create a line graph for each job type
for job_type in df['job_type'].unique():
    fig, ax = plt.subplots()
    df_filtered = df[df['job_type'] == job_type]
    y_vals = df.columns[-17:] # percentiles are the last 17 columns added to df
    colors_for_filename = df_filtered['drive_model'].map(drive_model_colors)
    for idx, row in df_filtered.iterrows():
        x_vals = row.iloc[-17:].values
        color = colors_for_filename[idx]
        job_name = row['job_name']
        file_name = row['filename']
        line_label = f'{file_name} - {job_name}'
        ax.plot(x_vals, y_vals, color=color)
        # Add the job_name label at the end of the line
        text = ax.annotate(job_name, xy=(x_vals[-1], y_vals[-1]), xytext=(5, 0), textcoords='offset points',
                color=color, ha='left', va='center')

    # Set plot title and axis labels
    ax.set_xlabel('Value')
    ax.set_ylabel('Log Percentage')
    ax.set_title('Completion Latency (ns)')

    # Setting the log scale on the y axis
    plt.yscale("log")

    # Creating legend based on drive model color
    legend_elements = [plt.Line2D([0], [0], marker='o', color='w', label=model, markerfacecolor=color, markersize=10)
                       for model, color in drive_model_colors.items()]
    ax.legend(handles=legend_elements, loc = 'center left', bbox_to_anchor=(1, 0.5))

    # Adjust the line labels so there is no overlapping
    adjustText.adjust_text(ax.texts, only_move={'points':'y', 'texts':'y'})

    # Save the plot as an image
    plt.savefig(f'test_{job_type}.png', bbox_inches='tight')

# Create a unique bar plot for each job_type
for job_type in df['job_type'].unique():
    fig, ax = plt.subplots()

    # Filter the DataFrame for a specific job_type
    df_filtered = df[df['job_type'] == job_type].copy()

    # Create the 'color' column in the 'df_filtered' DataFrame by mapping the 'drive_model' values
    df_filtered['color'] = df_filtered['drive_model'].map(drive_model_colors)
    # Create the bar plot with color coding based on 'color' column
    df_filtered.plot(x="job_name", y="iops", kind="bar", color=df_filtered['color'], ax=ax)

    # Set plot title and axis labels
    plt.title(f"IOPS - {job_type}")
    plt.xlabel("Job name")
    plt.ylabel("IOPS")

    # Create custom legend
    legend_elements = [plt.Line2D([0], [0], marker='o', color='w', label=model, markerfacecolor=color, markersize=10)
                       for model, color in drive_model_colors.items()]
    # Add the custom legend to the plot
    ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1, 0.5))

    # Save the plot as an image
    plt.savefig(f'test_{job_type}_bar.png', bbox_inches='tight')
