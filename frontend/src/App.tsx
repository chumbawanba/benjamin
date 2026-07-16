import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import { AuthProvider } from './context/AuthContext';
import ChecklistEditor from './pages/ChecklistEditor';
import Checklists from './pages/Checklists';
import Feed from './pages/Feed';
import Login from './pages/Login';
import Watchlist from './pages/Watchlist';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/watchlist" element={<Watchlist />} />
              <Route path="/checklists" element={<Checklists />} />
              <Route path="/checklists/:id" element={<ChecklistEditor />} />
              <Route path="/feed" element={<Feed />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/watchlist" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
