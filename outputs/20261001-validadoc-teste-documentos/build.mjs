import fs from 'node:fs/promises';
import { Workbook, SpreadsheetFile, FileBlob } from '@oai/artifact-tool';

const outputDir = new URL('.', import.meta.url).pathname.replace(/^\/(?=[A-Za-z]:)/, '');
if (process.argv.includes('--update-results')) {
  const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(`${outputDir}Plano_de_Testes_ValidaDoc.xlsx`));
  const sheet = wb.worksheets.getItem('Testes');
  const before = await wb.render({sheetName:'Testes',range:'H10:M17',scale:1,format:'png'});
  await fs.writeFile(`${outputDir}antes-reteste.png`,new Uint8Array(await before.arrayBuffer()));
  const results = JSON.parse(await fs.readFile(`${outputDir}resultados_web_20261002.json`,'utf8')).casos;
  sheet.getRange('A3').values=[['Jornada de documentos e auditoria. Reteste web de 02/10/2026.']];
  sheet.getRange('A7').values=[['Base automatizada: 77 testes aprovados. Resultados de API e navegador identificados nas evidências.']];
  for (let row=11;row<=43;row++) {
    const id=sheet.getRange(`A${row}`).values[0][0];
    const oldDate=sheet.getRange(`L${row}`).values[0][0];
    if (typeof oldDate==='string' && /^test_.*\.py$/.test(oldDate)) {
      sheet.getRange(`M${row}`).values=[[oldDate]];
      sheet.getRange(`L${row}`).values=[[null]];
    }
    if(results[id]) {
      const [status,observed,evidence]=results[id];
      sheet.getRange(`H${row}:L${row}`).values=[[status,observed,evidence,'Codex',new Date(2026,9,2,12)]];
      sheet.getRange(`H${row}:M${row}`).format.wrapText=true;
      sheet.getRange(`H${row}:M${row}`).format.rowHeight=78;
    }
  }
  sheet.getRange('M17').values=[['test_validacao_documental.py']];
  sheet.getRange('E32').values=[['F02']];
  sheet.getRange('E34').values=[['F01,F06']];
  const inventory=wb.worksheets.getItem('Arquivos');
  inventory.getRange('I9:I14').values=[
    ['CNH PDF enviada pela web. CPF inválido inicial levou à correção e novo processamento válido.'],
    ['Comprovante emitido há 191 dias. Alerta de validade e revisão manual confirmados.'],
    ['RG frente concluído na etapa KYC pela web.'],
    ['RG verso concluído no reteste, após corrigir CPF extraído da CNH.'],
    ['Usada no cadastro familiar e no teste de documento de outra pessoa, rejeitado no campo do titular.'],
    ['CNH PDF concluída no campo do familiar. Identidade consistente na auditoria.'],
  ];
  inventory.getRange('A6').values=[['F02 atende ao caso de comprovante vencido. Ainda faltam holerites e comprovante recente.']];
  inventory.getRange('G17:I17').values=[['Validade acima de 90 dias','Não necessário','F02 já atende ao cenário de comprovante vencido.']];
  inventory.getRange('I9:I14').format.rowHeight=65;
  wb.recalculate();
  for(const [sheetName,range,name] of [
    ['Testes','H10:M17','reteste-resultados.png'],
    ['Testes','H27:M35','reteste-auditoria.png'],
    ['Testes','A2:L8','reteste-resumo.png'],
    ['Arquivos','G8:I17','reteste-arquivos.png'],
  ]) {
    const preview=await wb.render({sheetName,range,scale:1,format:'png'});
    await fs.writeFile(`${outputDir}${name}`,new Uint8Array(await preview.arrayBuffer()));
  }
  console.log((await wb.inspect({kind:'table',range:'Testes!A5:L6',include:'values,formulas',tableMaxRows:2,tableMaxCols:12})).ndjson);
  console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:20}})).ndjson);
  await (await SpreadsheetFile.exportXlsx(wb)).save(`${outputDir}Plano_de_Testes_ValidaDoc.xlsx`);
  process.exit(0);
}
const workbook = Workbook.create();
const testsSheet = workbook.worksheets.add('Testes');
const filesSheet = workbook.worksheets.add('Arquivos');
testsSheet.showGridLines = false;
filesSheet.showGridLines = false;

