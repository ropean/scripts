# Test Suite

This directory contains all test files for the scripts-collection project.

## Running Tests

```bash
# Run all tests
npm test

# Run specific test suites
npm run test:docs         # Documentation build tests
npm run test:features     # Features update script tests
```

## Test Files

### `docs.test.js`
Tests for documentation build output, ensuring:
- Correct routing and metadata
- Proper file structure in dist directory
- Valid sidebar and navigation configuration

### `update-features.test.js`
Tests for the update-features script, verifying:
- Category config loading
- YAML generation
- Correct sorting by order field
- Integration with actual categories

## Writing Tests

Tests use Node.js built-in test runner (`node:test`) with the following structure:

```javascript
const { describe, test } = require("node:test");
const assert = require("node:assert");

describe("Test Suite Name", () => {
  test("should do something", () => {
    assert.strictEqual(actual, expected);
  });
});
```

## Test Standards

- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Clean up any test artifacts
- Keep tests focused and independent
