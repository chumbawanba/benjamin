import { Outlet } from 'react-router-dom';
import NavBar from './NavBar';

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50 pb-16">
      <main className="max-w-md mx-auto px-4 pt-4">
        <Outlet />
      </main>
      <NavBar />
    </div>
  );
}