const cases = [
  ['T01','P0','Acesso e KYC','Abrir inscrição de teste','—','Entrar como candidato de teste e abrir a jornada.','Inscrição e etapa atual aparecem sem dados de outra pessoa.','Não executado','','','','',''],
  ['T02','P0','Acesso e KYC','Bloquear etapa antes do KYC','F01','Antes de validar a identidade, tentar enviar documento familiar ou de residência.','Sistema bloqueia o avanço e informa que o KYC deve ser concluído.','Não executado','','','','test_bloqueio_jornada.py'],
  ['T03','P0','Acesso e KYC','Enviar RG frente','F03','Enviar F03 no campo RG do titular e registrar o ID retornado.','Documento termina em CONCLUIDO com dados extraídos; erros ficam registrados.','Não executado','','','',''],
  ['T04','P1','Acesso e KYC','Conferir RG verso','F04','Se a inscrição pedir RG_VERSO, enviar F04 no campo correspondente.','Lado do RG é identificado e não é confundido com a frente.','Não executado','','','',''],
  ['T05','P0','Acesso e KYC','Validar CNH legível','F01 ou F05','Enviar uma CNH no campo do titular; acompanhar status e continuar a jornada.','CNH válida é concluída e libera o cadastro familiar.','Não executado','','','',''],
  ['T06','P0','Processamento','Acompanhar processamento assíncrono','F01','Após upload, consultar a tela/status até o término.','Status deixa PROCESSANDO_IA; resultado e mensagem ficam visíveis.','Não executado','','','',''],
  ['T07','P0','Processamento','Documento de outra pessoa no campo do titular','F05','Em inscrição do Pack A, enviar CNH do Pack B como identidade do titular.','Documento é REJEITADO ou sinalizado para revisão; não confirma a identidade errada.','Não executado','','','','test_validacao_documental.py'],
  ['T08','P1','Processamento','Imagem de baixa qualidade','F07 convertido ou F10','Enviar imagem ruim em formato aceito, no campo de identidade.','Falha ou aviso legível; não há aprovação silenciosa de dados incertos.','Não executado','','','','test_validacao_documental.py'],
  ['T09','P0','Upload','Formato HEIF não aceito','F07','Tentar enviar F07 sem converter.','HTTP 400 e mensagem de formato não suportado; nenhum documento é criado.','Não executado','','','',''],
  ['T10','P1','Upload','Arquivo vazio','F11','Enviar arquivo JPG ou PDF vazio.','HTTP 400 e mensagem de arquivo vazio; nenhum processamento inicia.','Não executado','','','',''],
  ['T11','P0','Upload','Arquivo acima de 15 MB','F12','Enviar arquivo permitido com mais de 15 MB.','HTTP 413; limite de 15 MB informado, sem salvar o arquivo.','Não executado','','','',''],
  ['T12','P0','Upload','Mesmo arquivo em outro campo','F01','Enviar F01 em um campo e repetir os mesmos bytes em outro da mesma inscrição.','Segundo envio bloqueado como duplicado (HTTP 422).','Não executado','','','','test_upload_duplicados.py'],
  ['T13','P1','Upload','Reenvio no mesmo campo','F01','Reenviar F01 no mesmo campo da mesma inscrição.','Reenvio é aceito para nova tentativa; histórico e status permanecem coerentes.','Não executado','','','','test_upload_duplicados.py'],
  ['T14','P0','Acesso','Candidato não acessa inscrição alheia','F01','Com candidato A, tentar upload na inscrição do candidato B.','HTTP 403; arquivo não é salvo na inscrição alheia.','Não executado','','','',''],
  ['T15','P0','Acesso','Familiar de outra inscrição','F01','Enviar documento usando membro_id de outra inscrição.','HTTP 400; arquivo não é associado ao familiar incorreto.','Não executado','','','','test_upload_duplicados.py'],
  ['T16','P1','Acesso','Tipo solicitado de outro processo','F01','Usar solicitado_id que não pertence ao processo da inscrição.','HTTP 400; arquivo não é associado ao processo errado.','Não executado','','','',''],
  ['T17','P0','Família','Cadastrar e editar CPF do familiar','—','Cadastrar familiar com CPF controlado e depois editar o campo.','CPF fica editável e persiste; não é substituído silenciosamente pela IA.','Não executado','','','',''],
  ['T18','P0','Família','Identidade do familiar consistente','F05','Cadastrar familiar correspondente e enviar identidade no campo dele.','Nome e CPF extraídos são confrontados com o cadastro correto.','Não executado','','','','test_regras_negocio.py'],
  ['T19','P0','Família','CPF divergente do familiar','F05','Cadastrar CPF controlado diferente do documento e auditar.','REVISAO_MANUAL com inconsistência de CPF; não resulta em APTO.','Não executado','','','','test_regras_negocio.py'],
  ['T20','P0','Família','CPF ausente do familiar','F05','Cadastrar familiar sem CPF e auditar após documentos necessários.','REVISAO_MANUAL; ausência de CPF não confirma identidade.','Não executado','','','','test_regras_negocio.py'],
  ['T21','P0','Documentos','Comprovante de residência recente','F02','Enviar comprovante com emissão de até 90 dias.','Data e categoria são extraídas; documento pode seguir para auditoria.','Não executado','','','','test_validacao_documental.py'],
  ['T22','P0','Documentos','Comprovante vencido','F09','Enviar comprovante com emissão superior a 90 dias.','Alerta de validade e REVISAO_MANUAL na auditoria.','Não executado','','','','test_regras_negocio.py'],
  ['T23','P0','Auditoria','Documento obrigatório ausente','—','Deixar um documento obrigatório sem envio concluído e solicitar auditoria.','Status PENDENTE com lista dos documentos faltantes.','Não executado','','','',''],
  ['T24','P0','Auditoria','Concluir envio com todos os obrigatórios','F01,F02,F03','Enviar todos os tipos obrigatórios configurados, aguardar CONCLUIDO e concluir etapa.','Inscrição entra em PRONTO_AUDITORIA.','Não executado','','','',''],
  ['T25','P0','Auditoria','Conferência lado a lado pelo analista','F01,F02,F03','Abrir a inscrição como analista e comparar arquivo, dados extraídos e cadastrados.','Arquivo e dados da pessoa/categoria correta aparecem juntos, com alertas.','Não executado','','','','test_operacional.py'],
  ['T26','P0','Renda','Extrair renda de holerite','F08','Enviar holerite controlado de candidato e familiar; auditar.','Renda bruta é extraída e usada no cálculo per capita; resultado é rastreável.','Não executado','','','','test_regras_negocio.py'],
  ['T27','P0','Renda','Renda exatamente no teto','F08','Preparar renda e composição familiar que deem exatamente o limite; auditar.','APTO somente se os demais dados forem consistentes.','Não executado','','','','test_regras_negocio.py'],
  ['T28','P0','Renda','Renda acima do teto com dados consistentes','F08','Preparar renda per capita acima do limite, sem inconsistências; auditar.','NAO_APTO com renda calculada e justificativa do limite.','Não executado','','','','test_regras_negocio.py'],
  ['T29','P0','Renda','Renda acima do teto com divergência','F08,F05','Introduzir divergência de identidade e renda acima do limite; auditar.','REVISAO_MANUAL prevalece sobre NAO_APTO; alerta de renda permanece visível.','Não executado','','','','test_regras_negocio.py'],
  ['T30','P1','Auditoria','Parecer manual do analista','—','Em inscrição de revisão, registrar aprovação ou rejeição com justificativa.','Decisão, justificativa e estado final persistem e aparecem na consulta.','Não executado','','','','test_operacional.py'],
  ['T31','P0','Acesso','Candidato não acessa auditoria interna','—','Com perfil candidato, abrir detalhe de auditoria ou registrar parecer.','Acesso negado; não há exposição de dados nem alteração do parecer.','Não executado','','','',''],
  ['T32','P0','Acesso','Baixar documento de outra inscrição','F01','Com candidato B, tentar baixar arquivo enviado por candidato A.','HTTP 403; conteúdo não é entregue.','Não executado','','','',''],
  ['T33','P1','Processamento','Falha da API de extração','F01','Simular falha do provedor em ambiente de teste e consultar status.','Documento termina em ERRO_EXTRACAO com mensagem; não fica preso em PROCESSANDO_IA.','Não executado','','','',''],
];

