/**
 * React Select Auto Selector
 *
 * Purpose:
 * Create all permits api token on cloudflare
 * Automatically selects options in all React Select dropdowns on the current page.
 * Priority: First tries to select options starting with "Edit", otherwise selects the last option.
 * This utility is particularly useful for testing, form automation, or quickly setting
 * multiple select fields to their desired option.
 *
 * How It Works:
 * 1. Finds all React Select control elements using the CSS class '.react-select__control'
 * 2. For each control, locates its input field and simulates keyboard interactions
 * 3. Opens the dropdown menu by sending an ArrowDown key event
 * 4. Scans all available options to find one starting with "Edit" (case-insensitive)
 * 5. If an "Edit" option is found, navigates to it and selects it
 * 6. If no "Edit" option exists, jumps to the last option using the End key and selects it
 * 7. Includes appropriate delays between actions to ensure UI updates complete
 *
 * Applicable Scope:
 * - Works with react-select library (https://react-select.com/)
 * - Compatible with standard React Select implementations using default class names
 * - Requires '.react-select__control' and '.react-select__option' CSS classes to be present
 * - May need adjustment for heavily customized React Select components with modified class names
 *
 * Usage:
 * Simply load this script in the browser console and it will execute automatically:
 *
 * Method 1 - Copy and paste:
 *   Copy the entire file content and paste into the browser console, then press Enter
 *
 * Method 2 - Load from file/URL:
 *   const script = document.createElement('script');
 *   script.src = 'path/to/react-select-auto-selector.js';
 *   document.head.appendChild(script);
 *
 * Limitations:
 * - Only works on pages that have already rendered React Select components
 * - May not work with virtual scrolling or lazy-loaded options
 * - Timing delays are configured for typical scenarios; very slow pages may need adjustment
 *
 * @version 1.1.0
 * @author Ropean
 * @license MIT
 */

(async () => {
  console.log('🚀 React Select Auto Selector - Starting...');

  // Find all React Select control elements
  const controls = document.querySelectorAll('.react-select__control');

  if (controls.length === 0) {
    console.warn('⚠️ No React Select controls found on this page.');
    return;
  }

  console.log(`📋 Found ${controls.length} React Select control(s)`);

  /**
   * Simulates keyboard events on a target element
   * @param {HTMLElement} el - The target element
   * @param {string} key - The key name (e.g., 'Enter', 'ArrowDown')
   * @param {number} keyCode - The legacy keyCode value
   */
  const sendKey = (el, key, keyCode) => {
    ['keydown', 'keyup'].forEach((type) => {
      const evt = new KeyboardEvent(type, {
        key,
        bubbles: true,
        cancelable: true,
      });

      // Set legacy properties for compatibility
      Object.defineProperty(evt, 'keyCode', { get: () => keyCode });
      Object.defineProperty(evt, 'which', { get: () => keyCode });
      Object.defineProperty(evt, 'code', { get: () => key });

      el.dispatchEvent(evt);
    });
  };

  // Process each React Select control
  for (let i = 0; i < controls.length; i++) {
    const control = controls[i];
    const input = control.querySelector('input');

    if (!input) {
      console.warn(`⚠️ Control ${i + 1}: No input field found, skipping...`);
      continue;
    }

    console.log(`🔄 Processing control ${i + 1}/${controls.length}...`);

    // Focus the input field
    input.focus();
    await new Promise((r) => setTimeout(r, 200));

    // Open the dropdown menu
    sendKey(input, 'ArrowDown', 40);
    await new Promise((r) => setTimeout(r, 300));

    // Get all available options
    const options = document.querySelectorAll('.react-select__option, [class*="react-select"][class*="option"]');
    const optionCount = options.length;

    if (optionCount === 0) {
      console.warn(`   └─ ⚠️ No options found in dropdown`);
      continue;
    }

    console.log(`   ├─ Found ${optionCount} option(s) in dropdown`);

    // Look for an option starting with "Edit"
    let editOptionFound = false;
    let editOptionIndex = -1;

    for (let j = 0; j < options.length; j++) {
      const optionText = options[j].textContent.trim();
      if (optionText.toLowerCase().startsWith('edit')) {
        editOptionFound = true;
        editOptionIndex = j;
        console.log(`   ├─ Found "Edit" option at position ${j + 1}: "${optionText}"`);
        break;
      }
    }

    if (editOptionFound) {
      // Navigate to the Edit option
      // First go to the beginning
      sendKey(input, 'Home', 36);
      await new Promise((r) => setTimeout(r, 100));

      // Then press ArrowDown to reach the target option
      for (let k = 0; k < editOptionIndex; k++) {
        sendKey(input, 'ArrowDown', 40);
        await new Promise((r) => setTimeout(r, 50));
      }

      // Select the Edit option
      sendKey(input, 'Enter', 13);
      await new Promise((r) => setTimeout(r, 200));

      console.log(`   └─ ✓ Selected "Edit" option`);
    } else {
      // No Edit option found, select the last option
      console.log(`   ├─ No "Edit" option found, selecting last option`);

      // Jump to the last option using End key
      sendKey(input, 'End', 35);
      await new Promise((r) => setTimeout(r, 100));

      // Select the last option
      sendKey(input, 'Enter', 13);
      await new Promise((r) => setTimeout(r, 200));

      console.log(`   └─ ✓ Selected last option`);
    }
  }

  console.log('✅ All React Select controls have been processed');
})();
