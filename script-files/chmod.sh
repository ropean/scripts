#!/usr/bin/env bash

# @title Chmod Script
# @description Recursively set execute permissions for all shell scripts in the current directory and subdirectories
# @author ropean
# @version 1.0.0
# @date 2025-11-10
#
# ==============================================================
# Chmod Script (English)
# --------------------------------------------------------------
#  • Recursively set execute permissions for all shell scripts in the current directory and subdirectories
# ==============================================================

find . -type f -name "*.sh" -exec chmod +x {} \;