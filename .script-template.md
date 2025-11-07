---
title: 'Script Format Specification'
description: 'This document defines the standard format for all scripts in this repository.'
---

# Script Format Specification

This document defines the standard format for all scripts in this repository.

## File Header Format

All script files MUST include a standardized header comment block at the beginning.

### For JavaScript/Node.js (.js)

```javascript
/**
 * @title Script Title Here
 * @description Brief one-line description of what this script does
 * @author Your Name (optional)
 * @version 1.0.0 (optional)
 *
 * Detailed description can go here.
 * This section can span multiple lines and provide comprehensive
 * information about the script's purpose and functionality.
 *
 * @example
 * // Usage example
 * node script-name.js
 *
 * @requires dependency1, dependency2 (if any)
 * @see https://scripts.aceapp.dev (optional)
 */
```

### For Shell Scripts (.sh)

```bash
#!/bin/bash

# @title Script Title Here
# @description Brief one-line description of what this script does
# @author Your Name (optional)
# @version 1.0.0 (optional)
#
# Detailed description can go here.
# This section can span multiple lines and provide comprehensive
# information about the script's purpose and functionality.
#
# @example
# Usage example:
#   ./script-name.sh [options]
#
# @requires git, curl (if any)
# @see https://scripts.aceapp.dev (optional)
```

### For Python Scripts (.py)

```python
#!/usr/bin/env python3
"""
@title Script Title Here
@description Brief one-line description of what this script does
@author Your Name (optional)
@version 1.0.0 (optional)

Detailed description can go here.
This section can span multiple lines and provide comprehensive
information about the script's purpose and functionality.

@example
Usage example:
    python script-name.py [options]

@requires requests, pandas (if any)
@see https://scripts.aceapp.dev (optional)
"""
```

## Required Tags

- **@title**: Short, descriptive title (required)
- **@description**: One-line summary (required)

## Optional Tags

- **@author**: Author name(s)
- **@version**: Version number (semantic versioning recommended)
- **@example**: Usage examples
- **@requires**: Dependencies or prerequisites
- **@see**: Related documentation or resources
- **@note**: Important notes or warnings
- **@todo**: Pending improvements or features

## Directory Configuration

Each category directory SHOULD contain a `config.js` file:

```javascript
// config.js
module.exports = {
  title: 'Category Title',
  description: 'Brief description of this category',
  icon: '🎨', // Emoji icon for the category
  order: 1, // Display order (optional)
};
```

### Example: frontend/config.js

```javascript
module.exports = {
  title: 'Frontend Scripts',
  description: 'React components, vanilla JavaScript utilities, DOM manipulation, and modern UI patterns',
  icon: '🎨',
};
```

## File Naming Convention

- Use kebab-case for file names: `my-script-name.js`
- Be descriptive but concise
- Avoid special characters except hyphens
- Include appropriate file extension

## Code Style

### JavaScript

- Use ES6+ features
- Include JSDoc comments for functions
- Use meaningful variable names
- Follow consistent indentation (2 or 4 spaces)

```javascript
/**
 * Calculate the sum of two numbers
 * @param {number} a - First number
 * @param {number} b - Second number
 * @returns {number} Sum of a and b
 */
function add(a, b) {
  return a + b;
}
```

### Shell Scripts

- Use bash shebang: `#!/bin/bash`
- Include error handling
- Use meaningful variable names (UPPER_CASE for constants)
- Add comments for complex logic

```bash
#!/bin/bash

# Constants
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Error handling
set -euo pipefail
```

## Usage Instructions

Include clear usage instructions in the header or as inline comments:

```javascript
/**
 * USAGE:
 *
 * 1. Install dependencies:
 *    npm install dependency-name
 *
 * 2. Run the script:
 *    node script-name.js [options]
 *
 * 3. Options:
 *    --option1   Description of option1
 *    --option2   Description of option2
 */
```

## Template Files

### JavaScript Template

```javascript
/**
 * @title Script Name
 * @description What this script does in one line
 *
 * Detailed explanation of the script's purpose,
 * how it works, and when to use it.
 *
 * @example
 * node script-name.js
 *
 * @requires express, axios
 */

// Your code here
```

### Shell Script Template

```bash
#!/bin/bash

# @title Script Name
# @description What this script does in one line
#
# Detailed explanation of the script's purpose,
# how it works, and when to use it.
#
# @example
# ./script-name.sh
#
# @requires git, curl

set -euo pipefail

# Your code here
```

## Validation

The `generate-docs.js` script will:

1. Parse the header tags
2. Extract @title and @description
3. Generate documentation based on the metadata
4. Warn about missing required tags

## Migration Guide

For existing scripts without proper headers:

1. Add the required header block
2. Fill in @title and @description
3. Add @example if usage isn't obvious
4. List any dependencies in @requires
5. Run `npm run generate` to update docs

## Best Practices

1. **Keep headers concise** - Title should be < 60 characters
2. **Be descriptive** - Description should clearly explain the purpose
3. **Include examples** - Show typical usage scenarios
4. **Document dependencies** - List all prerequisites
5. **Update version** - Increment when making significant changes
6. **Add notes** - Highlight important information or caveats

## Examples

### Good Example

```javascript
/**
 * @title React Auto-Selector Utility
 * @description Automatically selects options in React Select dropdowns
 * @version 1.0.0
 *
 * This utility helps with testing and automation by automatically
 * selecting options in React Select components on a page.
 *
 * @example
 * // Run in browser console
 * autoSelectReactDropdowns();
 *
 * @requires React Select library on the page
 * @note This is designed for testing purposes only
 */

function autoSelectReactDropdowns() {
  // Implementation
}
```

### Bad Example (Avoid)

```javascript
// This script does some stuff with React

function doStuff() {
  // Code here
}
```

## Additional Resources

- [JSDoc Documentation](https://jsdoc.app/)
- [Bash Style Guide](https://google.github.io/styleguide/shellguide.html)
- [VitePress Markdown](https://vitepress.dev/guide/markdown)

---

**Last Updated**: 2025-01-06
**Applies To**: All scripts in this repository
