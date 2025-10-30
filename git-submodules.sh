#!/usr/bin/env bash
# auther: ropean
# date: 2025-10-30

# ==============================================================
# Git Submodules Management Script (English)
# --------------------------------------------------------------
#  • Configurable GitHub user name
#  • Bulk repo creation with single visibility choice
#  • Optional .gitmodules update
#  • Init / Push / Pull / Run-in-all with clear feedback
# ==============================================================

# --------------------- CONFIGURATION ---------------------
GITHUB_USER="ropean" # <<<--- CHANGE THIS
SUBMODULES_DIR="apps"  # Submodule root (change if needed)
GITMODULES_FILE=".gitmodules"
# ---------------------------------------------------------

# --------------------- COLOUR & EMOJI --------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m' # No colour
INFO="ℹ️  "
SUCCESS="✅ "
WARN="⚠️  "
ERR="❌  "
RUN="🔧  "

# --------------------- PRINT HELPERS --------------------
p_header() { echo -e "${PURPLE}=======================================${NC}"; }
p_title() { echo -e "${CYAN}   Git Submodules Manager${NC}"; }
p_success() { echo -e "${SUCCESS}${GREEN}$1${NC}"; }
p_error() { echo -e "${ERR}${RED}$1${NC}"; }
p_warn() { echo -e "${WARN}${YELLOW}$1${NC}"; }
p_info() { echo -e "${INFO}${BLUE}$1${NC}"; }
p_dim() { echo -e "${INFO}${DIM}$1${NC}"; }
p_run() { echo -e "${RUN}${CYAN}$1${NC}"; }

# --------------------- UTILS --------------------
# List submodules with numbers
list_submodules() {
	find "$SUBMODULES_DIR" -mindepth 1 -maxdepth 1 -type d | sort | nl -w2 -s') '
}
# Return array of submodule names only
submodule_names() {
	find "$SUBMODULES_DIR" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort
}

# --------------------- GH CLI CHECK --------------------
check_gh() {
	if ! command -v gh &>/dev/null; then
		p_error "GitHub CLI (gh) is not installed!"
		echo "    Install from: https://cli.github.com"
		return 1
	fi
	return 0
}

# --------------------- CHECK & UPDATE SUBMODULES_DIR --------------------
check_and_update_submodules_dir() {
	if [[ -d "$SUBMODULES_DIR" ]]; then
		return 0
	fi

	p_warn "Directory '$SUBMODULES_DIR' does not exist!"
	echo -n "Enter the submodules directory path: "
	read -r new_dir

	# Trim whitespace
	new_dir=$(echo "$new_dir" | xargs)

	if [[ -z "$new_dir" ]]; then
		p_error "Directory path cannot be empty"
		return 1
	fi

	if [[ ! -d "$new_dir" ]]; then
		echo -n "Directory '$new_dir' doesn't exist. Create it? [y/N]: "
		read -r create_choice
		case "$create_choice" in
		y | Y)
			if mkdir -p "$new_dir"; then
				p_success "Created directory: $new_dir"
			else
				p_error "Failed to create directory: $new_dir"
				return 1
			fi
			;;
		*)
			p_error "Operation cancelled"
			return 1
			;;
		esac
	fi

	# Update the script itself
	local script_path="${BASH_SOURCE[0]}"
	if [[ -w "$script_path" ]]; then
		p_info "Updating SUBMODULES_DIR in script..."
		if sed -i.bak "s|^SUBMODULES_DIR=\".*\"|SUBMODULES_DIR=\"$new_dir\"|" "$script_path"; then
			p_success "Script updated! SUBMODULES_DIR is now: $new_dir"
			# Update the current session variable
			SUBMODULES_DIR="$new_dir"
			rm -f "${script_path}.bak"
		else
			p_error "Failed to update script"
			return 1
		fi
	else
		p_warn "Cannot write to script file. Using '$new_dir' for this session only."
		SUBMODULES_DIR="$new_dir"
	fi

	return 0
}

