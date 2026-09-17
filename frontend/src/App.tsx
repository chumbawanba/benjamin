import { useEffect } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import { AnalystChatProvider } from './context/AnalystChatContext';
import { AuthProvider } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import { ThemeProvider } from './context/ThemeContext';
import { trackPageview } from './lib/analytics';
import AdminStats from './pages/AdminStats';
import FxRates from './pages/FxRates';
import Login from './pages/Login';
import Notifications from './pages/Notifications';
import Overview from './pages/Overview';
import Patrimonio from './pages/Patrimonio';
import ProjectionPage from './pages/Projection';
import Register from './pages/Register';
import StockDetail from './pages/StockDetail';
import StrategyEditor from './pages/StrategyEditor';
import StrategyWorkspace from './pages/StrategyWorkspace';

// Regista uma pageview no GA4 em cada mudança de rota, incluindo a
// primeira - ver lib/analytics.ts (send_page_view vem desligado porque uma
// SPA não recarrega a página em cada navegação).
function AnalyticsTracker() {
  const location = useLocation();
  useEffect(() => {
    trackPageview(location.pathname + location.search);
  }, [location]);
  return null;
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AnalystChatProvider>
          <BrowserRouter>
            <AnalyticsTracker />
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/admin" element={<AdminStats />} />
              <Route element={<ProtectedRoute />}>
                <Route
                  element={
                    <NotificationProvider>
                      <Layout />
                    </NotificationProvider>
                  }
                >
                  <Route path="/" element={<Overview />} />
                  <Route path="/workspace" element={<StrategyWorkspace />} />
                  <Route path="/patrimonio" element={<Patrimonio />} />
                  {/* Rotas antigas (Portfolio/Loans separados, ver ESTADO.md secção 11) -
                      redirecionam para os separadores correspondentes em Património, para
                      não partir marcadores/links já guardados. */}
                  <Route path="/portfolio" element={<Navigate to="/patrimonio" replace />} />
                  <Route path="/loans" element={<Navigate to="/patrimonio?tab=emprestimos" replace />} />
                  <Route path="/portfolio/fx-rates" element={<FxRates />} />
                  <Route path="/projection" element={<ProjectionPage />} />
                  <Route path="/stocks/:id" element={<StockDetail />} />
                  <Route path="/strategies/:id" element={<StrategyEditor />} />
                  <Route path="/notifications" element={<Notifications />} />
                </Route>
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </AnalystChatProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
