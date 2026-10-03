# Radar Imobiliario

Aplicativo local para pesquisa juridica, geracao de roteiros de video e
teleprompter, voltado para conteudo educativo de direito imobiliario.

O projeto e construido em 3 fases. Este README cobre a **Fase 1: Pesquisa**.

## Requisitos

- Python 3.11 ou superior
- Uma chave de API da Anthropic (https://console.anthropic.com/)

## Jeito mais facil de iniciar (um clique)

1. Instale o Python, se ainda nao tiver: https://www.python.org/downloads/
2. De dois cliques no arquivo correspondente ao seu sistema:
   - Windows: `iniciar_windows.bat`
   - Mac: `iniciar_mac.command` (se o macOS bloquear por seguranca na primeira
     vez, clique com o botao direito nele e escolha "Abrir")
3. Na primeira vez, o script vai pedir para voce colar sua chave da API no
   arquivo `.env` que ele mesmo cria. Salve o arquivo e volte para a janela
   do script.
4. O navegador abre automaticamente em http://localhost:8000. Para parar o
   programa, feche a janela preta que ficou aberta.

## Instalacao manual (alternativa)

```bash
# 1. Criar e ativar um ambiente virtual
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Instalar as dependencias
pip install -r requirements.txt

# 3. Configurar as variaveis de ambiente
cp .env.example .env
# edite o arquivo .env e preencha ANTHROPIC_API_KEY com sua chave
```

## Como rodar

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Acesse http://localhost:8000 no navegador.

## Uso da Fase 1

1. Preencha o tema (ex.: "distrato", "alienacao fiduciaria", "locacao"), o
   periodo, o tipo (noticia, julgado ou ambos) e o tribunal desejado.
2. Clique em "Pesquisar". O app usa a busca na web do Claude para localizar
   noticias e julgados reais publicados no periodo, sempre citando a fonte.
3. Cada resultado mostra titulo, data de publicacao na fonte, tribunal,
   numero do processo (quando disponivel), resumo da tese, palavras-chave,
   impacto pratico e as fontes com link clicavel.
4. Itens sem nenhuma fonte oficial (tribunal, orgao publico ou Diario
   Oficial) aparecem com o selo "nao verificado".
5. Use os botoes "Salvar", "Descartar" ou "Marcar como erro" (com uma
   observacao do problema) em cada item.
6. O historico de pesquisas fica salvo no banco local e pode ser filtrado
   por tema.

## Regras de fidelidade aplicadas

- O modelo nunca inventa numero de processo, relator, data ou ementa: campos
  sem informacao na fonte ficam vazios.
- Todo item precisa ter ao menos uma URL real de origem.
- Itens publicados fora do periodo pedido sao descartados automaticamente.
- Noticias/julgados repetidos em varios portais viram um unico item, com
  todas as fontes listadas.

## Custos

Cada pesquisa registra os tokens de entrada e saida consumidos e o custo
estimado em dolares, exibido no topo dos resultados. O valor e uma
aproximacao baseada no preco por token do modelo `claude-sonnet-5` e nao
inclui eventual taxa adicional por busca na web.

## Solucao de problemas

- **"ANTHROPIC_API_KEY nao configurada"**: verifique se o arquivo `.env`
  existe e contem a chave.
- **"Chave da API da Anthropic invalida"**: confirme a chave no arquivo `.env`.
- **"Limite de uso da API atingido"**: aguarde alguns instantes e tente
  novamente.
- **Nenhum resultado encontrado**: tente um periodo mais amplo ou um tema
  mais generico.

## Estrutura do projeto

```
app/
  main.py                  # aplicativo FastAPI
  config.py                # variaveis de ambiente
  database.py               # conexao SQLAlchemy
  models.py                  # tabelas do banco (todas as 3 fases)
  schemas.py                  # schemas Pydantic da Fase 1
  routers/pesquisa.py           # endpoints da Fase 1
  services/
    anthropic_client.py         # chamadas a API da Anthropic com web search
    pesquisa_service.py          # filtros, deduplicacao e persistencia
  templates/                      # paginas HTML (Jinja2)
  static/                           # CSS e JS
```

## Proximas fases

- **Fase 2**: geracao de roteiros a partir dos itens salvos, com
  verificacao etica automatica (Provimento 205/2021 CFOAB).
- **Fase 3**: teleprompter com acesso pelo tablet/celular na rede local.
