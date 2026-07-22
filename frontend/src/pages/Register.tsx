import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ApiError } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await register(name, email, password, acceptedTerms);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Falha ao criar conta');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-slate-950 px-4">
      <div className="w-full max-w-sm">
        {/* Link normal (não Link do react-router) - a landing page é um site
            estático à parte, em appbenjamin.com, servido pelo Caddy fora da SPA. */}
        <a
          href="https://appbenjamin.com"
          className="inline-flex items-center gap-1 text-xs text-gray-400 dark:text-slate-500 hover:text-navy-600 dark:hover:text-navy-400 mb-3"
        >
          &larr; Voltar ao site
        </a>
        <form onSubmit={handleSubmit} className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 p-6 rounded-xl shadow-sm">
          <h1 className="text-2xl font-bold text-navy-600 dark:text-navy-400 mb-1">Benjamin</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mb-6">Cria a tua conta</p>

          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1" htmlFor="name">
            Nome
          </label>
          <input
            id="name"
            type="text"
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-3 py-2 mb-4 text-sm"
          />

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
            autoComplete="new-password"
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-3 py-2 mb-1 text-sm"
          />
          <p className="text-xs text-gray-400 dark:text-slate-500 mb-4">Mínimo 8 caracteres.</p>

          <label className="flex items-start gap-2 text-xs text-gray-500 dark:text-slate-400 mb-4">
            <input
              type="checkbox"
              checked={acceptedTerms}
              onChange={(e) => setAcceptedTerms(e.target.checked)}
              required
              className="mt-0.5 shrink-0"
            />
            <span>
              Li e aceito a{' '}
              <a href="https://appbenjamin.com/privacy-policy.html" className="text-navy-600 dark:text-navy-400 underline">
                Política de Privacidade
              </a>{' '}
              e a{' '}
              <a href="https://appbenjamin.com/cookie-policy.html" className="text-navy-600 dark:text-navy-400 underline">
                Política de Cookies
              </a>
              .
            </span>
          </label>

          {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-navy-600 text-white rounded-lg py-2 text-sm font-semibold disabled:opacity-50"
          >
            {loading ? 'A criar conta…' : 'Criar conta'}
          </button>

          <p className="text-xs text-gray-400 dark:text-slate-500 mt-4 text-center">
            Já tens conta?{' '}
            <Link to="/login" className="text-navy-600 dark:text-navy-400 font-medium">
              Entra aqui
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
