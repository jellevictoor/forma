---
description: Comprehensive mobile responsiveness testing - scrolling, screenshots at all breakpoints, touch targets, and visual verification
---

# Mobile Responsive Testing Skill

Use this skill to perform thorough mobile responsiveness testing including scrolling through entire pages, capturing screenshots at multiple breakpoints, and verifying touch interactions.

## When to Use
- After implementing UI features
- After fixing responsive layout bugs
- Before deploying frontend changes
- During comprehensive QA validation
- When user reports mobile issues

## What This Skill Does

### 1. Multi-Breakpoint Testing
Tests at ALL standard breakpoints:
- **Mobile Portrait**: 375px × 667px (iPhone SE)
- **Mobile Portrait Large**: 414px × 896px (iPhone 11 Pro)
- **Mobile Landscape**: 667px × 375px
- **Tablet Portrait**: 768px × 1024px (iPad)
- **Tablet Landscape**: 1024px × 768px
- **Small Desktop**: 1280px × 720px
- **Large Desktop**: 1920px × 1080px

### 2. Comprehensive Scrolling
For EACH breakpoint:
- Scroll to top of page
- Take screenshot of viewport
- Scroll down by viewport height
- Take screenshot
- Repeat until bottom of page
- Verify no horizontal scrolling
- Check all content is accessible

### 3. Touch Target Verification
Validates mobile usability:
- All buttons minimum 44px × 44px
- Adequate spacing between tappable elements (8px minimum)
- No overlapping interactive elements
- Touch targets not too close to screen edges

### 4. Visual Verification
Captures evidence of:
- Layout at each breakpoint
- Component stacking on mobile
- Text readability without zooming
- Image scaling and aspect ratios
- Modal/dialog behavior on small screens
- Navigation menu responsiveness

### 5. Scroll Behavior Testing
Verifies smooth scrolling:
- No janky animations
- Sticky headers work correctly
- Infinite scroll (if applicable)
- Pull-to-refresh doesn't interfere
- Scroll position maintained on navigation

## Available Playwright MCP Tools

- `mcp__playwright__browser_navigate` - Navigate to page
- `mcp__playwright__browser_resize` - Change viewport size **CRITICAL FOR THIS SKILL**
- `mcp__playwright__browser_take_screenshot` - Capture visual state **USE EXTENSIVELY**
- `mcp__playwright__browser_evaluate` - Run JavaScript to scroll and measure
- `mcp__playwright__browser_snapshot` - Get page accessibility tree
- `mcp__playwright__browser_scroll` - Scroll programmatically
- `mcp__playwright__browser_wait_for` - Wait for scroll completion
- `mcp__playwright__browser_close` - Close browser when done

## Testing Workflow

### Step 1: Initialize Browser
```
mcp__playwright__browser_navigate(url)
```

### Step 2: Test Each Breakpoint
For each breakpoint (375px, 414px, 768px, 1024px, 1280px, 1920px):

```javascript
// Resize to breakpoint
mcp__playwright__browser_resize(width, height)

// Wait for layout to settle
mcp__playwright__browser_wait_for(selector: "body", state: "stable")

// Get page height
const pageHeight = await mcp__playwright__browser_evaluate(`
  document.documentElement.scrollHeight
`)

// Get viewport height
const viewportHeight = await mcp__playwright__browser_evaluate(`
  window.innerHeight
`)

// Calculate number of screenshots needed
const numScreenshots = Math.ceil(pageHeight / viewportHeight)

// Scroll and screenshot
for (let i = 0; i < numScreenshots; i++) {
  // Scroll to position
  await mcp__playwright__browser_evaluate(`
    window.scrollTo(0, ${i * viewportHeight})
  `)

  // Wait for scroll to complete
  await mcp__playwright__browser_wait_for(timeout: 500)

  // Take screenshot
  await mcp__playwright__browser_take_screenshot(
    filename: `${breakpoint}_scroll_${i}.png`
  )

  // Check for horizontal scroll (BAD!)
  const hasHorizontalScroll = await mcp__playwright__browser_evaluate(`
    document.documentElement.scrollWidth > window.innerWidth
  `)

  if (hasHorizontalScroll) {
    // CRITICAL ISSUE - Report immediately
    console.error(`Horizontal scroll detected at ${breakpoint}px`)
  }
}
```

### Step 3: Test Touch Targets (Mobile Only)
For viewports < 768px:

