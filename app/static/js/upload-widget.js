/**
 * uploadWidget — widget reutilizável de upload de imagem.
 *
 * uploadWidget.init(containerId, opcoes)
 *   forma:    'circulo' | 'quadrado' (default: 'circulo')
 *   urlAtual: URL da foto atual (string) ou null
 *   onUpload: async function(file) => string (URL)
 *             Se fornecido, faz upload automático ao selecionar o arquivo.
 *             Se omitido, armazena o arquivo para upload manual via getFile().
 *
 * uploadWidget.getFile(id)  → File | null   (arquivo pendente p/ upload manual)
 * uploadWidget.getUrl(id)   → string | null (URL atual após upload)
 * uploadWidget.setUrl(id, url)              (atualizar URL externamente)
 * uploadWidget.reset(id)                    (limpar estado e preview)
 */
(function () {
  'use strict';

  // ── CSS injetado uma vez ───────────────────────────────────────
  const _CSS = `
    .uw-container { display:flex; align-items:center; gap:14px; }
    .uw-preview {
      overflow:hidden; background:#1e1e1e; border:2px solid #2d2d2d;
      display:flex; align-items:center; justify-content:center;
      cursor:pointer; flex-shrink:0; transition:border-color .15s;
    }
    .uw-preview:hover { border-color:var(--cor-primaria,#BA7517); }
    .uw-preview img { width:100%; height:100%; object-fit:cover; }
    .uw-preview svg { pointer-events:none; }
    .uw-btn {
      padding:7px 14px; background:none; border:1.5px solid #333; color:#888;
      border-radius:7px; font-size:13px; cursor:pointer; font-family:inherit;
      transition:all .15s; white-space:nowrap;
    }
    .uw-btn:hover { border-color:var(--cor-primaria,#BA7517); color:var(--cor-primaria,#BA7517); }
    .uw-status { font-size:11px; margin-top:5px; min-height:16px; }
  `;

  if (!document.getElementById('_uw_style')) {
    const s = document.createElement('style');
    s.id = '_uw_style';
    s.textContent = _CSS;
    document.head.appendChild(s);
  }

  // ── Estado ─────────────────────────────────────────────────────
  const _st = {};

  // ── Ícone placeholder ──────────────────────────────────────────
  function _iconeSvg() {
    return `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#444" stroke-width="1.5">
      <rect x="3" y="3" width="18" height="18" rx="3"/>
      <circle cx="8.5" cy="8.5" r="1.5" fill="#444" stroke="none"/>
      <path d="m21 15-5-5-7 7"/>
    </svg>`;
  }

  // ── Render ─────────────────────────────────────────────────────
  function _render(id, forma, url) {
    const el = document.getElementById(id);
    if (!el) return;
    const isCircle = forma === 'circulo';
    const size = isCircle ? 72 : 80;
    const radius = isCircle ? '50%' : '10px';
    el.innerHTML = `
      <div class="uw-container">
        <div class="uw-preview" id="${id}_prev"
             style="width:${size}px;height:${size}px;border-radius:${radius}"
             onclick="uploadWidget._click('${id}')" title="Clique para alterar">
          ${url ? `<img src="${url}" alt="">` : _iconeSvg()}
        </div>
        <div>
          <input type="file" id="${id}_inp" accept="image/*" style="display:none"
                 onchange="uploadWidget._onChange('${id}')">
          <button type="button" class="uw-btn" onclick="uploadWidget._click('${id}')">
            📷 Escolher foto
          </button>
          <div class="uw-status" id="${id}_st"></div>
        </div>
      </div>`;
  }

  // ── Init ───────────────────────────────────────────────────────
  function init(id, { forma = 'circulo', urlAtual = null, onUpload = null } = {}) {
    _st[id] = { url: urlAtual, file: null, onUpload, forma };
    _render(id, forma, urlAtual);
  }

  // ── Clique no input ────────────────────────────────────────────
  function _click(id) {
    document.getElementById(id + '_inp')?.click();
  }

  // ── Arquivo selecionado ────────────────────────────────────────
  async function _onChange(id) {
    const inp  = document.getElementById(id + '_inp');
    const file = inp?.files[0];
    if (!file) return;

    const st  = _st[id];
    const prev = document.getElementById(id + '_prev');
    const stat = document.getElementById(id + '_st');

    st.file = file;

    // Preview local imediato via FileReader
    const reader = new FileReader();
    reader.onload = e => {
      if (prev) prev.innerHTML = `<img src="${e.target.result}" alt="">`;
    };
    reader.readAsDataURL(file);

    // Upload automático se onUpload fornecido
    if (st.onUpload) {
      if (stat) { stat.textContent = '⏳ Enviando…'; stat.style.color = '#888'; }
      try {
        const result = await st.onUpload(file);
        const url = (typeof result === 'string') ? result : result?.url;
        st.url  = url;
        st.file = null;
        if (stat) { stat.textContent = '✓ Salvo'; stat.style.color = '#4ade80'; }
        setTimeout(() => { if (stat) stat.textContent = ''; }, 3000);
      } catch(err) {
        if (stat) { stat.textContent = '✗ ' + err.message; stat.style.color = '#f87171'; }
      }
    }
  }

  // ── Reset ──────────────────────────────────────────────────────
  function reset(id) {
    const st = _st[id];
    if (!st) return;
    st.file = null;
    st.url  = null;
    _render(id, st.forma, null);
  }

  // ── API pública ────────────────────────────────────────────────
  window.uploadWidget = {
    init,
    reset,
    _click,
    _onChange,
    getFile: id => _st[id]?.file  || null,
    getUrl:  id => _st[id]?.url   || null,
    setUrl:  (id, url) => { if (_st[id]) { _st[id].url = url; _st[id].file = null; } },
  };
})();
