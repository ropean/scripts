#!/bin/bash

# @title Git LFS Config Generator
# @description Generates smart .gitattributes configuration for Git LFS based on file sizes
# @author ropean
# @version 1.0.0
# @date 2025-10-30
#
# SYNOPSIS
#     Generates a smart .gitattributes configuration for Git LFS based on file sizes in a repository.
#
# DESCRIPTION
#     This script scans a Git repository for large files and automatically generates appropriate Git LFS
#     configurations. It identifies file extensions of large files and creates corresponding entries in
#     the .gitattributes file. The script can either create a new configuration or append to an existing one.
#
# PARAMETERS
#     -r, --repo-path PATH     The path to the Git repository to scan. Defaults to current directory.
#     -s, --min-size SIZE      The minimum file size in megabytes to consider for Git LFS tracking. Defaults to 5MB.
#     -o, --output-file FILE   The name of the output .gitattributes file. Defaults to ".gitattributes".
#     -a, --append             If specified, appends new configurations to an existing .gitattributes file.
#     -h, --help               Display this help message.
#
# EXAMPLES
#     ./git-lfs-config-generator.sh
#     Scans the current directory for files larger than 5MB and creates a new .gitattributes file.
#
#     ./git-lfs-config-generator.sh -r /path/to/repo -s 10 -a
#     Scans /path/to/repo for files larger than 10MB and appends configurations to existing .gitattributes.
#
# NOTES
#     Author: Converted from PowerShell
#     Last Updated: 2025-10-30

# Default values
REPO_PATH="$(pwd)"
MIN_SIZE_MB=5
OUTPUT_FILE=".gitattributes"
APPEND_MODE=false

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Help function
show_help() {
	cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Generates a smart .gitattributes configuration for Git LFS based on file sizes.

OPTIONS:
    -r, --repo-path PATH     Repository path (default: current directory)
    -s, --min-size SIZE      Minimum file size in MB (default: 5)
    -o, --output-file FILE   Output file name (default: .gitattributes)
    -a, --append             Append to existing file
    -h, --help               Show this help message

EXAMPLES:
    $(basename "$0")
    $(basename "$0") -r /path/to/repo -s 10 -a
EOF
	exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
	case $1 in
	-r | --repo-path)
		REPO_PATH="$2"
		shift 2
		;;
	-s | --min-size)
		MIN_SIZE_MB="$2"
		shift 2
		;;
	-o | --output-file)
		OUTPUT_FILE="$2"
		shift 2
		;;
	-a | --append)
		APPEND_MODE=true
		shift
		;;
	-h | --help)
		show_help
		;;
	*)
		echo -e "${RED}Error: Unknown option $1${NC}"
		show_help
		;;
	esac
done

# If no repo path specified, ask user
if [[ "$REPO_PATH" == "$(pwd)" ]]; then
	echo -n "Enter repository path (press Enter to use current directory): "
	read -r user_input
	if [[ -n "$user_input" ]]; then
		REPO_PATH="$user_input"
	fi
fi

# Validate repository path
if [[ ! -d "$REPO_PATH" ]]; then
	echo -e "${RED}Error: Repository path does not exist: $REPO_PATH${NC}"
	exit 1
fi

if [[ ! -d "$REPO_PATH/.git" ]]; then
	echo -e "${YELLOW}Warning: The specified path may not be a Git repository (.git folder not found)${NC}"
	echo -n "Do you want to continue anyway? (Y/N): "
	read -r continue
	if [[ "$continue" != "Y" && "$continue" != "y" ]]; then
		exit 0
	fi
fi

# Initialize
MIN_SIZE_BYTES=$((MIN_SIZE_MB * 1024 * 1024))

# Change to repository directory
cd "$REPO_PATH" || exit 1

echo -e "${CYAN}=== Git LFS Configuration Generator ===${NC}"
echo -e "${YELLOW}Scanning for files larger than ${MIN_SIZE_MB}MB...${NC}"
echo ""