```javascript
// Find all interactive elements
const touchTargets = await mcp__playwright__browser_evaluate(`
  const elements = document.querySelectorAll('button, a, input, select, textarea, [role="button"]')
  Array.from(elements).map(el => {
    const rect = el.getBoundingClientRect()
    return {
      tag: el.tagName,
      text: el.textContent?.substring(0, 20),
      width: rect.width,
      height: rect.height,
      x: rect.x,
      y: rect.y
    }
  })
`)

// Check each touch target
touchTargets.forEach(target => {
  if (target.width < 44 || target.height < 44) {
    console.error(`Touch target too small: ${target.tag} "${target.text}" is ${target.width}x${target.height}px (min 44x44px)`)
  }
})
```

### Step 4: Test Navigation Responsiveness
```javascript
// Check if mobile menu exists on small screens
if (viewport.width < 768) {
  const hasMobileMenu = await mcp__playwright__browser_evaluate(`
    // Look for hamburger icon or mobile nav
    const hamburger = document.querySelector('[aria-label*="menu"], .mobile-menu, .hamburger')
    hamburger !== null
  `)

  if (!hasMobileMenu) {
    console.warn('No mobile menu found on mobile viewport')
  }
}
```

### Step 5: Test Form Layouts
```javascript
// Verify forms are single-column on mobile
if (viewport.width < 768) {
  const formLayouts = await mcp__playwright__browser_evaluate(`
    const forms = document.querySelectorAll('form')
    Array.from(forms).map(form => {
      const inputs = form.querySelectorAll('input, select, textarea')
      const positions = Array.from(inputs).map(input => input.getBoundingClientRect().left)
      const uniqueColumns = [...new Set(positions)].length
      return {
        formId: form.id || 'unknown',
        columns: uniqueColumns
      }
    })
  `)

  formLayouts.forEach(layout => {
    if (layout.columns > 1) {
      console.error(`Form "${layout.formId}" has ${layout.columns} columns on mobile (should be 1)`)
    }
  })
}
```

### Step 6: Generate Report
```javascript
// Compile all findings
const report = {
  breakpoints_tested: ['375px', '414px', '768px', '1024px', '1280px', '1920px'],
  screenshots_captured: totalScreenshots,
  horizontal_scroll_issues: horizontalScrollIssues,
  touch_target_violations: touchTargetViolations,
  layout_issues: layoutIssues,
  status: issues.length === 0 ? 'PASS' : 'FAIL'
}
```

## Docker IP Configuration

**IMPORTANT**: When testing against Docker containers, use the container IP address, NOT localhost.

### Get Docker Container IP:
```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' {container_name}
```

### Use in Playwright:
```
# Instead of:
mcp__playwright__browser_navigate("http://localhost:3003")

# Use:
mcp__playwright__browser_navigate("http://172.18.0.5:80")
```

## Expected Inputs
- URL to test (Docker IP address if using containers)
- Page/feature to test
- Specific breakpoints (or use all standard ones)

## Deliverables
- Screenshot for each breakpoint at each scroll position
- List of horizontal scroll violations
- List of touch target violations (< 44px)
- Form layout issues on mobile
- Navigation responsiveness issues
- Overall PASS/FAIL status
- Detailed report with recommendations

## Example: Complete Mobile Testing Flow

