import sqlite3
import argparse
import json

# Connect to the sqlite database
connection = sqlite3.connect('fio.db')
cursor = connection.cursor()

#Function to insert JSON file data into database
def insert_json(filename, drive_model, capacity, compression_ratio, path_to_file):

    with open(path_to_file, 'r') as file:
        json_content = file.read()

    #Pulling additional column data from JSON file
    json_data = json.loads(json_content)

    time = json_data['time']

    #Executing entry into database
    insert_query = """
        INSERT INTO json_files (filename, drive_model, capacity, compression_ratio, time, content)
        VALUES (?, ?, ?, ?, ?, ?)
    """

    cursor.execute(insert_query, (filename, drive_model, capacity, compression_ratio, time, json_content))

    connection.commit()

#Parser Arguments for manual column data
parser = argparse.ArgumentParser(description='Insert JSON data into SQLite database.')
parser.add_argument('-f', '--filename', help='Filename')
parser.add_argument('-m', '--drive_model', help='Drive model')
parser.add_argument('-c', '--capacity', help='Capacity (value only in GB)')
parser.add_argument('-r', '--compression_ratio', help='Compression ratio (value only)')
parser.add_argument('-p', '--path_to_file', help='Path to the JSON file')

args = parser.parse_args()

if not all(vars(args).values()):
    parser.print_help()
    exit(1)

#Calling insert method
insert_json(args.filename, args.drive_model, args.capacity, args.compression_ratio, args.path_to_file)

connection.close()
