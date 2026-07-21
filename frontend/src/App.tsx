import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import { AnalystChatProvider } from './context/AnalystChatContext';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import Login from './pages/Login';
import Overview from './pages/Overview';
import Portfolio from './pages/Portfolio';
import StockDetail from './pages/StockDetail';
import StrategyEditor from './pages/StrategyEditor';
import StrategyWorkspace from './pages/StrategyWorkspace';

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AnalystChatProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route element={<ProtectedRoute />}>
                <Route element={<Layout />}>
                  <Route path="/" element={<Overview />} />
                  <Route path="/workspace" element={<StrategyWorkspace />} />
                  <Route path="/portfolio" element={<Portfolio />} />
                  <Route path="/stocks/:id" element={<StockDetail />} />
                  <Route path="/strategies/:id" element={<StrategyEditor />} />
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