```
// Test URL (using Docker IP)
const url = "http://172.18.0.5:80/schedules"

// Navigate
mcp__playwright__browser_navigate(url)

// Define breakpoints to test
const breakpoints = [
  { name: 'mobile_portrait', width: 375, height: 667 },
  { name: 'mobile_large', width: 414, height: 896 },
  { name: 'tablet_portrait', width: 768, height: 1024 },
  { name: 'desktop', width: 1280, height: 720 },
  { name: 'desktop_large', width: 1920, height: 1080 }
]

// Test each breakpoint
for (const breakpoint of breakpoints) {
  console.log(`Testing ${breakpoint.name} (${breakpoint.width}x${breakpoint.height})`)

  // Resize
  mcp__playwright__browser_resize(breakpoint.width, breakpoint.height)

  // Get page dimensions
  const dimensions = await mcp__playwright__browser_evaluate(`({
    pageHeight: document.documentElement.scrollHeight,
    pageWidth: document.documentElement.scrollWidth,
    viewportHeight: window.innerHeight,
    viewportWidth: window.innerWidth
  })`)

  // Check for horizontal scroll
  if (dimensions.pageWidth > dimensions.viewportWidth) {
    console.error(`❌ FAIL: Horizontal scroll at ${breakpoint.name}`)
    console.error(`   Page width: ${dimensions.pageWidth}px, Viewport: ${dimensions.viewportWidth}px`)
  }

  // Calculate scroll positions
  const scrollPositions = Math.ceil(dimensions.pageHeight / dimensions.viewportHeight)

  // Scroll and capture screenshots
  for (let i = 0; i < scrollPositions; i++) {
    const scrollY = i * dimensions.viewportHeight

    // Scroll
    await mcp__playwright__browser_evaluate(`window.scrollTo(0, ${scrollY})`)
    await mcp__playwright__browser_wait_for(timeout: 300)

    // Screenshot
    await mcp__playwright__browser_take_screenshot(
      filename: `${breakpoint.name}_scroll_${i}_y${scrollY}.png`
    )

    console.log(`  📸 Captured: ${breakpoint.name}_scroll_${i}.png (scroll position: ${scrollY}px)`)
  }

  // Test touch targets for mobile
  if (breakpoint.width < 768) {
    const touchIssues = await mcp__playwright__browser_evaluate(`
      const buttons = document.querySelectorAll('button, a[role="button"], [onclick]')
      const issues = []
      buttons.forEach((btn, idx) => {
        const rect = btn.getBoundingClientRect()
        if (rect.width < 44 || rect.height < 44) {
          issues.push({
            element: btn.tagName + (btn.textContent ? ': ' + btn.textContent.substring(0, 20) : ''),
            size: \`\${Math.round(rect.width)}x\${Math.round(rect.height)}px\`
          })
        }
      })
      issues
    `)

    if (touchIssues.length > 0) {
      console.error(`❌ Touch target violations at ${breakpoint.name}:`)
      touchIssues.forEach(issue => {
        console.error(`   - ${issue.element}: ${issue.size} (min 44x44px required)`)
      })
    } else {
      console.log(`✅ All touch targets meet 44px minimum`)
    }
  }

  // Scroll back to top for next breakpoint
  await mcp__playwright__browser_evaluate(`window.scrollTo(0, 0)`)
}

// Close browser
mcp__playwright__browser_close()

console.log('Mobile responsive testing complete!')
```

## Validation Checklist

### Layout
- [ ] No horizontal scrolling at any breakpoint
- [ ] All content visible without zooming
- [ ] Images scale proportionally
- [ ] Text remains readable (min 16px on mobile)
- [ ] No content cut off at edges

### Touch Interactions (Mobile < 768px)
- [ ] All buttons/links minimum 44x44px
- [ ] Adequate spacing between touch targets (8px)
- [ ] No overlapping interactive elements
- [ ] Touch targets not at extreme screen edges

### Navigation
- [ ] Mobile menu appears on small screens (< 768px)
- [ ] Desktop navigation on large screens (>= 1024px)
- [ ] Menu items all accessible
- [ ] Deep linking works at all sizes

### Forms
- [ ] Single column layout on mobile
- [ ] Multi-column on desktop
- [ ] Input fields large enough to tap (44px height)
- [ ] Keyboard doesn't obscure inputs on mobile

### Content
- [ ] Grid layouts adapt per breakpoint
- [ ] Tables convert to cards/stacked layout on mobile
- [ ] Modals/dialogs fit mobile screens
- [ ] No content hidden or inaccessible

## Integration with QA Agents

The QA Frontend Engineer agent should ALWAYS use this skill to:
1. Test all breakpoints (not just desktop)
2. Scroll through entire page at each breakpoint
3. Capture screenshots as evidence
4. Verify touch targets on mobile
5. Check for horizontal scrolling
6. Validate form layouts

## Common Issues Detected

### Issue: Horizontal Scroll on Mobile
**Detected**: Page width > viewport width
**Common Causes**:
- Fixed width elements (e.g., `width: 1200px`)
- Images without `max-width: 100%`
- Long unbreakable text (URLs)
- Negative margins breaking out of container

### Issue: Touch Targets Too Small
**Detected**: Button/link < 44x44px on mobile
**Common Causes**:
- Desktop-sized buttons on mobile
- Icon-only buttons without padding
- Links inline in text

### Issue: Content Cut Off
**Detected**: Elements positioned outside viewport
**Common Causes**:
- Absolute positioning without responsive values
- Fixed positioning without mobile adjustments
- Overflow hidden cutting off content

### Issue: Forms Not Mobile-Friendly
**Detected**: Multi-column form on mobile
**Common Causes**:
- CSS Grid not responsive
- Flexbox not wrapping on mobile
- Fixed columns in form layout

This skill ensures comprehensive mobile testing that catches layout issues, usability problems, and responsive design bugs that would otherwise be missed with desktop-only testing.
