import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, api } from '../api/client';
import { ChecklistTemplate } from '../api/types';

export default function Checklists() {
  const [templates, setTemplates] = useState<ChecklistTemplate[]>([]);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const data = await api.get<ChecklistTemplate[]>('/checklists');
      setTemplates(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar checklists');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await api.post('/checklists', { name: name.trim() });
      setName('');
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao criar checklist');
    }
  }

  async function toggleActive(t: ChecklistTemplate) {
    try {
      await api.put(`/checklists/${t.id}`, {
        name: t.name,
        description: t.description,
        is_active: !t.is_active,
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao atualizar checklist');
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Apagar esta checklist e todos os seus critérios?')) return;
    try {
      await api.delete(`/checklists/${id}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao apagar checklist');
    }
  }

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900 mb-4">Checklists</h1>

      <form onSubmit={handleCreate} className="flex gap-2 mb-4">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Nome da nova checklist"
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
        />
        <button type="submit" className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-semibold">
          Criar
        </button>
      </form>

      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500">A carregar…</p>
      ) : templates.length === 0 ? (
        <p className="text-sm text-gray-500">Ainda não tens checklists.</p>
      ) : (
        <ul className="space-y-2">
          {templates.map((t) => (
            <li key={t.id} className="bg-white rounded-xl shadow-sm p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-gray-900">{t.name}</p>
                  <p className="text-xs text-gray-500">{t.items.length} critério(s)</p>
                </div>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    t.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {t.is_active ? 'Ativa' : 'Inativa'}
                </span>
              </div>
              <div className="flex gap-3 mt-3 text-sm font-medium">
                <Link to={`/checklists/${t.id}`} className="text-blue-600">
                  Editar
                </Link>
                <button onClick={() => toggleActive(t)} className="text-gray-600">
                  {t.is_active ? 'Desativar' : 'Ativar'}
                </button>
                <button onClick={() => handleDelete(t.id)} className="text-red-500">
                  Apagar
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