# Scan for large files and collect statistics
declare -A file_stats_count
declare -A file_stats_size

while IFS= read -r -d '' file; do
	# Skip .git directory
	if [[ "$file" == *"/.git/"* ]]; then
		continue
	fi

	file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)

	if [[ $file_size -gt $MIN_SIZE_BYTES ]]; then
		ext="${file##*.}"
		ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')

		if [[ -n "$ext" && "$ext" != "$file" ]]; then
			ext=".$ext"
			file_stats_count["$ext"]=$((${file_stats_count["$ext"]:-0} + 1))
			file_stats_size["$ext"]=$((${file_stats_size["$ext"]:-0} + file_size))
		fi
	fi
done < <(find . -type f -print0 2>/dev/null)

# Check if any large files were found
if [[ ${#file_stats_count[@]} -eq 0 ]]; then
	echo -e "${YELLOW}No files larger than ${MIN_SIZE_MB}MB found${NC}"
	exit 0
fi

# Display statistics
echo -e "${GREEN}Found the following large file types:${NC}"
echo ""
echo -e "${CYAN}Extension\tCount\tTotal Size${NC}"
echo "----------------------------------------"

for ext in $(printf '%s\n' "${!file_stats_count[@]}" | sort); do
	count=${file_stats_count["$ext"]}
	size_mb=$(echo "scale=2; ${file_stats_size["$ext"]} / 1048576" | bc)
	printf "%s\t\t%s\t\t%s MB\n" "$ext" "$count" "$size_mb"
done
echo ""

# Read existing configuration if append mode
declare -A existing_rules
output_path="$REPO_PATH/$OUTPUT_FILE"

if [[ "$APPEND_MODE" == true && -f "$output_path" ]]; then
	echo -e "${YELLOW}Detected existing configuration, merging...${NC}"

	while IFS= read -r line; do
		if [[ "$line" =~ ^\*(\.[a-zA-Z0-9]+)[[:space:]]+filter=lfs ]]; then
			ext="${BASH_REMATCH[1]}"
			existing_rules["$ext"]="$line"
		fi
	done <"$output_path"
fi

# Generate new rules
declare -A new_rules

for ext in "${!file_stats_count[@]}"; do
	count=${file_stats_count["$ext"]}
	size_mb=$(echo "scale=2; ${file_stats_size["$ext"]} / 1048576" | bc)
	rule="# $count files, ${size_mb}MB"$'\n'"*$ext filter=lfs diff=lfs merge=lfs -text"
	new_rules["$ext"]="$rule"
done

# Merge rules (new rules take precedence)
declare -A final_rules

for ext in "${!existing_rules[@]}"; do
	final_rules["$ext"]="${existing_rules["$ext"]}"
done

for ext in "${!new_rules[@]}"; do
	final_rules["$ext"]="${new_rules["$ext"]}"
done

# Generate final content
current_date=$(date "+%Y-%m-%d %H:%M:%S")
content="# Git LFS Configuration
# Generated: $current_date
# Scan criteria: File size > ${MIN_SIZE_MB}MB

"

# Add rules sorted by extension
for ext in $(printf '%s\n' "${!final_rules[@]}" | sort); do
	content+="${final_rules["$ext"]}"$'\n'
done

# Write to file
echo "$content" >"$output_path"

echo -e "${GREEN}✅ Configuration file generated: $output_path${NC}"

if [[ "$APPEND_MODE" == true && ${#existing_rules[@]} -gt 0 ]]; then
	new_count=0
	for ext in "${!new_rules[@]}"; do
		if [[ -z "${existing_rules["$ext"]}" ]]; then
			((new_count++))
		fi
	done
	echo -e "${CYAN}   Preserved ${#existing_rules[@]} existing rules${NC}"
	echo -e "${CYAN}   Added $new_count new rules${NC}"
fi

echo ""
echo -e "${YELLOW}File content preview:${NC}"
echo "----------------------------------------"
cat "$output_path"
echo "----------------------------------------"
