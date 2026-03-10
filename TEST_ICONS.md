# Icon Fix Testing Guide

## Quick Test

1. **Start Streamlit**:
   ```bash
   streamlit run frontend/app.py
   ```

2. **Open Browser DevTools** (F12)

3. **Check if CSS is loaded**:
   - Go to "Elements" tab
   - Find `<style>` tag in `<head>`
   - Search for "FIX STREAMLIT ICON TEXT"
   - If found → CSS is loaded ✅
   - If not found → CSS not loading ❌

4. **Inspect sidebar collapse button**:
   - Right-click the sidebar collapse button
   - Click "Inspect"
   - Look for `[data-testid="collapsedControl"]`
   - Check computed styles:
     - Should have: `font-size: 0px`
     - Should have: `color: rgba(0, 0, 0, 0)`
   - Find the `<svg>` element inside
     - Should have: `font-size: 24px`
     - Should be visible

5. **Test expander**:
   - Find any expander on the page (like "Advanced Settings")
   - Click to expand/collapse
   - Should show arrow icon, not text

## If Icons Still Show Text

### Option 1: Check if page loaded the theme
```javascript
// Run in browser console:
document.documentElement.getAttribute('data-theme')
// Should return: "dark" or "light"
```

### Option 2: Force clear browser cache
1. Press `Ctrl+Shift+Delete` (or `Cmd+Shift+Delete` on Mac)
2. Clear cache and hard reload: `Ctrl+Shift+R`

### Option 3: Verify Streamlit version
```bash
streamlit version
# Should be 1.30.0 or higher
```

### Option 4: Check for CSS conflicts
In browser DevTools Console, run:
```javascript
// Check if collapsed control exists
console.log(document.querySelector('[data-testid="collapsedControl"]'));

// Check its computed style
let el = document.querySelector('[data-testid="collapsedControl"]');
console.log(window.getComputedStyle(el).fontSize);
// Should be "0px"
```

## Manual CSS Override (Emergency Fix)

If nothing else works, add this to browser console:
```javascript
// Nuclear option - manually hide text
let style = document.createElement('style');
style.textContent = `
  [data-testid="collapsedControl"],
  [data-testid="stExpander"] details summary > div:last-child,
  span[data-baseweb="icon"] {
    font-size: 0 !important;
  }
  [data-testid="collapsedControl"] svg,
  [data-testid="stExpander"] summary svg,
  span[data-baseweb="icon"] svg {
    font-size: 24px !important;
  }
`;
document.head.appendChild(style);
```

## Expected Behavior

### ✅ Working
- Sidebar collapse button shows ◄ arrow
- Expanders show ▼ or ▶ arrows
- No text like "keyboard_double_arrow_left"
- Theme toggle shows "🌙 Dark Mode" or "☀️ Light Mode"

### ❌ Not Working
- Text showing: "keyboard_double_arrow_left", "_arrow_drop_down", "expand_more"
- Icons not visible
- Buttons misaligned

## Common Issues

### Issue: CSS not applied after Streamlit update
**Solution**: Clear `.streamlit` cache
```bash
rm -rf ~/.streamlit/cache
```

### Issue: Icons work sometimes but not always
**Solution**: Streamlit async rendering issue. Add this to `config.toml`:
```toml
[runner]
fastReruns = true
```

### Issue: Dark mode not persisting
**Solution**: Check localStorage in browser console:
```javascript
localStorage.getItem('nestscope-theme')
// Should return "dark" or "light"

// If null, set it manually:
localStorage.setItem('nestscope-theme', 'dark');
location.reload();
```

## Debug Output

If you still see icon text, please provide:

1. **Streamlit version**:
   ```bash
   streamlit version
   ```

2. **Browser version**:
   - Chrome/Firefox version
   - OS

3. **Console errors**:
   - Open DevTools → Console
   - Copy any red errors

4. **Computed CSS for collapsed control**:
   ```javascript
   let el = document.querySelector('[data-testid="collapsedControl"]');
   console.log({
     fontSize: window.getComputedStyle(el).fontSize,
     color: window.getComputedStyle(el).color,
     display: window.getComputedStyle(el).display
   });
   ```
