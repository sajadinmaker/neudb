(() => {
  const $ = (id) => document.getElementById(id);
  const state = { base: sessionStorage.getItem('neudb-api-url') || 'http://127.0.0.1:8000', key: sessionStorage.getItem('neudb-api-key') || '', table: '', records: [], editing: null };
  const connectionDialog = $('connection-dialog');
  const recordDialog = $('record-dialog');

  function showNotice(message, error = false) { const el = $('notice'); el.textContent = message; el.className = `notice${error ? ' error' : ''}`; el.hidden = false; }
  function clearNotice() { $('notice').hidden = true; }
  async function request(path, options = {}) {
    const response = await fetch(`${state.base.replace(/\/$/, '')}${path}`, { ...options, headers: { 'Content-Type': 'application/json', 'X-API-Key': state.key, ...(options.headers || {}) } });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
    return body;
  }
  function setConnected(connected) { $('connection-dot').classList.toggle('online', connected); $('connection-label').textContent = connected ? 'Connected' : 'Not connected'; }
  function openDialog(dialog) { if (typeof dialog.showModal === 'function') dialog.showModal(); else dialog.setAttribute('open', ''); }
  function closeDialog(dialog) { dialog.close?.(); dialog.removeAttribute('open'); }

  async function connect() {
    try { await request('/health'); const data = await request('/tables'); setConnected(true); $('welcome').hidden = true; $('workspace').hidden = false; renderTables(data.tables); if (data.tables[0]) selectTable(data.tables[0]); clearNotice(); }
    catch (error) { setConnected(false); showNotice(error.message || 'Could not connect to neuDB.', true); }
  }
  function renderTables(tables) { $('table-list').innerHTML = tables.length ? tables.map((name) => `<button class="table-item${name === state.table ? ' active' : ''}" data-table="${escapeHtml(name)}">▦ ${escapeHtml(name)}</button>`).join('') : '<p class="muted">No tables yet.</p>'; document.querySelectorAll('[data-table]').forEach((button) => button.onclick = () => selectTable(button.dataset.table)); }
  async function selectTable(name) { state.table = name; $('table-title').textContent = name; document.querySelectorAll('[data-table]').forEach((button) => button.classList.toggle('active', button.dataset.table === name)); await loadRecords(); }
  async function loadRecords() { try { clearNotice(); const data = await request(`/tables/${encodeURIComponent(state.table)}/records?limit=1000`); state.records = data.records; renderRecords(); } catch (error) { showNotice(error.message, true); } }
  function renderRecords() {
    const query = $('record-search').value.trim().toLowerCase(); const records = state.records.filter((record) => !query || JSON.stringify(record).toLowerCase().includes(query));
    $('record-count').textContent = `${state.records.length} record${state.records.length === 1 ? '' : 's'}${query ? ` · ${records.length} shown` : ''}`;
    $('empty-state').hidden = records.length > 0;
    if (!records.length) { $('records-head').innerHTML = ''; $('records-body').innerHTML = ''; return; }
    const keys = [...new Set(records.flatMap((record) => Object.keys(record)))]; $('records-head').innerHTML = `<tr>${keys.map((key) => `<th>${escapeHtml(key)}</th>`).join('')}<th>Actions</th></tr>`;
    $('records-body').innerHTML = records.map((record) => `<tr>${keys.map((key) => `<td>${escapeHtml(formatValue(record[key]))}</td>`).join('')}<td class="row-actions"><button data-edit="${escapeHtml(record.id)}">Edit</button><button class="delete" data-delete="${escapeHtml(record.id)}">Delete</button></td></tr>`).join('');
    document.querySelectorAll('[data-edit]').forEach((button) => button.onclick = () => editRecord(button.dataset.edit)); document.querySelectorAll('[data-delete]').forEach((button) => button.onclick = () => deleteRecord(button.dataset.delete));
  }
  function formatValue(value) { return typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value ?? ''); }
  function escapeHtml(value) { return String(value).replace(/[&<>"']/g, (char) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[char])); }
  function editRecord(id) { const record = state.records.find((item) => item.id === id); if (!record) return; state.editing = id; $('record-mode').textContent = 'EDIT RECORD'; $('record-dialog-title').textContent = 'Edit record'; $('record-json').value = JSON.stringify(record, null, 2); openDialog(recordDialog); }
  async function saveRecord(event) { event.preventDefault(); try { const record = JSON.parse($('record-json').value); if (!record || Array.isArray(record) || typeof record !== 'object') throw new Error('Enter a JSON object.'); if (state.editing) { delete record.id; await request(`/tables/${encodeURIComponent(state.table)}/records/${encodeURIComponent(state.editing)}`, { method: 'PATCH', body: JSON.stringify(record) }); } else await request(`/tables/${encodeURIComponent(state.table)}/records`, { method: 'POST', body: JSON.stringify(record) }); closeDialog(recordDialog); state.editing = null; await loadRecords(); showNotice('Record saved.'); } catch (error) { showNotice(error.message || 'Invalid JSON.', true); } }
  async function deleteRecord(id) { if (!confirm('Delete this record permanently?')) return; try { await request(`/tables/${encodeURIComponent(state.table)}/records/${encodeURIComponent(id)}`, { method: 'DELETE' }); await loadRecords(); showNotice('Record deleted.'); } catch (error) { showNotice(error.message, true); } }
  async function createTable() { const name = prompt('New table name (letters, numbers, underscores):'); if (!name) return; try { await request('/tables', { method: 'POST', body: JSON.stringify({ name }) }); const data = await request('/tables'); renderTables(data.tables); await selectTable(name); showNotice('Table created.'); } catch (error) { showNotice(error.message, true); } }

  $('connection-form').addEventListener('submit', (event) => { event.preventDefault(); state.base = $('api-url').value.trim(); state.key = $('api-key').value.trim(); sessionStorage.setItem('neudb-api-url', state.base); sessionStorage.setItem('neudb-api-key', state.key); closeDialog(connectionDialog); connect(); });
  $('open-connection').onclick = () => openDialog(connectionDialog); $('new-table').onclick = createTable; $('refresh').onclick = loadRecords; $('add-record').onclick = () => { state.editing = null; $('record-mode').textContent = 'NEW RECORD'; $('record-dialog-title').textContent = 'Add record'; $('record-json').value = '{\n  "content": ""\n}'; openDialog(recordDialog); }; $('record-form').addEventListener('submit', saveRecord); $('record-search').addEventListener('input', renderRecords);
  document.querySelectorAll('[data-close]').forEach((button) => button.onclick = () => closeDialog(button.closest('dialog')));
  $('api-url').value = state.base; $('api-key').value = state.key; if (state.key) connect();
})();
