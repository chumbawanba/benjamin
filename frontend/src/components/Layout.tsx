import { Outlet } from 'react-router-dom';
import NavBar from './NavBar';

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 pb-16">
      <main className="max-w-md md:max-w-2xl lg:max-w-4xl mx-auto px-4 pt-4">
        <Outlet />
      </main>
      <NavBar />
    </div>
  );
}
