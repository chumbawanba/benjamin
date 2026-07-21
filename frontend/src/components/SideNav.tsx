import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { ThemeIcon } from './ThemeToggle';
import { IconHome, IconLogout, IconSliders, IconWallet } from './icons';

function linkClass({ isActive }: { isActive: boolean }): string {
  return `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium ${
    isActive
      ? 'bg-navy-50 text-navy-700 dark:bg-navy-500/15 dark:text-navy-400'
      : 'text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800'
  }`;
}

// Navegação lateral fixa à esquerda, só no desktop (hidden lg:flex - no mobile a
// navegação vive na NavBar, em baixo, ver NavBar.tsx e Layout.tsx). Substitui a barra
// de baixo esticada em ecrãs largos por um padrão mais habitual em apps desktop
// (Notion, Slack, etc.) - lista vertical de ícone + rótulo.
export default function SideNav() {
  const { logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  return (
    <nav className="hidden lg:flex lg:flex-col lg:w-56 lg:shrink-0 lg:h-screen lg:sticky lg:top-0 border-r border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-4">
      <div className="flex items-center gap-2 px-2 mb-6">
        <img src="/icon-192.png" alt="" className="w-8 h-8 rounded-full shrink-0" />
        <span className="text-base font-bold text-gray-900 dark:text-slate-100">Benjamin</span>
      </div>

      <div className="flex-1 flex flex-col gap-1">
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
          Desenhar estratégia
        </NavLink>
      </div>

      <div className="flex flex-col gap-1 pt-3 border-t border-gray-100 dark:border-slate-800">
        <button
          onClick={toggleTheme}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800"
        >
          <ThemeIcon theme={theme} />
          {theme === 'dark' ? 'Tema escuro' : 'Tema claro'}
        </button>
        <button
          onClick={logout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-800"
        >
          <IconLogout />
          Sair
        </button>
      </div>
    </nav>
  );
}
