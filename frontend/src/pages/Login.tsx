import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Falha ao iniciar sessão');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-slate-950 px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 p-6 rounded-xl shadow-sm">
        <h1 className="text-2xl font-bold text-petrol-600 dark:text-petrol-400 mb-1">Benjamin</h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mb-6">Inicia sessão para continuar</p>

        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1" htmlFor="email">
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-3 py-2 mb-4 text-sm"
        />

        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-3 py-2 mb-4 text-sm"
        />

        {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-petrol-600 text-white rounded-lg py-2 text-sm font-semibold disabled:opacity-50"
        >
          {loading ? 'A entrar…' : 'Entrar'}
        </button>

        <p className="text-xs text-gray-400 dark:text-slate-500 mt-4 text-center">
          Registo desativado por defeito (ALLOW_REGISTRATION). Pede ao administrador para criar a tua conta.
        </p>
      </form>
    </div>
  );
}
