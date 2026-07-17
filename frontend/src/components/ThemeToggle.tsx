import { useTheme } from '../context/ThemeContext';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  return (
    <button
      onClick={toggleTheme}
      aria-label={theme === 'dark' ? 'Mudar para tema claro' : 'Mudar para tema escuro'}
      className="flex-1 flex items-center justify-center py-3 text-gray-500 dark:text-slate-500"
    >
      {theme === 'dark' ? (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
          <path d="M12 3a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0V4a1 1 0 0 1 1-1Zm0 15a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm9-6a1 1 0 1 1 0 2h-1a1 1 0 1 1 0-2h1ZM4 12a1 1 0 1 1 0 2H3a1 1 0 1 1 0-2h1Zm14.66-6.66a1 1 0 0 1 1.41 1.41l-.7.71a1 1 0 1 1-1.42-1.41l.71-.71ZM6.05 17.24a1 1 0 0 1 1.41 1.41l-.7.71A1 1 0 1 1 5.34 18l.71-.76Zm12.61 1.41a1 1 0 0 1-1.41 0l-.71-.7a1 1 0 0 1 1.42-1.42l.7.71a1 1 0 0 1 0 1.41ZM6.76 5.34a1 1 0 0 1-1.42 1.41l-.7-.7a1 1 0 1 1 1.41-1.42l.71.71ZM12 20a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0v-1a1 1 0 0 1 1-1Z" />
        </svg>
      ) : (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
          <path d="M20.35 14.5a8.5 8.5 0 0 1-11.35-11 8.5 8.5 0 1 0 11.35 11Z" />
        </svg>
      )}
    </button>
  );
}
