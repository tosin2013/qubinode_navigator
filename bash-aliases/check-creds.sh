#!/bin/bash

# =============================================================================
# YAML Credential Checker - The "Configuration Diff Analyzer"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script compares and updates YAML configuration files, specifically designed
# for credential and configuration management. It identifies differences between
# YAML files and safely updates target files with new or changed values.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements YAML file comparison and updating:
# 1. [PHASE 1]: Input Validation - Validates command-line arguments and file existence
# 2. [PHASE 2]: YAML Comparison - Uses yq to identify differences between files
# 3. [PHASE 3]: Backup Creation - Creates backup of target file before modification
# 4. [PHASE 4]: Selective Update - Merges only changed values into target file
# 5. [PHASE 5]: Verification - Reports changes and confirms successful update
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Configuration Management]: Updates inventory YAML files with new credentials
# - [Credential Safety]: Provides safe method for credential file updates
# - [Backup Protection]: Creates backups before making changes
# - [Diff Analysis]: Shows exactly what changes are being made
# - [Automation Support]: Can be used in automated configuration workflows
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Safety-First]: Creates backups before making any changes
# - [Selective Updates]: Only updates changed or new values
# - [Transparency]: Shows exactly what changes are being made
# - [Error-Resilient]: Validates inputs and handles errors gracefully
# - [Tool-Dependent]: Requires yq for YAML processing
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [YAML Processing]: Update for new yq versions or syntax changes
# - [Backup Strategy]: Enhance backup naming or retention policies
# - [Diff Reporting]: Improve change reporting and visualization
# - [Error Handling]: Add more robust error handling and recovery
# - [Integration Features]: Add support for different YAML structures or formats
#
# 🚨 IMPORTANT FOR LLMs: This script modifies YAML configuration files that may
# contain sensitive credentials. It requires yq tool and creates backup files.
# Changes affect configuration state and credential management.

# Exit immediately if a command exits with a non-zero status
set -e

# Usage Display Function - The "Help Guide"
usage() {
# 🎯 FOR LLMs: Provides clear usage instructions for the script
    echo "Usage: $0 <file1_yaml> <file2_yaml>"
    echo "  <file1_yaml> : Path to the first YAML file to be updated."
    echo "  <file2_yaml> : Path to the second YAML file containing updates."
    exit 1
}

# Input Validation - The "Argument Validator"
# 🎯 FOR LLMs: Validates command-line arguments before processing
if [[ $# -ne 2 ]]; then
    echo "Error: Incorrect number of arguments."
    usage
fi

# 📊 INPUTS/OUTPUTS:
# Assign command-line arguments to variables for processing
file1_yaml="$1"  # Target file to be updated
file2_yaml="$2"  # Source file containing updates

# YAML Difference Analyzer - The "Configuration Detective"
compare_yaml() {
# 🎯 FOR LLMs: This function compares two YAML files and identifies differences,
# returning only the keys and values that are different or new in the second file.
# 🔄 WORKFLOW:
# 1. Uses yq to load both YAML files with file indices
# 2. Merges the new file over the base file
# 3. Compares the result with the original base file
# 4. Returns only the differences
# 📊 INPUTS/OUTPUTS:
# - INPUT: Two YAML file paths
# - OUTPUT: YAML content showing only differences
# ⚠️  SIDE EFFECTS: Requires yq tool, reads file contents

    local file1="$1"  # Base file for comparison
    local file2="$2"  # New file with potential updates

    # Use yq to compute differences by identifying keys in file2 that are different or new compared to file1
    yq eval-all '
        select(fileIndex == 0) as $base |
        select(fileIndex == 1) as $new |
        $new * $base | select(. != $base)
    ' "$file1" "$file2"
}

# YAML Update Manager - The "Safe Configuration Updater"
update_yaml() {
# 🎯 FOR LLMs: This function safely updates a YAML file with changes from another
# YAML file, creating a backup before making any modifications.
# 🔄 WORKFLOW:
# 1. Creates backup copy of target file with .backup extension
# 2. Uses yq to merge source file into target file
# 3. Updates target file in-place with merged content
# 📊 INPUTS/OUTPUTS:
# - INPUT: Target file path and source file path
# - OUTPUT: Updated target file and backup file
# ⚠️  SIDE EFFECTS: Modifies target file, creates backup file, requires yq tool

    local file1="$1"  # Target file to be updated
    local file2="$2"  # Source file containing updates

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
