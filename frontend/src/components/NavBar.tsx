import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function linkClass({ isActive }: { isActive: boolean }): string {
  return `flex-1 text-center py-3 text-sm font-medium ${isActive ? 'text-blue-600' : 'text-gray-500'}`;
}

export default function NavBar() {
  const { logout } = useAuth();
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 flex items-center max-w-md mx-auto">
      <NavLink to="/watchlist" className={linkClass}>
        Watchlist
      </NavLink>
      <NavLink to="/checklists" className={linkClass}>
        Checklists
      </NavLink>
      <NavLink to="/feed" className={linkClass}>
        Feed
      </NavLink>
      <button onClick={logout} className="flex-1 text-center py-3 text-sm font-medium text-gray-400">
        Sair
      </button>
    </nav>
  );
}
