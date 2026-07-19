import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ThemeToggle from './ThemeToggle';

function linkClass({ isActive }: { isActive: boolean }): string {
  return `flex-1 text-center py-3 text-sm font-medium ${
    isActive ? 'text-petrol-600 dark:text-petrol-400' : 'text-gray-500 dark:text-slate-500'
  }`;
}

export default function NavBar() {
  const { logout } = useAuth();
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-900 border-t border-gray-200 dark:border-slate-800 flex items-center max-w-md md:max-w-2xl lg:max-w-4xl mx-auto">
      <NavLink to="/" end className={linkClass}>
        Overview
      </NavLink>
      <NavLink to="/watchlist" className={linkClass}>
        Watchlist
      </NavLink>
      <NavLink to="/portfolio" className={linkClass}>
        Portfolio
      </NavLink>
      <NavLink to="/strategies" className={linkClass}>
        Estratégias
      </NavLink>
      <NavLink to="/feed" className={linkClass}>
        Avaliações
      </NavLink>
      <ThemeToggle />
      <button onClick={logout} className="flex-1 text-center py-3 text-sm font-medium text-gray-400 dark:text-slate-500">
        Sair
      </button>
    </nav>
  );
}
