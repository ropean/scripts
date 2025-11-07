#!/bin/bash
#
# @title Validate Script Metadata
# @description Verify that all scripts have proper @ tags
# @author Wei Guo
# @version 1.0.0
#
# This script validates that all git-change-*.sh scripts have
# the required metadata tags in the correct format.

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Script Metadata Validation ===${NC}\n"

# Required tags
REQUIRED_TAGS=(
    "title"
    "description"
    "author"
    "version"
    "license"
    "repository"
    "requires"
    "note"
    "example"
)

# Find all git-change scripts
SCRIPTS=(git-change-*.sh)

TOTAL_SCRIPTS=0
PASSED_SCRIPTS=0
FAILED_SCRIPTS=0

for script in "${SCRIPTS[@]}"; do
    if [ ! -f "$script" ]; then
        continue
    fi
    
    TOTAL_SCRIPTS=$((TOTAL_SCRIPTS + 1))
    echo -e "${BLUE}Checking: $script${NC}"
    
    MISSING_TAGS=()
    DUPLICATE_TAGS=()
    
    # Check each required tag
    for tag in "${REQUIRED_TAGS[@]}"; do
        COUNT=$(grep -c "^# @$tag" "$script" || true)
        
        if [ "$COUNT" -eq 0 ]; then
            MISSING_TAGS+=("$tag")
        elif [ "$COUNT" -gt 1 ]; then
            DUPLICATE_TAGS+=("$tag (found $COUNT times)")
        fi
    done
    
    # Report results
    if [ ${#MISSING_TAGS[@]} -eq 0 ] && [ ${#DUPLICATE_TAGS[@]} -eq 0 ]; then
        echo -e "  ${GREEN}✓ PASS${NC} - All required tags present and unique"
        PASSED_SCRIPTS=$((PASSED_SCRIPTS + 1))
    else
        echo -e "  ${RED}✗ FAIL${NC}"
        FAILED_SCRIPTS=$((FAILED_SCRIPTS + 1))
        
        if [ ${#MISSING_TAGS[@]} -gt 0 ]; then
            echo -e "  ${YELLOW}Missing tags:${NC}"
            for tag in "${MISSING_TAGS[@]}"; do
                echo "    - @$tag"
            done
        fi
        
        if [ ${#DUPLICATE_TAGS[@]} -gt 0 ]; then
            echo -e "  ${YELLOW}Duplicate tags:${NC}"
            for tag in "${DUPLICATE_TAGS[@]}"; do
                echo "    - @$tag"
            done
        fi
    fi
    
    echo ""
done

# Summary
echo -e "${BLUE}=== Summary ===${NC}"
echo "Total scripts: $TOTAL_SCRIPTS"
echo -e "${GREEN}Passed: $PASSED_SCRIPTS${NC}"
if [ $FAILED_SCRIPTS -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED_SCRIPTS${NC}"
fi

echo ""

if [ $FAILED_SCRIPTS -eq 0 ]; then
    echo -e "${GREEN}✓ All scripts have valid metadata!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some scripts have invalid metadata${NC}"
    exit 1
fi

