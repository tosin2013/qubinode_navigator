#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Function to display usage instructions
usage() {
    echo "Usage: $0 <file1_yaml> <file2_yaml>"
    echo "  <file1_yaml> : Path to the first YAML file to be updated."
    echo "  <file2_yaml> : Path to the second YAML file containing updates."
    exit 1
}

# Check if exactly two arguments are provided
if [[ $# -ne 2 ]]; then
    echo "Error: Incorrect number of arguments."
    usage
fi

# Assign command-line arguments to variables
file1_yaml="$1"
file2_yaml="$2"

# Function to compare two YAML files and return differences
compare_yaml() {
    local file1="$1"
    local file2="$2"

    # Use yq to compute differences by identifying keys in file2 that are different or new compared to file1
    yq eval-all '
        select(fileIndex == 0) as $base |
        select(fileIndex == 1) as $new |
        $new * $base | select(. != $base)
    ' "$file1" "$file2"
}

# Function to update file1 with differences from file2
update_yaml() {
    local file1="$1"
    local file2="$2"

    # Create a backup before making changes
    cp "$file1" "${file1}.backup"

    # Merge file2 into file1 and update file1 in-place
    yq eval-all '
        select(fileIndex == 0) * select(fileIndex == 1)
    ' "$file1" "$file2" -i
}

# Main script execution starts here

# Check if both files exist
if [[ ! -f "$file1_yaml" ]]; then
    echo "Error: File1 does not exist at path: $file1_yaml"
    exit 1
fi

if [[ ! -f "$file2_yaml" ]]; then
    echo "Error: File2 does not exist at path: $file2_yaml"
    exit 1
fi

# Compare the YAML files and get the differences
diff_output=$(compare_yaml "$file1_yaml" "$file2_yaml")

# Check if there are any differences
if [[ -z "$diff_output" || "$diff_output" == "null" ]]; then
    echo "No differences found. No updates needed."
else
    echo "Differences found. Updating $file1_yaml with the following changes:"
    echo "$diff_output"

    # Update file1 with differences from file2
    update_yaml "$file1_yaml" "$file2_yaml"

    echo "Successfully updated $file1_yaml with differences from $file2_yaml."
    echo "A backup of the original file has been created at ${file1_yaml}.backup"
fi
