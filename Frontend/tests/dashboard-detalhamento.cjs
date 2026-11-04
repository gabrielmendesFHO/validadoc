/* Run with NODE_PATH pointing to a Playwright installation and Vite on port 5173. */
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

const baseURL = process.env.DASHBOARD_TEST_URL || 'http://127.0.0.1:5173';
const pessoa = { inscricao_id: 2, candidato: 'Bruno Exemplo', email: 'bruno@example.invalid', status_funil: 'DOCS_PENDENTES', acessou: true, com_dificuldade: true, ausente: false, documentos_com_erro: 1 };
const resumo = { ...pessoa, alertas_dificuldade: 0, pessoas: [
  { membro_id: null, nome: 'Bruno Exemplo', tipo: 'Titular', documentos: [
    { id: 12, solicitado_id: 1, categoria: 'RG', obrigatorio: true, status: 'REJEITADO', motivo: 'Imagem ilegível.' },
    { id: 14, solicitado_id: 2, categoria: 'HOLERITE', obrigatorio: true, status: 'CONCLUIDO', status_auditoria: 'POSSIVEL_DIVERGENCIA', motivo: 'Renda requer conferência.' },
  ] },
  { membro_id: 1, nome: 'Familiar Exemplo', tipo: 'Familiar', documentos: [{ id: null, solicitado_id: 1, categoria: 'RG', obrigatorio: true, status: 'PENDENTE', motivo: null }] },
] };

