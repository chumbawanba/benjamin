import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ThemeToggle from './ThemeToggle';
import { IconHome, IconLogout, IconSliders, IconWallet } from './icons';

function linkClass({ isActive }: { isActive: boolean }): string {
  return `flex-1 flex flex-col items-center justify-center gap-0.5 py-2 text-xs font-medium ${
    isActive ? 'text-navy-600 dark:text-navy-400' : 'text-gray-500 dark:text-slate-500'
  }`;
}

// Barra de baixo, só no mobile (lg:hidden - no desktop a navegação vive na SideNav,
// à esquerda, ver SideNav.tsx e Layout.tsx).
export default function NavBar() {
  const { logout } = useAuth();
  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-900 border-t border-gray-200 dark:border-slate-800 flex items-center max-w-md md:max-w-2xl mx-auto">
      <NavLink to="/" end className={linkClass}>
        <IconHome />
        Overview
      </NavLink>
      <NavLink to="/portfolio" className={linkClass}>
        <IconWallet />
        Portfolio
      </NavLink>
      <NavLink to="/workspace" className={linkClass}>
        <IconSliders />
        Estratégia
      </NavLink>
      <ThemeToggle />
      <button
        onClick={logout}
        className="flex-1 flex flex-col items-center justify-center gap-0.5 py-2 text-xs font-medium text-gray-400 dark:text-slate-500"
      >
        <IconLogout />
        Sair
      </button>
    </nav>
  );
}
