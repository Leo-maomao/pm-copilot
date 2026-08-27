(() => {
  const state = { index: null, selectedId: localStorage.getItem('prd-manager.selected'), results: [], selectedResult: -1, composing: false };
  const $ = (id) => document.getElementById(id);
  const tree = $('tree'), viewer = $('document-viewer'), empty = $('empty-state'), dialog = $('search-dialog'), input = $('search-input');
  const appShell = document.querySelector('.app-shell');
  const escape = (value) => String(value).replace(/[&<>'"]/g, (char) => ({ '&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;' })[char]);
  const displayDate = (value) => value ? value.replace(/-/g, '年').replace(/年(\d{2})$/, '月$1日') : '未标注日期';
  const allDocuments = () => state.index ? state.index.projects.flatMap((project) => project.documents) : [];
  function renderTree() {
    tree.innerHTML = (state.index?.projects || []).map((project) => {
      const collapsed = localStorage.getItem(`prd-manager.project.${project.name}`) === 'collapsed';
      return `<section class="project ${collapsed ? 'collapsed' : ''}" data-project="${escape(project.name)}"><button class="project-toggle" aria-expanded="${!collapsed}"><svg class="chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="m4 6 4 4 4-4"/></svg><span class="project-name">${escape(project.name)}</span><span class="project-count" aria-label="${project.documents.length} 份 PRD">${project.documents.length}</span></button><div class="document-list">${project.documents.map((item) => `<div class="document-row ${item.id === state.selectedId ? 'active' : ''}"><div class="document-heading"><button class="document-item" data-id="${item.id}"><span class="document-title">${escape(item.title)}</span></button><span class="document-actions"><button class="copy-document" data-id="${item.id}" aria-label="复制 ${escape(item.title)} 所在目录" title="复制所在目录"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="11" height="11" rx="1.5"/><path d="M5 16V5.5A1.5 1.5 0 0 1 6.5 4H17"/></svg></button><button class="reveal-document" data-id="${item.id}" aria-label="在访达中打开 ${escape(item.title)} 所在目录" title="在访达中打开所在目录"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7.5h6l1.5 2H20v8.25A1.25 1.25 0 0 1 18.75 19h-13A1.25 1.25 0 0 1 4.5 17.75z"/></svg></button></span></div><span class="document-date">${displayDate(item.prd_date)}</span></div>`).join('')}</div></section>`;
    }).join('');
    tree.querySelectorAll('.project-toggle').forEach((button) => button.onclick = () => { const project = button.closest('.project'); const isCollapsed = project.classList.toggle('collapsed'); button.setAttribute('aria-expanded', String(!isCollapsed)); localStorage.setItem(`prd-manager.project.${project.dataset.project}`, isCollapsed ? 'collapsed' : 'open'); });
    tree.querySelectorAll('.document-row').forEach((row) => row.onclick = (event) => { if (event.target.closest('.document-actions')) return; selectDocument(row.querySelector('.document-item').dataset.id); });
    tree.querySelectorAll('.document-item').forEach((button) => button.onclick = () => selectDocument(button.dataset.id));
    tree.querySelectorAll('.copy-document').forEach((button) => button.onclick = async (event) => { event.stopPropagation(); try { const response = await fetch(`/api/document/${encodeURIComponent(button.dataset.id)}/copy`, { method: 'POST' }); if (!response.ok) throw new Error('无法复制目录'); button.classList.add('is-copied'); button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg>'; button.setAttribute('aria-label', '已复制目录'); button.title = '已复制目录'; window.setTimeout(() => { button.classList.remove('is-copied'); button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="11" height="11" rx="1.5"/><path d="M5 16V5.5A1.5 1.5 0 0 1 6.5 4H17"/></svg>'; button.setAttribute('aria-label', `复制 ${button.closest('.document-row').querySelector('.document-title').textContent} 所在目录`); button.title = '复制所在目录'; }, 1500); } catch (error) { button.title = '复制失败'; window.setTimeout(() => { button.title = '复制所在目录'; }, 1500); } });
    tree.querySelectorAll('.reveal-document').forEach((button) => button.onclick = async (event) => { event.stopPropagation(); try { const response = await fetch(`/api/document/${encodeURIComponent(button.dataset.id)}/reveal`, { method: 'POST' }); if (!response.ok) throw new Error('无法打开目录'); } catch (error) { /* The current PRD remains selected if the operating system cannot open Finder. */ } });
  }
  function selectDocument(id, query = '', restoreScroll = null) {
    const item = allDocuments().find((entry) => entry.id === id); if (!item) return;
    state.selectedId = id; localStorage.setItem('prd-manager.selected', id); renderTree();
    empty.hidden = true; viewer.hidden = false; viewer.src = `/document/${encodeURIComponent(id)}/`;
    viewer.onload = () => { if (restoreScroll && !query) viewer.contentWindow?.scrollTo(restoreScroll.left, restoreScroll.top); if (query) highlight(query); }; document.querySelector('.sidebar').classList.remove('open');
  }
  function setSidebarCollapsed(collapsed) {
    appShell.classList.toggle('sidebar-collapsed', collapsed);
    localStorage.setItem('prd-manager.sidebar-collapsed', String(collapsed));
    const toggle = $('sidebar-toggle');
    toggle.setAttribute('aria-label', collapsed ? '展开目录' : '收起目录');
    toggle.setAttribute('title', collapsed ? '展开目录' : '收起目录');
  }
  function highlight(query) {
    const documentNode = viewer.contentDocument; if (!documentNode || !query) return;
    const walker = documentNode.createTreeWalker(documentNode.body, NodeFilter.SHOW_TEXT);
    const nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode);
    let first = null; const needle = query.toLocaleLowerCase();
    nodes.forEach((node) => { const source = node.nodeValue; const start = source.toLocaleLowerCase().indexOf(needle); if (start < 0 || node.parentElement.closest('script,style')) return; const fragment = documentNode.createDocumentFragment(); fragment.append(source.slice(0, start)); const mark = documentNode.createElement('mark'); mark.textContent = source.slice(start, start + query.length); fragment.append(mark, source.slice(start + query.length)); node.parentNode.replaceChild(fragment, node); first ||= mark; });
    first?.scrollIntoView({ block:'center', behavior:'smooth' });
  }
  const highlightText = (text, query) => { const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); return escape(text).replace(new RegExp(escapedQuery, 'ig'), (match) => `<mark>${match}</mark>`); };
  function contextSnippet(text, query) {
    const source = String(text).replace(/\s+/g, ' ').trim();
    const start = source.toLocaleLowerCase().indexOf(query.toLocaleLowerCase());
    if (start < 0) return '';
    const before = Math.max(0, start - 34), after = Math.min(source.length, start + query.length + 76);
    return `${before ? '...' : ''}${source.slice(before, after)}${after < source.length ? '...' : ''}`;
  }
  function search() {
    const query = input.value.trim();
    state.results = query ? allDocuments().filter((item) => `${item.title} ${item.text}`.toLocaleLowerCase().includes(query.toLocaleLowerCase())) : [];
    state.selectedResult = -1;
    $('clear-search').hidden = !query;
    const summary = $('search-summary'), results = $('search-results'), noResults = Boolean(query && !state.results.length);
    summary.textContent = query ? `找到 ${state.results.length} 份匹配的 PRD` : '';
    summary.classList.toggle('no-results', noResults);
    results.classList.toggle('no-results', noResults);
    results.innerHTML = state.results.map((item, index) => { const snippet = contextSnippet(item.text, query); return `<button class="result" role="option" aria-selected="false" data-index="${index}"><span class="result-title">${highlightText(item.title, query)}</span><span class="result-meta">${highlightText(item.project, query)}</span>${snippet ? `<span class="result-snippet">${highlightText(snippet, query)}</span>` : ''}</button>`; }).join('');
    results.querySelectorAll('.result').forEach((button) => button.onclick = () => openResult(Number(button.dataset.index)));
  }
  function openResult(index) { const item = state.results[index]; if (!item) return; dialog.close(); selectDocument(item.id, input.value.trim()); }
  function openSearch() { dialog.showModal(); input.focus(); input.select(); search(); }
  function loadIndex(payload, restoreScroll = null) { state.index = payload; $('index-status').textContent = `${payload.count} 份`; renderTree(); const choice = allDocuments().some((item) => item.id === state.selectedId) ? state.selectedId : allDocuments()[0]?.id; if (choice) selectDocument(choice, '', restoreScroll); else if (payload.scanning) { empty.querySelector('h1').textContent = '正在整理 PRD'; empty.querySelector('p').textContent = '首次扫描正在后台进行，完成后可点击刷新。'; } else { empty.querySelector('h1').textContent = '尚未找到 PRD'; empty.querySelector('p').textContent = '请确认项目中存在 pm-copilot-outputs/<run-id>/prd.html。'; } }
  async function refresh() { const button = $('refresh-button'); const currentId = state.selectedId; const frameDocument = viewer.contentDocument; const restoreScroll = currentId && frameDocument ? { left: viewer.contentWindow?.scrollX || 0, top: viewer.contentWindow?.scrollY || frameDocument.documentElement?.scrollTop || frameDocument.body?.scrollTop || 0 } : null; button.disabled = true; button.classList.add('is-refreshing'); try { const response = await fetch('/api/refresh', { method:'POST' }); if (!response.ok) throw new Error('刷新失败'); loadIndex(await response.json(), currentId === state.selectedId ? restoreScroll : null); } catch (error) { /* Keep the prior count when refresh cannot complete. */ } finally { button.disabled = false; button.classList.remove('is-refreshing'); } }
  document.addEventListener('keydown', (event) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'f') { event.preventDefault(); openSearch(); } if (!dialog.open) return; if (event.key === 'Escape') { event.preventDefault(); if (!state.composing) dialog.close(); return; } if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); const length = state.results.length; if (!length) return; state.selectedResult = state.selectedResult < 0 ? (event.key === 'ArrowDown' ? 0 : length - 1) : (state.selectedResult + (event.key === 'ArrowDown' ? 1 : length - 1)) % length; $('search-results').querySelectorAll('.result').forEach((element, index) => { const selected = index === state.selectedResult; element.classList.toggle('selected', selected); element.setAttribute('aria-selected', String(selected)); }); } if (event.key === 'Enter' && state.selectedResult >= 0 && !state.composing) { event.preventDefault(); openResult(state.selectedResult); } });
  setSidebarCollapsed(localStorage.getItem('prd-manager.sidebar-collapsed') === 'true');
  input.addEventListener('compositionstart', () => { state.composing = true; }); input.addEventListener('compositionend', () => { state.composing = false; search(); }); input.addEventListener('input', () => { if (!state.composing) search(); }); $('clear-search').onclick = () => { input.value = ''; search(); input.focus(); }; dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); }); dialog.addEventListener('cancel', (event) => { if (state.composing) event.preventDefault(); }); $('refresh-button').onclick = refresh; $('sidebar-toggle').onclick = () => setSidebarCollapsed(!appShell.classList.contains('sidebar-collapsed')); $('menu-button').onclick = () => document.querySelector('.sidebar').classList.toggle('open');
  fetch('/api/index').then((response) => { if (!response.ok) throw new Error('索引加载失败'); return response.json(); }).then(loadIndex).catch(() => { empty.querySelector('h1').textContent = '无法加载 PRD 索引'; empty.querySelector('p').textContent = '请检查本地服务是否正在运行。'; });
})();
