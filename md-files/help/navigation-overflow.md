---
title: "Navigation Menu Overflow Handling"
description: "How the navigation menu adapts when there are many categories"
---

# Navigation Menu Overflow Handling

## Automatic Menu Grouping

The documentation system automatically adjusts the navigation menu structure based on the number of categories:

### Flat Navigation (≤6 items)

When there are **6 or fewer** total categories, the navigation displays as a simple flat menu:

```
Home | Backend | Database | Frontend | Git | Node.js | Documentation
```

### Grouped Navigation (>6 items)

When there are **more than 6** categories, the navigation automatically switches to a grouped dropdown menu:

```
Home | Scripts ▼ | Documentation ▼
```

Where:

- **Scripts** dropdown contains all categories from `script-files/`
- **Documentation** dropdown contains all categories from `md-files/`

## Configuration

### Setting Menu Order

In your `.config.js` file, you can set the `order` property to control the position in the menu:

```javascript
module.exports = {
  title: "Category Name",
  description: "Category description",
  icon: "📚",
  order: 100, // Higher numbers appear later in the menu
};
```

### Default Ordering

- Script categories (from `script-files/`): `order: 0` (default)
- Documentation categories (from `md-files/`): `order: 999` (default)

## Benefits

1. **Scalability**: Handles any number of categories without cluttering the UI
2. **Automatic**: No manual configuration needed
3. **Clean UI**: Keeps the navigation bar clean and organized
4. **Semantic Grouping**: Naturally separates scripts from documentation

## Implementation

The menu structure is automatically determined in `scripts/generate-docs.js`:

```javascript
if (allNavItems.length <= 6) {
  // Flat navigation
} else {
  // Grouped navigation
}
```

This ensures the best user experience regardless of how many categories you add to your repository.
