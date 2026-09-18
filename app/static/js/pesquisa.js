// Logica da pagina de pesquisa (Fase 1).

const formPesquisa = document.getElementById("form-pesquisa");
const botaoPesquisar = document.getElementById("botao-pesquisar");
const mensagemStatus = document.getElementById("mensagem-status");
const painelResultados = document.getElementById("painel-resultados");
const listaItens = document.getElementById("lista-itens");
const resumoCusto = document.getElementById("resumo-custo");
const seletorOrdenar = document.getElementById("ordenar");
const listaHistorico = document.getElementById("lista-historico");
const filtroTema = document.getElementById("filtro-tema");
const botaoAtualizarHistorico = document.getElementById("botao-atualizar-historico");

let pesquisaAtualId = null;

function formatarData(dataIso) {
    if (!dataIso) return "data nao informada";
    const [ano, mes, dia] = dataIso.split("-");
    return `${dia}/${mes}/${ano}`;
}

function definirDatasPadrao() {
    const hoje = new Date();
    const seteDiasAtras = new Date();
    seteDiasAtras.setDate(hoje.getDate() - 7);

    document.getElementById("data_fim").value = hoje.toISOString().slice(0, 10);
    document.getElementById("data_inicio").value = seteDiasAtras.toISOString().slice(0, 10);
}

function mostrarMensagem(texto, tipo = "info") {
    mensagemStatus.textContent = texto;
    mensagemStatus.className = "mensagem-status" + (tipo === "erro" ? " erro" : "");
}

function renderizarItem(item) {
    const div = document.createElement("div");
    div.className = `item-card status-${item.status}`;
    div.dataset.itemId = item.id;

    const selo = item.nao_verificado
        ? '<span class="selo-nao-verificado">nao verificado</span>'
        : "";

    const fontesHtml = item.fontes
        .map((f) => `<a href="${f.url}" target="_blank" rel="noopener">${f.nome_fonte || f.url}${f.oficial ? " (fonte oficial)" : ""}</a>`)
        .join("");

    const palavrasChave = item.palavras_chave ? `<div class="item-meta">Palavras-chave: ${item.palavras_chave}</div>` : "";
    const processo = item.numero_processo ? `<div class="item-meta">Processo: ${item.numero_processo}</div>` : "";

    div.innerHTML = `
        <div class="item-titulo">${item.titulo}${selo}</div>
        <div class="item-meta">${item.tipo === "julgado" ? "Julgado" : "Noticia"} | ${formatarData(item.data_publicacao)} | ${item.tribunal || "tribunal nao informado"} | relevancia ${item.relevancia_score}/5</div>
        ${processo}
        <p>${item.tese_resumo}</p>
        <p><strong>Impacto pratico:</strong> ${item.relevancia_pratica}</p>
        ${palavrasChave}
        <div class="item-fontes">${fontesHtml}</div>
        <div class="item-acoes">
            <button class="acao-salvar">Salvar</button>
            <button class="acao-descartar secundario">Descartar</button>
            <button class="acao-erro perigo">Marcar como erro</button>
        </div>
        <div class="item-erro-form">
            <textarea placeholder="Descreva o problema encontrado (ex.: data errada, fonte inexistente, resumo impreciso)"></textarea>
            <button class="acao-confirmar-erro perigo">Confirmar erro</button>
        </div>
    `;

    div.querySelector(".acao-salvar").addEventListener("click", () => atualizarStatusItem(item.id, "salvo", "", div));
    div.querySelector(".acao-descartar").addEventListener("click", () => atualizarStatusItem(item.id, "descartado", "", div));
    div.querySelector(".acao-erro").addEventListener("click", () => {
        div.querySelector(".item-erro-form").classList.toggle("visivel");
    });
    div.querySelector(".acao-confirmar-erro").addEventListener("click", () => {
        const observacao = div.querySelector("textarea").value.trim();
        if (!observacao) {
            alert("Descreva o problema antes de confirmar.");
            return;
        }
        atualizarStatusItem(item.id, "erro", observacao, div);
    });

    return div;
}

async function atualizarStatusItem(itemId, status, observacaoErro, elementoCard) {
    try {
        const resposta = await fetch(`/api/itens/${itemId}/status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status, observacao_erro: observacaoErro }),
        });
        if (!resposta.ok) {
            const erro = await resposta.json();
            throw new Error(erro.detail || "Falha ao atualizar item.");
        }
        elementoCard.className = `item-card status-${status}`;
        if (status !== "erro") {
            elementoCard.querySelector(".item-erro-form").classList.remove("visivel");
        }
    } catch (erro) {
        alert(erro.message);
    }
}

function renderizarResultados(pesquisa) {
    pesquisaAtualId = pesquisa.id;
    painelResultados.hidden = false;
    resumoCusto.textContent = `${pesquisa.itens.length} item(ns) encontrado(s) | custo estimado desta pesquisa: US$ ${pesquisa.custo_tokens_estimado.toFixed(4)}`;
    listaItens.innerHTML = "";
    if (pesquisa.itens.length === 0) {
        listaItens.innerHTML = "<p>Nenhum resultado confiavel foi encontrado no periodo informado.</p>";
        return;
    }
    pesquisa.itens.forEach((item) => listaItens.appendChild(renderizarItem(item)));
}

formPesquisa.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const dados = Object.fromEntries(new FormData(formPesquisa).entries());

    botaoPesquisar.disabled = true;
    mostrarMensagem("Pesquisando noticias e julgados recentes, isso pode levar um minuto...");
    painelResultados.hidden = true;

    try {
        const resposta = await fetch("/api/pesquisas", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(dados),
        });
        const corpo = await resposta.json();
        if (!resposta.ok) {
            throw new Error(corpo.detail || "Falha ao executar a pesquisa.");
        }
        mostrarMensagem("Pesquisa concluida.");
        renderizarResultados(corpo);
        carregarHistorico();
    } catch (erro) {
        mostrarMensagem(erro.message, "erro");
    } finally {
        botaoPesquisar.disabled = false;
    }
});

seletorOrdenar.addEventListener("change", async () => {
    if (!pesquisaAtualId) return;
    const resposta = await fetch(`/api/pesquisas/${pesquisaAtualId}?ordenar=${seletorOrdenar.value}`);
    const corpo = await resposta.json();
    renderizarResultados(corpo);
});

async function carregarHistorico() {
    const tema = filtroTema.value.trim();
    const url = tema ? `/api/pesquisas?tema=${encodeURIComponent(tema)}` : "/api/pesquisas";
    const resposta = await fetch(url);
    const pesquisas = await resposta.json();

    listaHistorico.innerHTML = "";
    if (pesquisas.length === 0) {
        listaHistorico.innerHTML = "<p>Nenhuma pesquisa no historico.</p>";
        return;
    }

    pesquisas.forEach((p) => {
        const linha = document.createElement("div");
        linha.className = "historico-linha";
        linha.innerHTML = `
            <span>${p.tema} (${formatarData(p.data_inicio)} a ${formatarData(p.data_fim)}) | ${p.tipo} | ${p.tribunal}</span>
            <span>${p.total_itens} item(ns)</span>
        `;
        linha.addEventListener("click", async () => {
            const respostaDetalhe = await fetch(`/api/pesquisas/${p.id}`);
            const detalhe = await respostaDetalhe.json();
            renderizarResultados(detalhe);
            window.scrollTo({ top: painelResultados.offsetTop, behavior: "smooth" });
        });
        listaHistorico.appendChild(linha);
    });
}

botaoAtualizarHistorico.addEventListener("click", carregarHistorico);

definirDatasPadrao();
carregarHistorico();
