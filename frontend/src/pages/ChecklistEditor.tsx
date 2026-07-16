import { FormEvent, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ApiError, api } from '../api/client';
import { ChecklistItem, ChecklistItemInput, ChecklistTemplate, MetricInfo } from '../api/types';

const OPERATORS = ['<', '>', '<=', '>=', '==', 'between'];

const emptyForm: ChecklistItemInput = {
  name: '',
  category: '',
  metric: '',
  operator: '<',
  threshold_value: null,
  threshold_value_max: null,
  weight: 1,
  direction: 'buy_signal',
  is_active: true,
  display_order: null,
};

export default function ChecklistEditor() {
  const { id } = useParams<{ id: string }>();
  const [template, setTemplate] = useState<ChecklistTemplate | null>(null);
  const [metrics, setMetrics] = useState<MetricInfo[]>([]);
  const [form, setForm] = useState<ChecklistItemInput>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [templates, metricList] = await Promise.all([
        api.get<ChecklistTemplate[]>('/checklists'),
        api.get<MetricInfo[]>('/checklists/metrics'),
      ]);
      const found = templates.find((t) => t.id === id) ?? null;
      setTemplate(found);
      setMetrics(metricList);
      setForm((f) => (f.metric ? f : { ...f, metric: metricList[0]?.key ?? '' }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar checklist');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  function startEdit(item: ChecklistItem) {
    setEditingId(item.id);
    setForm({
      name: item.name,
      category: item.category ?? '',
      metric: item.metric,
      operator: item.operator,
      threshold_value: item.threshold_value,
      threshold_value_max: item.threshold_value_max,
      weight: item.weight,
      direction: item.direction,
      is_active: item.is_active,
      display_order: item.display_order,
    });
  }

  function resetForm() {
    setEditingId(null);
    setForm({ ...emptyForm, metric: metrics[0]?.key ?? '' });
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!id) return;
    setError(null);

    const payload: ChecklistItemInput = {
      name: form.name,
      category: form.category && form.category.trim() !== '' ? form.category : null,
      metric: form.metric,
      operator: form.operator,
      threshold_value: form.threshold_value === null || (form.threshold_value as unknown) === '' ? null : Number(form.threshold_value),
      threshold_value_max:
        form.operator === 'between' && form.threshold_value_max !== null && (form.threshold_value_max as unknown) !== ''
          ? Number(form.threshold_value_max)
          : null,
      weight: Number(form.weight),
      direction: form.direction,
      is_active: form.is_active ?? true,
      display_order: form.display_order ?? null,
    };

    try {
      if (editingId) {
        await api.put(`/checklists/items/${editingId}`, payload);
      } else {
        await api.post(`/checklists/${id}/items`, payload);
      }
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao gravar critério');
    }
  }

  async function handleDeleteItem(itemId: string) {
    if (!confirm('Remover este critério?')) return;
    try {
      await api.delete(`/checklists/items/${itemId}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao remover critério');
    }
  }

  if (loading) return <p className="text-sm text-gray-500">A carregar…</p>;
  if (!template) {
    return (
      <p className="text-sm text-red-600">
        Checklist não encontrada.{' '}
        <Link to="/checklists" className="text-blue-600">
          Voltar
        </Link>
      </p>
    );
  }

  return (
    <div>
      <Link to="/checklists" className="text-sm text-blue-600">
        &larr; Checklists
      </Link>
      <h1 className="text-xl font-bold text-gray-900 mt-2 mb-4">{template.name}</h1>

      <ul className="space-y-2 mb-6">
        {template.items.map((item) => (
          <li key={item.id} className="bg-white rounded-xl shadow-sm p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900 text-sm">{item.name}</p>
                <p className="text-xs text-gray-500">
                  {item.metric} {item.operator}{' '}
                  {item.operator === 'between' ? `${item.threshold_value} - ${item.threshold_value_max}` : item.threshold_value} · peso{' '}
                  {item.weight} · {item.direction === 'buy_signal' ? 'compra' : 'venda'}
                  {!item.is_active ? ' · inativo' : ''}
                </p>
              </div>
              <div className="flex gap-2 text-sm font-medium shrink-0">
                <button onClick={() => startEdit(item)} className="text-blue-600">
                  Editar
                </button>
                <button onClick={() => handleDeleteItem(item.id)} className="text-red-500">
                  Apagar
                </button>
              </div>
            </div>
          </li>
        ))}
        {template.items.length === 0 && <p className="text-sm text-gray-500">Sem critérios ainda.</p>}
      </ul>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm p-4 space-y-3">
        <h2 className="font-semibold text-gray-900 text-sm">{editingId ? 'Editar critério' : 'Novo critério'}</h2>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Nome</label>
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Categoria (opcional)</label>
          <input
            value={form.category ?? ''}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            placeholder="ex: technical, fundamental"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Métrica</label>
          <select
            value={form.metric}
            onChange={(e) => setForm({ ...form, metric: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            {metrics.map((m) => (
              <option key={m.key} value={m.key}>
                {m.key}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Operador</label>
            <select
              value={form.operator}
              onChange={(e) => setForm({ ...form, operator: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              {OPERATORS.map((op) => (
                <option key={op} value={op}>
                  {op}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Direção</label>
            <select
              value={form.direction}
              onChange={(e) => setForm({ ...form, direction: e.target.value as 'buy_signal' | 'sell_signal' })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              <option value="buy_signal">Compra</option>
              <option value="sell_signal">Venda</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              {form.operator === 'between' ? 'Mínimo' : 'Threshold'}
            </label>
            <input
              type="number"
              step="any"
              value={form.threshold_value ?? ''}
              onChange={(e) => setForm({ ...form, threshold_value: e.target.value === '' ? null : Number(e.target.value) })}
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          {form.operator === 'between' && (
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Máximo</label>
              <input
                type="number"
                step="any"
                value={form.threshold_value_max ?? ''}
                onChange={(e) =>
                  setForm({ ...form, threshold_value_max: e.target.value === '' ? null : Number(e.target.value) })
                }
                required
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
          )}
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Peso</label>
          <input
            type="number"
            step="any"
            value={form.weight}
            onChange={(e) => setForm({ ...form, weight: Number(e.target.value) })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>

        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={form.is_active ?? true}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
          />
          Ativo
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex gap-2">
          <button type="submit" className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-semibold">
            {editingId ? 'Guardar' : 'Adicionar'}
          </button>
          {editingId && (
            <button
              type="button"
              onClick={resetForm}
              className="flex-1 bg-gray-100 text-gray-700 rounded-lg py-2 text-sm font-semibold"
            >
              Cancelar
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
