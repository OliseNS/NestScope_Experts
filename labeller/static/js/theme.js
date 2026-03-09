/**
 * Theme Management for Nestperts
 * Handles dark/light mode toggling with localStorage persistence
 */

class ThemeManager {
    constructor() {
        this.theme = this.getInitialTheme();
        this.init();
    }

    getInitialTheme() {
        // Priority: localStorage > system preference > default (dark)
        const stored = localStorage.getItem('nestperts-theme');
        if (stored) {
            return stored;
        }

        // Check system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
            return 'light';
        }

        return 'dark'; // Default to dark theme
    }

    init() {
        // Apply initial theme
        this.applyTheme(this.theme);

        // Setup theme toggle buttons
        this.setupToggleButtons();

        // Listen for system theme changes
        this.watchSystemTheme();
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('nestperts-theme', theme);
        this.theme = theme;

        // Update toggle buttons
        this.updateToggleButtons();

        // Dispatch theme change event
        window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
    }

    toggle() {
        const newTheme = this.theme === 'dark' ? 'light' : 'dark';
        this.applyTheme(newTheme);
    }

    setupToggleButtons() {
        // Find all theme toggle buttons
        document.querySelectorAll('.theme-toggle').forEach(button => {
            button.addEventListener('click', () => this.toggle());
        });
    }

    updateToggleButtons() {
        document.querySelectorAll('.theme-toggle-thumb').forEach(thumb => {
            if (this.theme === 'dark') {
                thumb.textContent = '🌙';
            } else {
                thumb.textContent = '☀️';
            }
        });
    }

    watchSystemTheme() {
        if (window.matchMedia) {
            const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
            darkModeQuery.addEventListener('change', (e) => {
                // Only auto-switch if user hasn't manually set a preference
                if (!localStorage.getItem('nestperts-theme')) {
                    this.applyTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    }
}

// Initialize theme manager when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.themeManager = new ThemeManager();
    });
} else {
    window.themeManager = new ThemeManager();
}
