const SUPABASE_URL = window.APP_CONFIG?.SUPABASE_URL || "";
const SUPABASE_ANON_KEY = window.APP_CONFIG?.SUPABASE_ANON_KEY || "";
const PER_PAGE = window.APP_CONFIG?.PER_PAGE || 50;

/* ── Relógio ────────────────────────────────── */
        function tick() {
            document.getElementById('clock').textContent =
                new Date().toLocaleTimeString('pt-BR');
        }
        tick(); setInterval(tick, 1000);

        /* ── Supabase REST ──────────────────────────── */
        const HEADERS = {
            'apikey': SUPABASE_ANON_KEY,
            'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        };

        async function sbFetch(path) {
            const r = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, { headers: HEADERS });
            if (!r.ok) throw new Error(`Supabase HTTP ${r.status}: ${await r.text()}`);
            return r.json();
        }

        /* ── Estado global ──────────────────────────── */
        let airports = [];
        let currentIcao = '';
        let chegadasAll = [];
        let partidasAll = [];
        let chegadasFilt = [];
        let partidasFilt = [];
        let pagChegadas = 1;
        let pagPartidas = 1;
        let sortChegadas = { col: 'chegada_iso', asc: true };
        let sortPartidas = { col: 'partida_iso', asc: true };

        /* ── Helpers ────────────────────────────────── */
        function fmtHora(iso) {
            if (!iso) return '—';
            try {
                return new Date(iso).toLocaleTimeString('pt-BR', {
                    hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo'
                });
            } catch { return iso; }
        }

        function fmtData(str) {
            if (!str) return '—';
            const [y, m, d] = str.split('-');
            return `${d}/${m}/${y}`;
        }

        function todayIso() {
            return new Date().toLocaleDateString('pt-BR', {
                timeZone: 'America/Sao_Paulo'
            }).split('/').reverse().join('-');
        }

        function opBadge(tipo) {
            if (!tipo) return '';
            return tipo.includes('nter')
                ? `<span class="badge badge-inter">✈ Internacional</span>`
                : `<span class="badge badge-domestico">✈ Doméstico</span>`;
        }

        /* ── Selects cascata ────────────────────────── */
        async function loadAirports() {
            try {
                const r = await fetch('data/airports.json');
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                airports = await r.json();

                const states = [...new Set(airports.map(a => a.state))].sort();
                const sel = document.getElementById('sel-state');
                sel.innerHTML = '<option value="">Todos os estados</option>';
                states.forEach(s => {
                    const o = document.createElement('option');
                    o.value = o.textContent = s;
                    sel.appendChild(o);
                });

                document.getElementById('meta-bar').textContent =
                    `${airports.length} aeroportos disponíveis · Dados históricos via Supabase`;
            } catch (e) {
                document.getElementById('meta-bar').textContent =
                    'Erro ao carregar aeroportos: ' + e.message;
            }

            document.getElementById('sel-date').value = todayIso();
        }

        function onStateChange() {
            const state = document.getElementById('sel-state').value;
            const selCity = document.getElementById('sel-city');
            const selAp = document.getElementById('sel-airport');

            selCity.innerHTML = '<option value="">Selecione o município</option>';
            selAp.innerHTML = '<option value="">Selecione o município</option>';
            document.getElementById('btn-refresh').disabled = true;
            chegadasAll = partidasAll = chegadasFilt = partidasFilt = [];
            renderTables();

            if (!state) return;

            const cities = [...new Set(airports.filter(a => a.state === state).map(a => a.city))].sort();
            cities.forEach(c => {
                const o = document.createElement('option');
                o.value = o.textContent = c;
                selCity.appendChild(o);
            });
            if (cities.length === 1) { selCity.value = cities[0]; onCityChange(); }
        }

        function onCityChange() {
            const state = document.getElementById('sel-state').value;
            const city = document.getElementById('sel-city').value;
            const selAp = document.getElementById('sel-airport');

            selAp.innerHTML = '<option value="">Selecione o aeroporto</option>';
            document.getElementById('btn-refresh').disabled = true;
            if (!city) return;

            const aps = airports.filter(a => a.state === state && a.city === city);
            aps.forEach(a => {
                const o = document.createElement('option');
                o.value = a.icao;
                o.textContent = `${a.icao} – ${a.name}`;
                selAp.appendChild(o);
            });
            if (aps.length === 1) { selAp.value = aps[0].icao; onAirportChange(); }
        }

        function onAirportChange() {
            const icao = document.getElementById('sel-airport').value;
            document.getElementById('btn-refresh').disabled = !icao;
            if (icao) loadFlights();
        }

        /* ── Carregar voos do Supabase ──────────────── */
        async function loadFlights() {
            const icao = document.getElementById('sel-airport').value;
            const date = document.getElementById('sel-date').value;
            if (!icao || !date) return;
            currentIcao = icao;

            const btn = document.getElementById('btn-refresh');
            btn.disabled = true; btn.textContent = '…';
            document.getElementById('meta-bar').textContent =
                `Consultando Supabase para ${icao} em ${fmtData(date)}...`;

            try {
                // Os campos usados no filtro batem com o que o Python salva
                const [chegadas, partidas] = await Promise.all([
                    sbFetch(`voos?destino_icao=eq.${icao}&data_referencia=eq.${date}&order=chegada_iso.asc&limit=500`),
                    sbFetch(`voos?origem_icao=eq.${icao}&data_referencia=eq.${date}&order=partida_iso.asc&limit=500`),
                ]);

                chegadasAll = chegadas;
                partidasAll = partidas;
                pagChegadas = pagPartidas = 1;

                // Info cards
                const ap = airports.find(a => a.icao === icao);
                document.getElementById('airport-name').textContent =
                    ap ? `${ap.city} — ${ap.name}` : icao;
                document.getElementById('airport-subtitle').textContent =
                    `ICAO: ${icao}${ap ? ' · ' + ap.state : ''} · Fonte: SIROS/ANAC via Supabase`;

                document.getElementById('card-icao').textContent = icao;
                document.getElementById('card-data').textContent = fmtData(date);
                document.getElementById('card-chegadas').textContent = chegadas.length;
                document.getElementById('card-partidas').textContent = partidas.length;
                document.getElementById('info-cards').style.display = 'flex';

                // Último pipeline (tabela opcional)
                try {
                    const exec = await sbFetch('execucoes?order=concluido_em.desc&limit=1');
                    if (exec?.[0]?.concluido_em) {
                        const dt = new Date(exec[0].concluido_em)
                            .toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
                        document.getElementById('card-pipeline').textContent = dt;
                    }
                } catch { /* tabela execucoes opcional */ }

                document.getElementById('meta-bar').textContent =
                    `Dados de ${fmtData(date)} · ${chegadas.length} chegadas · ${partidas.length} partidas · Clique no cabeçalho para ordenar`;

                populateAirlineFilter();
                applyFilters();

            } catch (e) {
                document.getElementById('meta-bar').textContent =
                    'Erro ao consultar Supabase: ' + e.message;
                chegadasAll = partidasAll = chegadasFilt = partidasFilt = [];
                renderTables();
            } finally {
                btn.disabled = false; btn.textContent = '↺ Atualizar';
            }
        }

        /* ── Filtros ────────────────────────────────── */
        function populateAirlineFilter() {
            const airlines = new Set(
                [...chegadasAll, ...partidasAll].map(f => f.airline).filter(Boolean)
            );
            const sel = document.getElementById('filter-airline');
            const cur = sel.value;
            sel.innerHTML = '<option value="">Todas</option>';
            [...airlines].sort().forEach(a => {
                const o = document.createElement('option');
                o.value = o.textContent = a;
                if (a === cur) o.selected = true;
                sel.appendChild(o);
            });
        }

        function applyFilters() {
            const fAirl = document.getElementById('filter-airline').value;
            const fType = document.getElementById('filter-type').value;

            chegadasFilt = chegadasAll.filter(f =>
                (!fAirl || f.airline === fAirl) &&
                (!fType || f.tipo_operacao === fType)
            );
            partidasFilt = partidasAll.filter(f =>
                (!fAirl || f.airline === fAirl) &&
                (!fType || f.tipo_operacao === fType)
            );
            pagChegadas = pagPartidas = 1;
            renderTables();
        }

        function sortTable(which, col) {
            if (which === 'chegadas') {
                sortChegadas.asc = sortChegadas.col === col ? !sortChegadas.asc : true;
                sortChegadas.col = col;
                chegadasFilt.sort((a, b) => {
                    const v = (a[col] || '') < (b[col] || '') ? -1 : 1;
                    return sortChegadas.asc ? v : -v;
                });
                pagChegadas = 1;
            } else {
                sortPartidas.asc = sortPartidas.col === col ? !sortPartidas.asc : true;
                sortPartidas.col = col;
                partidasFilt.sort((a, b) => {
                    const v = (a[col] || '') < (b[col] || '') ? -1 : 1;
                    return sortPartidas.asc ? v : -v;
                });
                pagPartidas = 1;
            }
            renderTables();
        }

        /* ── Renderização ────────────────────────────── */
        function renderRow(f, kind) {
            const horario = kind === 'arrival'
                ? fmtHora(f.chegada_iso)
                : fmtHora(f.partida_iso);
            const rota = kind === 'arrival'
                ? (f.origem_icao || '—')
                : (f.destino_icao || '—');
            const assentos = f.assentos
                ? `<span class="seats-pill">✦ ${f.assentos}</span>` : '—';

            return `<tr>
        <td class="td-time">${horario}</td>
        <td class="td-flight">${f.airline_icao || ''}${f.numero_voo || '?'}</td>
        <td><span class="airline-pill">${f.airline || '?'}</span></td>
        <td class="td-muted">${f.equipamento || '—'}</td>
        <td>${assentos}</td>
        <td class="td-muted">${rota}</td>
        <td>${opBadge(f.tipo_operacao)}</td>
      </tr>`;
        }

        function renderPagination(id, data, page, setter) {
            const total = Math.ceil(data.length / PER_PAGE) || 1;
            const el = document.getElementById(id);
            if (total <= 1) { el.innerHTML = ''; return; }

            let html = `<span>${data.length} resultados · Página</span>`;
            for (let i = 1; i <= total; i++) {
                html += `<button class="page-btn${i === page ? ' active' : ''}" onclick="${setter}(${i})">${i}</button>`;
            }
            el.innerHTML = html;
        }

        function setPageC(p) { pagChegadas = p; renderTables(); }
        function setPageP(p) { pagPartidas = p; renderTables(); }

        function renderTables() {
            const tbC = document.getElementById('tbody-chegadas');
            const tbP = document.getElementById('tbody-partidas');

            if (!chegadasFilt.length) {
                tbC.innerHTML = '<tr><td colspan="7" class="empty">Nenhuma chegada para o filtro selecionado.</td></tr>';
            } else {
                const slice = chegadasFilt.slice((pagChegadas - 1) * PER_PAGE, pagChegadas * PER_PAGE);
                tbC.innerHTML = slice.map(f => renderRow(f, 'arrival')).join('');
            }

            if (!partidasFilt.length) {
                tbP.innerHTML = '<tr><td colspan="7" class="empty">Nenhuma partida para o filtro selecionado.</td></tr>';
            } else {
                const slice = partidasFilt.slice((pagPartidas - 1) * PER_PAGE, pagPartidas * PER_PAGE);
                tbP.innerHTML = slice.map(f => renderRow(f, 'departure')).join('');
            }

            renderPagination('pag-chegadas', chegadasFilt, pagChegadas, 'setPageC');
            renderPagination('pag-partidas', partidasFilt, pagPartidas, 'setPageP');
        }

        /* ── Init ─────────────────────────────────────── */
        loadAirports();
        setInterval(() => { if (currentIcao) loadFlights(); }, 300_000);
