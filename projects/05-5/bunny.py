import os
import argparse

# Set up parsing for command line arguments
parser = argparse.ArgumentParser(prog="bunny", description="Counts the number of times the word 'bunny' appears in a .txt file or a directory that contains .txt files")
parser.add_argument("file_dir", help="Path to folder where .txt could be located or a specific .txt file", type=str, default=None)

# Grab current working directory
cwd = os.getcwd()

def count_bunny_in_file(file_path) -> int:
    # Check if the file has a .txt extension
    if not file_path.endswith(".txt"):
        print(f"Error: File '{file_path}' does not have a .txt extension.")
        return 0
    
    # read the file and store its lines in a list
    with open(file_path, "r") as f:
        lines_unstripped = f.readlines()
        
    lines = []
    for line in lines_unstripped:
        # Strip ends of whitespace
        line = line.strip()
        # Remove comments
        if '#' in line:
            line = line.split('#')[0].strip()
        # Only add non-empty lines
        if line:
            lines.append(line)
            
    # Now iterate through the lines and count the occurence of the word "bunny"
    bunny_count = 0
    for line in lines:
        bunny_count += line.lower().count("bunny")
        
    return bunny_count

def count_bunny_in_directory(directory_path) -> int:
    # Iterate through the directory and grab all of the files that end in .txt
    files = []
    for file in os.listdir(directory_path):
        if file.endswith(".txt") and os.path.isfile(os.path.join(directory_path, file)):
            files.append(os.path.join(directory_path, file))

    # Now iterate through the files and count the occurrences of the word "bunny"
    bunny_count = 0
    for file in files:
        bunny_count += count_bunny_in_file(file)

    return bunny_count

if __name__ == "__main__":
    args = parser.parse_args()
    file_dir = args.file_dir
    
    if file_dir is None:
        print("Error: Please provide a path to a .txt file or a directory containing .txt files.")
        exit()
    
    if not os.path.isabs(file_dir):
        file_dir = os.path.join(cwd, file_dir)

    if os.path.isfile(file_dir):
        bunny_count = count_bunny_in_file(file_dir)
        
        print(f"The word 'bunny' appears {bunny_count} times in the .txt file '{file_dir}'")
        
        # Now save the result to the output file that is named the same as the input file but with a .out extension
        output_file = os.path.splitext(file_dir)[0] + ".out"
        
        with open(output_file, "w") as out_file:
            out_file.write(str(bunny_count))
        
    elif os.path.isdir(file_dir):
        bunny_count = count_bunny_in_directory(file_dir)
        
        print(f"The word 'bunny' appears {bunny_count} times in the .txt files located in the directory '{file_dir}'")
        
        # Now save the results to an output file named the same as the directory but with a .out extension inside the directory
        dir_name = os.path.basename(os.path.normpath(file_dir)) # strip out the final folder
        output_file = os.path.join(file_dir, dir_name + ".out") # Put the output file in the directory
        
        with open(output_file, "w") as out_file:
            out_file.write(str(bunny_count))
        
    else:
        print("Error: Invalid file or directory.")
        exit()