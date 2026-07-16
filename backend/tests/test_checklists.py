from tests.conftest import login

ITEM = {"name": "RSI sobrevendido", "metric": "RSI_14", "operator": "<",
        "threshold_value": 30, "weight": 2, "direction": "buy_signal"}


async def test_crud_checklist_and_items(client, user_a):
    headers = await login(client, "a@test.local", "password-a")
    resp = await client.post("/checklists", json={"name": "Value simples"}, headers=headers)
    assert resp.status_code == 201
    template_id = resp.json()["id"]

    resp = await client.post(f"/checklists/{template_id}/items", json=ITEM, headers=headers)
    assert resp.status_code == 201

    resp = await client.get("/checklists", headers=headers)
    assert len(resp.json()) == 1
    assert len(resp.json()[0]["items"]) == 1


async def test_invalid_metric_rejected(client, user_a):
    headers = await login(client, "a@test.local", "password-a")
    resp = await client.post("/checklists", json={"name": "T"}, headers=headers)
    template_id = resp.json()["id"]
    bad = dict(ITEM, metric="INVENTADO_99")
    resp = await client.post(f"/checklists/{template_id}/items", json=bad, headers=headers)
    assert resp.status_code == 422


async def test_metrics_endpoint(client, user_a):
    headers = await login(client, "a@test.local", "password-a")
    resp = await client.get("/checklists/metrics", headers=headers)
    keys = {m["key"] for m in resp.json()}
    assert "RSI_14" in keys and "PE_RATIO" in keys


async def test_checklist_isolation(client, user_a, user_b):
    headers_a = await login(client, "a@test.local", "password-a")
    headers_b = await login(client, "b@test.local", "password-b")
    resp = await client.post("/checklists", json={"name": "Privada"}, headers=headers_a)
    template_id = resp.json()["id"]
    resp = await client.put(f"/checklists/{template_id}", json={"name": "Hack"}, headers=headers_b)
    assert resp.status_code == 404