# --------------------- OPTIONAL .gitmodules UPDATE --------------------
update_gitmodules() {
	p_info "Upserting missing entries into $GITMODULES_FILE..."
	# Ensure file exists
	touch "$GITMODULES_FILE"

	local count=0
	while IFS= read -r dir; do
		local name
		name=$(basename "$dir")
		local path="$SUBMODULES_DIR/$name"
		local url="git@github.com:$GITHUB_USER/$name.git"

		if grep -q "path = $path" "$GITMODULES_FILE" 2>/dev/null; then
			p_dim "Entry for $path already exists in $GITMODULES_FILE — skipping"
			continue
		fi

		cat >>"$GITMODULES_FILE" <<EOF
[submodule "$path"]
	path = $path
	url = $url
EOF
		((count++))
	done < <(find "$SUBMODULES_DIR" -mindepth 1 -maxdepth 1 -type d)

	if ((count > 0)); then
		git add "$GITMODULES_FILE" &>/dev/null || true
		p_success "Appended $count missing submodule(s) to $GITMODULES_FILE."
	else
		p_success "No new submodules."
	fi
}

# --------------------- 1. INITIALIZE ALL SUBMODULES --------------------
init_all_submodules() {
	p_info "Initializing all submodules in $SUBMODULES_DIR (git init only)..."
	local total=0 failed=()
	while IFS= read -r dir; do
		((total++))
		local name
		name=$(basename "$dir")
		if (cd "$dir" && git rev-parse --is-inside-work-tree &>/dev/null); then
			p_dim "[$name] already a git repo — skipping"
			continue
		fi
		if (cd "$dir" && git init -q); then
			p_success "Initialized $name"
		else
			failed+=("$name")
			p_error "Failed to init $name"
		fi
	done < <(find "$SUBMODULES_DIR" -mindepth 1 -maxdepth 1 -type d)

	echo
	p_success "Initialized $((total - ${#failed[@]})) / $total submodules."
	((${#failed[@]})) && p_error "Failed: ${failed[*]}"
}

# --------------------- 2. CREATE GITHUB REPOS (bulk) --------------------
create_github_repos() {
	check_gh || return 1

	# === 1. Get submodule names ===
	local names
	mapfile -t names < <(submodule_names)
	((${#names[@]} == 0)) && {
		p_error "No submodules found in $SUBMODULES_DIR"
		return 1
	}

	# === 2. Set visibility uniformly (ask only once) ===
	local VIS="private"
	echo -n "Repository visibility [P]rivate / [p]ublic (default private): "
	read -r vis_input
	case "$vis_input" in
	p | P | public | Public) VIS="public" ;;
	*) VIS="private" ;;
	esac

	# === 3. Fetch all user repositories at once (max 1000, sufficient) ===
	p_info "Fetching existing repositories for '$GITHUB_USER'..."
	local existing_raw
	if ! existing_raw=$(gh repo list "$GITHUB_USER" --limit 1000 --json name -q '.[].name' 2>/dev/null); then
		p_error "Failed to fetch repository list. Is 'gh' authenticated?"
		return 1
	fi

	# Build existence map
	declare -A exists_map
	while IFS= read -r repo_name; do
		[[ -n "$repo_name" ]] && exists_map["$repo_name"]=1
	done <<<"$existing_raw"

	# === 4. Filter out repositories that need to be created ===
	local to_create=()
	for name in "${names[@]}"; do
		if [[ -z "${exists_map[$name]}" ]]; then
			to_create+=("$name")
		else
			p_dim "Repo '$name' already exists — skipping"
		fi
	done

	((${#to_create[@]} == 0)) && {
		p_success "All ${#names[@]} repositories already exist."
		return 0
	}

	# === 5. Batch create and push ===
	p_info "Creating ${#to_create[@]} new $VIS repositories..."
	local created=0 failed=()

	for repo in "${to_create[@]}"; do
		local dir="$SUBMODULES_DIR/$repo"
		[[ ! -d "$dir" ]] && {
			p_error "Directory missing: $dir"
			failed+=("$repo")
			continue
		}

		printf "${YELLOW}→ Creating %s ($VIS)${NC}\n" "$repo"
		if gh repo create "$repo" \
			--$VIS \
			--source="$dir" \
			--remote=origin \
			--description "Submodule: $repo"; then

			p_success "$repo created"
			((created++))
		else
			p_error "$repo creation failed"
			failed+=("$repo")
		fi
	done

	# === 6. Final statistics ===
	echo
	p_success "Created $created out of ${#to_create[@]} repositories."
	((${#failed[@]})) && p_error "Failed: ${failed[*]}"
}

# --------------------- 5. RUN COMMAND IN ALL --------------------
run_in_all() {
	echo -n "Enter command to run in every submodule: "
	read -r cmd
	[[ -z "$cmd" ]] && {
		p_error "Command cannot be empty"
		return 1
	}

	p_run "$cmd"
	local total=0 ok=0 fail=() args
	while IFS= read -r dir; do
		((total++))
		name=$(basename "$dir")
		echo -e "\n${YELLOW}[$name] $cmd${NC}"
		if (cd "$dir" &&
			eval "args=($cmd)" &&
			[ ${#args[@]} -gt 0 ] &&
			"${args[@]}" >/dev/null 2>&1); then
			((ok++))
			p_success "$name"
		else
			fail+=("$name")
			p_error "$name"
		fi
	done < <(find "$SUBMODULES_DIR" -mindepth 1 -maxdepth 1 -type d)

	echo
	p_success "Executed on $ok / $total submodules."
	((${#fail[@]})) && p_error "Failed: ${fail[*]}"
}

# --------------------- 6. HELP --------------------
show_help() {
	cat <<'EOF'

Common Git Submodule Commands
-----------------------------
git submodule add <url> <path>          Add a submodule
git submodule init                      Initialise .gitmodules
git submodule update                    Checkout submodules
git submodule update --remote           Pull latest remote
git submodule foreach <cmd>             Run <cmd> in every submodule
git submodule status                    Show status
git rm --cached <path>                  Remove submodule (keep folder)

Full docs: https://git-scm.com/book/en/v2/Git-Tools-Submodules
EOF
}

fix_git_remote() {
	[[ -z "$GITHUB_USER" ]] && {
		p_error "GITHUB_USER is not set"
		return 1
	}

	local total=0 ok=0 fail=() name url current_origin

	while IFS= read -r dir; do
		((total++))
		name=$(basename "$dir")
		url="https://github.com/$GITHUB_USER/$name.git"

		p_run "[$name] Fixing remote origin -> $url${NC}"

		if ! current_origin=$(cd "$dir" && git remote get-url origin 2>/dev/null); then
			# No origin exists → add it
			if (cd "$dir" && git remote add origin "$url" >/dev/null 2>&1); then
				((ok++))
				p_success "$name (added origin)"
			else
				fail+=("$name")
				p_error "$name (failed to add origin)"
			fi
		elif [[ "$current_origin" != "$url" ]]; then
			# Origin exists but wrong URL → set-url
			if (cd "$dir" && git remote set-url origin "$url" >/dev/null 2>&1); then
				((ok++))
				p_success "$name (updated origin)"
			else
				fail+=("$name")
				p_error "$name (failed to set-url)"
			fi
		else
			# Origin already correct
			((ok++))
			p_dim "$name (origin already correct)"
		fi
	done < <(find "$SUBMODULES_DIR" -mindepth 1 -maxdepth 1 -type d)

	echo
	p_success "Fixed remote on $ok / $total submodules."
	((${#fail[@]})) && p_error "Failed: ${fail[*]}"
}

# --------------------- MAIN MENU --------------------
main_menu() {
	# Check if SUBMODULES_DIR exists before showing menu
	check_and_update_submodules_dir || exit 1

	while true; do
		clear
		p_header
		p_title
		p_header
		echo -e "${DIM}Current submodules directory: ${CYAN}$SUBMODULES_DIR${NC}"
		p_header
		echo "1) Upsert .gitmodules"
		echo "2) Create GitHub repos"
		echo "3) Run command in ALL submodules"
		echo "4) Show submodule commands"
		echo "5) Git init all submodules"
		echo "6) Git pull all submodules"
		echo "7) Fix git remote for all submodules"
		echo "0) Exit"
		echo -e "${PURPLE}----------------------------------------${NC}"
		echo -n "Choose [0-7]: "
		read -r opt

		case "$opt" in
		1) update_gitmodules ;;
		2) create_github_repos ;;
		3) run_in_all ;;
		4) show_help ;;
		5) run_in_all "git init" ;;
		6) run_in_all "git pull" ;;
		7) fix_git_remote ;;
		0)
			echo -e "${SUCCESS}Goodbye!${NC}"
			exit 0
			;;
		*) p_error "Invalid option — try again" ;;
		esac

		echo -e "\n${YELLOW}Press ENTER to continue…${NC}"
		read -r
	done
}

# --------------------- START --------------------
main_menu