const fileRows = [
  ['F01','Pack A','CNH_DIG_GA.pdf','CNH','.pdf',285,'Identidade do titular','Disponível','Documento existente; conteúdo ainda não foi enviado à IA.'],
  ['F02','Pack A','RES_GA.jpg','RESIDENCIA','.jpg',899,'Comprovante de residência','Disponível','Conferir data de emissão antes de afirmar que está dentro de 90 dias.'],
  ['F03','Pack A','RG_FRENTE_GA.jpg','RG','.jpg',2754,'RG frente','Disponível',''],
  ['F04','Pack A','RG_VERSO_GA.jpg','RG_VERSO','.jpg',355,'RG verso','Disponível','Depende de RG_VERSO estar configurado no processo.'],
  ['F05','Pack B','CNH_ZERO_BOA.jpg','CNH','.jpg',3526,'Identidade de outra pessoa / familiar','Disponível','Usar somente com inscrição controlada apropriada.'],
  ['F06','Pack B','CNH_ZERO_DIG.pdf','CNH','.pdf',284,'CNH digital alternativa','Disponível',''],
  ['F07','Pack B','CNH_ZERO_RUIM.heif','CNH','.heif',1705,'Formato não aceito','Disponível','HEIF não está nas extensões permitidas; converter uma cópia para testar legibilidade.'],
  ['F08','A preparar','','HOLERITE','',null,'Renda e limites','Faltando','Essencial para os cenários financeiros completos.'],
  ['F09','A preparar','','RESIDENCIA','',null,'Validade acima de 90 dias','Faltando','Usar documento fictício ou autorizado com data controlada.'],
  ['F10','A preparar','','RG/CNH','',null,'Baixa legibilidade em formato aceito','Faltando','Pode ser cópia degradada de documento fictício.'],
  ['F11','A preparar','','JPG/PDF','',0,'Arquivo vazio','Faltando','Criar arquivo de zero byte apenas para rejeição no upload.'],
  ['F12','A preparar','','JPG/PDF','',null,'Arquivo acima de 15 MB','Faltando','Criar arquivo sintético; será rejeitado antes da IA.'],
];