(async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  let falharLista = false;
  let paginar = false;
  let concluirBuscaLenta;
  const buscaLentaConcluida = new Promise(resolve => { concluirBuscaLenta = resolve; });
  await page.addInitScript(() => {
    localStorage.setItem('access_token', 'token-ficticio-apenas-no-teste');
    localStorage.setItem('usuario', JSON.stringify({ nome_completo: 'Analista Exemplo', perfil: 'ANALISTA' }));
  });
  await page.route('http://127.0.0.1:8000/**', async route => {
    const url = new URL(route.request().url());
    let body;
    if (url.pathname === '/dashboard/metricas') body = { total: paginar ? 21 : 3, com_dificuldade: paginar ? 21 : 3, prontas_auditoria: 0, concluidas: 0, por_status: { DOCS_PENDENTES: paginar ? 21 : 3 } };
    else if (url.pathname === '/inscricoes/dashboard/candidatos') {
      if (falharLista && url.searchParams.get('com_dificuldade') === 'true') return route.fulfill({ status: 503, json: { detail: 'Lista temporariamente indisponível.' } });
      const busca = url.searchParams.get('busca') || '';
      if (busca === 'lenta') {
        await new Promise(resolve => setTimeout(resolve, 800));
        await route.fulfill({ json: { itens: [{ ...pessoa, candidato: 'Resultado antigo' }], total: 1, pagina: 1, por_pagina: 20 } });
        concluirBuscaLenta();
        return;
      }
      const vazio = busca === 'inexistente' || url.searchParams.get('status_funil') === 'CONCLUIDO';
      const todos = paginar ? [...Array.from({ length: 20 }, (_, index) => ({ ...pessoa, inscricao_id: 100 + index, candidato: `Candidato ${index + 1}` })), pessoa] : [pessoa, { ...pessoa, inscricao_id: 3, candidato: 'Carla Exemplo' }, { ...pessoa, inscricao_id: 4, candidato: 'Dani Exemplo' }];
      const filtrados = vazio ? [] : todos.filter(item => !busca || item.candidato.toLowerCase().includes(busca.toLowerCase()) || String(item.inscricao_id) === busca);
      const pagina = Number(url.searchParams.get('pagina') || 1);
      body = { itens: filtrados.slice((pagina - 1) * 20, pagina * 20), total: filtrados.length, pagina, por_pagina: 20 };
    } else if (url.pathname === '/dashboard/inscricoes/2/resumo') body = resumo;
    else if (url.pathname === '/auditoria/2') body = {
      inscricao: { id: 2, status_funil: 'DOCS_PENDENTES', status_geral: 'PENDENTE', inconsistencias: [] },
      candidato: { nome_completo: 'Bruno Exemplo' }, membros: [], documentos: [
        { id: 11, categoria: 'HOLERITE', pessoa: 'Bruno Exemplo', status_processamento: 'CONCLUIDO', nome_arquivo: 'holerite.png', mime_type: 'image/png', arquivo_url: '/documentos/11/arquivo' },
        { id: 12, categoria: 'RG', pessoa: 'Bruno Exemplo', status_processamento: 'REJEITADO', parecer_ia: 'Imagem ilegível.', nome_arquivo: 'rg.png', mime_type: 'image/png', arquivo_url: '/documentos/12/arquivo' },
      ],
    };
    else if (url.pathname.endsWith('/arquivo')) return route.fulfill({ status: 404 });
    else return route.fulfill({ status: 404, json: {} });
    return route.fulfill({ json: body });
  });
  try {
    const reviewCase = process.env.DASHBOARD_REVIEW_CASE;
    if (reviewCase) {
      if (reviewCase === 'documento') {
        await page.goto(`${baseURL}/auditoria/2?documento=999`);
        await page.getByRole('alert').filter({ hasText: 'Documento solicitado não está disponível' }).waitFor({ timeout: 5000 });
        assert.equal(await page.locator('.audit-document-option[aria-pressed="true"]').count(), 0);
        await page.getByRole('button', { name: /HOLERITE|Holerite/ }).click();
        await page.locator('.audit-document-option[aria-pressed="true"]').waitFor();
      } else if (reviewCase === 'pagina') {
        await page.goto(`${baseURL}/dashboard?resumo=dificuldade&resumo_pagina=2`);
        const dialog = page.getByRole('dialog');
        await dialog.getByText('Nenhuma inscrição encontrada.', { exact: true }).waitFor();
        await dialog.getByText('0–0 de 3', { exact: true }).waitFor({ timeout: 5000 });
      } else {
        await page.goto(`${baseURL}/dashboard?resumo=${reviewCase === 'foco' ? 'DOCS_PENDENTES' : 'dificuldade'}&inscricao=2`);
        const dialog = page.getByRole('dialog');
        await dialog.getByText('Imagem ilegível.', { exact: true }).waitFor();
        if (reviewCase === 'divergencia') {
          await dialog.getByText('Possível divergência', { exact: true }).waitFor({ timeout: 5000 });
          assert.equal(await dialog.locator('.drill-document').filter({ hasText: 'Holerite' }).locator('.success').count(), 0);
        } else if (reviewCase === 'privacidade') {
          await dialog.getByRole('textbox', { name: 'Buscar no resumo' }).fill('Bruno');
          await dialog.getByText('inscrição na busca', { exact: true }).waitFor();
          await dialog.getByRole('button', { name: /Ver resumo de Bruno Exemplo/ }).click();
          await dialog.getByRole('link', { name: /Abrir RG/ }).waitFor();
          assert.equal(decodeURIComponent(page.url()).includes('Bruno'), false);
          await dialog.getByRole('link', { name: /Abrir RG/ }).click();
          assert.equal(decodeURIComponent(page.url()).includes('Bruno'), false);
          await page.getByRole('button', { name: 'Voltar ao resumo' }).click();
          assert.equal(await dialog.getByRole('textbox', { name: 'Buscar no resumo' }).inputValue(), 'Bruno');
        } else if (reviewCase === 'foco') {
          await dialog.getByRole('link', { name: /Abrir RG/ }).click();
          await page.getByRole('button', { name: 'Voltar ao resumo' }).click();
          await page.getByRole('button', { name: /Ver inscrições em Documentos/ }).waitFor({ state: 'attached' });
          await page.keyboard.press('Escape');
          await dialog.waitFor({ state: 'hidden' });
          assert.equal(await page.getByRole('button', { name: /Ver inscrições em Documentos/ }).evaluate(element => element === document.activeElement), true);
        }
      }
      console.log(`PASS revisão: ${reviewCase}`);
      return;
    }
    await page.goto(`${baseURL}/dashboard`);
    const card = page.getByRole('button', { name: /Com dificuldade/ });
    await card.click();
    const drawer = page.getByRole('dialog', { name: /Com dificuldade/ });
    await drawer.waitFor({ timeout: 5000 });
    await drawer.getByRole('textbox', { name: 'Buscar no resumo' }).fill('Bruno');
    await drawer.getByRole('button', { name: /Ver resumo de Bruno Exemplo/ }).click();
    await drawer.getByText('Imagem ilegível.', { exact: true }).waitFor();
    await drawer.getByText('Familiar Exemplo', { exact: true }).waitFor();
    await drawer.getByRole('link', { name: /Abrir RG/ }).click();
    await page.waitForURL(/\/auditoria\/2\?/);
    await page.locator('.audit-document-option[aria-pressed="true"]').filter({ hasText: 'RG' }).waitFor();
    await page.getByRole('button', { name: 'Voltar ao resumo' }).click();
    await drawer.waitFor();
    assert.equal(await drawer.getByRole('textbox', { name: 'Buscar no resumo' }).inputValue(), 'Bruno');
    await drawer.getByText('Imagem ilegível.', { exact: true }).waitFor();
    await page.keyboard.press('Escape');
    await drawer.waitFor({ state: 'hidden' });
    assert.equal(await drawer.count(), 0);
    assert.equal(await card.evaluate(element => element === document.activeElement), true);

    await page.getByRole('button', { name: /Ver inscrições em Documentos/ }).click();
    await page.getByRole('dialog', { name: /Documentos/ }).waitFor();
    await page.keyboard.press('Escape');
    await page.getByRole('dialog').waitFor({ state: 'hidden' });

    await page.locator('.recharts-bar-rectangle').first().click();
    await page.getByRole('dialog', { name: /Documentos/ }).waitFor();
    await page.keyboard.press('Escape');
    await page.getByRole('dialog').waitFor({ state: 'hidden' });

    await page.setViewportSize({ width: 390, height: 844 });
    await card.click();
    await drawer.getByRole('button', { name: /Ver resumo de Bruno Exemplo/ }).click();
    await drawer.getByText('Imagem ilegível.', { exact: true }).waitFor();
    assert.equal(await drawer.evaluate(element => element.scrollWidth <= element.clientWidth), true);
    await page.screenshot({ path: process.env.DASHBOARD_SCREENSHOT || '../outputs/dashboard-detalhamento-mobile.png', fullPage: false });
    await drawer.getByRole('textbox', { name: 'Buscar no resumo' }).fill('inexistente');
    await drawer.getByText('Nenhuma inscrição encontrada.', { exact: true }).waitFor();
    await page.keyboard.press('Escape');
    falharLista = true;
    await card.click();
    await drawer.getByRole('button', { name: 'Tentar novamente' }).waitFor();
    falharLista = false;
    await drawer.getByRole('button', { name: 'Tentar novamente' }).click();
    await drawer.getByRole('button', { name: /Ver resumo de Bruno Exemplo/ }).waitFor();

    await Promise.all([
      page.waitForRequest(request => request.url().includes('busca=lenta')),
      drawer.getByRole('textbox', { name: 'Buscar no resumo' }).fill('lenta'),
    ]);
    await drawer.getByRole('textbox', { name: 'Buscar no resumo' }).fill('inexistente');
    await drawer.getByText('Nenhuma inscrição encontrada.', { exact: true }).waitFor();
    await buscaLentaConcluida;
    assert.equal(await drawer.getByText('Resultado antigo', { exact: true }).count(), 0);
    await drawer.getByText('Nenhuma inscrição encontrada.', { exact: true }).waitFor();

    paginar = true;
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(`${baseURL}/dashboard`);
    await card.click();
    await drawer.getByRole('button', { name: 'Próxima página do resumo' }).click();
    await drawer.getByRole('button', { name: /Ver resumo de Bruno Exemplo/ }).click();
    await drawer.getByRole('link', { name: /Abrir RG/ }).click();
    await page.getByRole('button', { name: 'Voltar ao resumo' }).click();
    await drawer.getByText('Página 2', { exact: true }).waitFor();
    await drawer.getByText('Imagem ilegível.', { exact: true }).waitFor();
    await page.screenshot({ path: '../outputs/dashboard-detalhamento-desktop.png', fullPage: false });
    await page.keyboard.press('Escape');
    await page.getByRole('dialog').waitFor({ state: 'hidden' });
    await page.getByRole('button', { name: /Concluídas/ }).click();
    await page.getByRole('dialog', { name: 'Concluído' }).getByText('Nenhuma inscrição encontrada.', { exact: true }).waitFor();
    assert.deepEqual(errors, []);
    console.log('PASS: indicador, resumo, documento selecionado, retorno com busca/página, Escape/foco, etapa/barra, celular, vazio, nova tentativa e resposta atrasada.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
