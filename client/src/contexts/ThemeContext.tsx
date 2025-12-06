import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
    theme: Theme;
    toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
    // Helper to get time-based theme (GMT+7)
    const getAutoTheme = (): Theme => {
        try {
            const now = new Date();
            const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
            const vnTime = new Date(utc + (3600000 * 7));
            const currentHour = vnTime.getHours();
            // Dark mode from 18:00 (6 PM) to 06:00 (6 AM)
            return (currentHour >= 18 || currentHour < 6) ? 'dark' : 'light';
        } catch (e) {
            console.error("Error detecting time for theme:", e);
            return 'light';
        }
    };

    const [theme, setTheme] = useState<Theme>(() => {
        const saved = localStorage.getItem('theme');
        if (saved === 'dark' || saved === 'light') return saved;
        return getAutoTheme();
    });

    // Apply theme to DOM
    useEffect(() => {
        const root = window.document.documentElement;
        if (theme === 'dark') {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }
    }, [theme]);

    // Periodically check time for auto-switch (if not overridden)
    useEffect(() => {
        const checkTime = () => {
            const saved = localStorage.getItem('theme');
            // If user hasn't manually set a preference, follow the clock
            if (!saved) {
                const autoTheme = getAutoTheme();
                setTheme((prev: Theme) => {
                    if (prev !== autoTheme) return autoTheme;
                    return prev;
                });
            }
        };

        const interval = setInterval(checkTime, 60000); // Check every minute
        return () => clearInterval(interval);
    }, []);

    const toggleTheme = () => {
        setTheme((prev: Theme) => {
            const newTheme = prev === 'light' ? 'dark' : 'light';
            localStorage.setItem('theme', newTheme); // Save preference
            return newTheme;
        });
    };

    return (
        <ThemeContext.Provider value={{ theme, toggleTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

export function useTheme() {
    const context = useContext(ThemeContext);
    if (context === undefined) {
        throw new Error('useTheme must be used within a ThemeProvider');
    }
    return context;
}