const navy = '#12345B';
const dark = '#0B243D';
const blue = '#EAF2FA';
const amber = '#FFF2CC';
const light = '#F4F7FB';
const font = 'Arial';

testsSheet.getRange('A2').values = [['Plano de validação do ValidaDoc']];
testsSheet.getRange('A3').values = [['Jornada de documentos e auditoria | rodada inicial de 01/10/2026']];
testsSheet.getRange('A5').values = [['Casos']];
testsSheet.getRange('C5').values = [['Aprovados']];
testsSheet.getRange('F5').values = [['Falhas']];
testsSheet.getRange('H5').values = [['Bloqueados']];
testsSheet.getRange('K5').values = [['Não executados']];
const first = 11;
const last = first + cases.length - 1;
testsSheet.getRange('A6').formulas = [[`=COUNTA(A${first}:A${last})`]];
testsSheet.getRange('C6').formulas = [[`=COUNTIFS(H${first}:H${last},"Aprovado")`]];
testsSheet.getRange('F6').formulas = [[`=COUNTIFS(H${first}:H${last},"Falhou")`]];
testsSheet.getRange('H6').formulas = [[`=COUNTIFS(H${first}:H${last},"Bloqueado")`]];
testsSheet.getRange('K6').formulas = [[`=COUNTIFS(H${first}:H${last},"Não executado")`]];
testsSheet.getRange('A7').values = [['Base automatizada: 57 testes aprovados em 01/10/2026. Os resultados manuais abaixo ainda não foram executados.']];
testsSheet.getRange('A8').values = [['Preencha Status, Resultado observado, Evidência, Responsável e Data. Registre IDs e mensagens; não copie CPF nem imagens para esta planilha.']];
testsSheet.getRange('A10:M10').values = [[
  'ID','Prioridade','Etapa','Cenário','Arquivo(s)','Procedimento','Resultado esperado','Status','Resultado observado','Evidência','Responsável','Data','Teste no código'
]];
testsSheet.getRange(`A${first}:M${last}`).values = cases;

const outcomes = {
  T03:['Falhou','RG frente recebeu HTTP 202, mas terminou em ERRO_EXTRACAO.','Rodada API isolada com F03; doc 1.'],
  T05:['Falhou','CNH PDF recebeu HTTP 202, mas terminou em ERRO_EXTRACAO.','Repetição isolada com F01; doc 1.'],
  T07:['Falhou','A regra aceitou como sucesso uma CNH sintética com nome e CPF diferentes do titular. Teste com packs reais foi inconclusivo por falhas da IA.','Validação direta da regra: aceito=True, nível=sucesso.'],
  T09:['Aprovado','HEIF recusado antes do processamento (HTTP 400).','Rodada API isolada com F07.'],
  T10:['Aprovado','Arquivo vazio recusado (HTTP 400).','Rodada API isolada com 0 byte.'],
  T11:['Aprovado','Arquivo acima de 15 MB recusado (HTTP 413).','Rodada API isolada com arquivo sintético.'],
  T12:['Aprovado','Mesmo conteúdo em outro campo recusado (HTTP 422).','Rodada API isolada com F03.'],
  T14:['Aprovado','Candidato B não enviou arquivo à inscrição A (HTTP 403).','Rodada API isolada com F03.'],
  T15:['Aprovado','Familiar de outra inscrição recusado (HTTP 400).','Rodada API isolada com F03.'],
  T23:['Aprovado','Auditoria retornou PENDENTE com documentos obrigatórios faltantes.','Rodada API isolada; HTTP 200.'],
  T31:['Aprovado','Candidato não acessou rota de auditoria (HTTP 403).','Rodada API isolada.'],
  T32:['Aprovado','Candidato B não baixou arquivo da inscrição A (HTTP 403).','Rodada API isolada; doc 1.'],
};
for (const [id,[status,observed,evidence]] of Object.entries(outcomes)) {
  const row = first + cases.findIndex((entry) => entry[0] === id);
  testsSheet.getRange(`H${row}:K${row}`).values = [[status,observed,evidence,'Codex']];
  testsSheet.getRange(`L${row}`).values = [[new Date('2026-10-01T12:00:00')]];
}
for (const [id,observed,evidence] of [
  ['T16','ID inexistente recebeu HTTP 400; ID de outro processo ainda não foi testado.','Rodada API isolada com F03.'],
  ['T21','Comprovante terminou em CONCLUIDO; data extraída e limite de 90 dias ainda não foram conferidos.','Rodada API isolada com F02; doc 3.'],
  ['T25','API de auditoria retornou 200 e três documentos; interface lado a lado ainda não foi conferida.','Rodada API isolada; validação visual pendente.'],
]) {
  const row = first + cases.findIndex((entry) => entry[0] === id);
  testsSheet.getRange(`I${row}:J${row}`).values = [[observed,evidence]];
}

testsSheet.getRange(`A2:M${last}`).format.font = {name:font,size:10,color:dark};
testsSheet.getRange('A2').format.font = {name:font,size:15,bold:true,color:navy};
testsSheet.getRange('A3').format.font = {name:font,size:10,italic:true,color:'#5B6B7B'};
testsSheet.getRange('A5:L6').format.fill = blue;
testsSheet.getRange('A5:L5').format.font = {name:font,size:10,bold:true,color:navy};
for (const col of ['A','C','F','H','K']) testsSheet.getRange(`${col}6`).format.font = {name:font,size:13,bold:true,color:navy};
testsSheet.getRange('A7:A8').format.font = {name:font,size:10,color:'#5B6B7B'};
testsSheet.getRange('A10:M10').format = {fill:navy,font:{name:font,size:10,bold:true,color:'#FFFFFF'},rowHeight:32,verticalAlignment:'center',wrapText:true};
testsSheet.getRange(`A${first}:M${last}`).format.rowHeight = 52;
testsSheet.getRange(`A${first}:M${last}`).format.verticalAlignment = 'center';
testsSheet.getRange(`D${first}:G${last}`).format.wrapText = true;
testsSheet.getRange(`I${first}:J${last}`).format.wrapText = true;
testsSheet.getRange(`H${first}:L${last}`).format.fill = amber;
testsSheet.getRange(`L${first}:L${last}`).setNumberFormat('dd/mm/yyyy');
testsSheet.getRange(`H${first}:H${last}`).dataValidation = {rule:{type:'list',values:['Não executado','Aprovado','Falhou','Bloqueado','Não se aplica']}};
testsSheet.getRange(`H${first}:H${last}`).conditionalFormats.add('containsText',{text:'Falhou',format:{fill:'#FDE8E8',font:{bold:true,color:'#A12222'}}});
testsSheet.getRange(`H${first}:H${last}`).conditionalFormats.add('containsText',{text:'Bloqueado',format:{fill:'#FFF0CC',font:{bold:true,color:'#8C5A00'}}});
testsSheet.getRange(`H${first}:H${last}`).conditionalFormats.add('containsText',{text:'Aprovado',format:{fill:'#E7F5EA',font:{bold:true,color:'#1E6A37'}}});
const widths = {A:8,B:12,C:18,D:35,E:17,F:62,G:62,H:17,I:42,J:34,K:17,L:14,M:27};
for (const [col,width] of Object.entries(widths)) testsSheet.getRange(`${col}:${col}`).format.columnWidth = width;
const casesTable = testsSheet.tables.add(`A10:M${last}`,true,'CasosValidaDoc');
casesTable.style = 'TableStyleMedium2';
testsSheet.freezePanes.freezeRows(10);
testsSheet.freezePanes.freezeColumns(4);

filesSheet.getRange('A2').values = [['Inventário dos arquivos controlados']];
filesSheet.getRange('A3').values = [['Os sete arquivos existentes foram inventariados por nome, formato e tamanho; conteúdo e dados pessoais não foram copiados.']];
filesSheet.getRange('A5').values = [['Pack A: doc-gabriel-mendes | Pack B: doc-gustavo-paes']];
filesSheet.getRange('A6').values = [['F08 a F12 são materiais adicionais para fechar os cenários de renda, validade e limites do upload.']];
filesSheet.getRange('A8:I8').values = [['Código','Pasta','Arquivo','Tipo sugerido','Formato','Tamanho (KB)','Uso no teste','Situação','Observação']];
filesSheet.getRange('A9:I20').values = fileRows;
filesSheet.getRange('A2:I20').format.font = {name:font,size:10,color:dark};
filesSheet.getRange('A2').format.font = {name:font,size:15,bold:true,color:navy};
filesSheet.getRange('A3:A6').format.font = {name:font,size:10,color:'#5B6B7B'};
filesSheet.getRange('A8:I8').format = {fill:navy,font:{name:font,size:10,bold:true,color:'#FFFFFF'},rowHeight:32,verticalAlignment:'center',wrapText:true};
filesSheet.getRange('A9:I20').format.rowHeight = 43;
filesSheet.getRange('A9:I20').format.verticalAlignment = 'center';
filesSheet.getRange('G9:I20').format.wrapText = true;
filesSheet.getRange('F9:F20').setNumberFormat('#,##0');
for (const [col,width] of Object.entries({A:10,B:15,C:27,D:19,E:11,F:16,G:38,H:16,I:62})) filesSheet.getRange(`${col}:${col}`).format.columnWidth = width;
const filesTable = filesSheet.tables.add('A8:I20',true,'ArquivosValidaDoc');
filesTable.style = 'TableStyleMedium2';
filesSheet.freezePanes.freezeRows(8);

workbook.recalculate();
for (const [sheetName,range,name] of [
  ['Testes','A1:G16','preview-testes-esquerda.png'],
  ['Testes','H10:M16','preview-testes-direita.png'],
  ['Arquivos','A1:I16','preview-arquivos.png'],
]) {
  const preview = await workbook.render({sheetName,range,scale:1,format:'png'});
  await fs.writeFile(`${outputDir}${name}`,new Uint8Array(await preview.arrayBuffer()));
}
const summary = await workbook.inspect({kind:'table',range:'Testes!A5:L6',include:'values,formulas',tableMaxRows:2,tableMaxCols:12});
console.log(summary.ndjson);
const errors = await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:50},summary:'Verificação final de fórmulas'});
console.log(errors.ndjson);
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(`${outputDir}Plano_de_Testes_ValidaDoc.xlsx`);
console.log(`Salvo em ${outputDir}Plano_de_Testes_ValidaDoc.xlsx`);
