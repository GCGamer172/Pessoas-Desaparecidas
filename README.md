# Pessoas-Desaparecidas — Sistema de Cadastro Milk Carton

Aplicação acadêmica em Python e Streamlit, inspirada nos cartazes impressos nas antigas caixas de leite. Cadastra registros, gera cartazes para impressão/compartilhamento, detecta a classe genérica “pessoa” com YOLO e extrai texto de cartazes por OCR.

> **Uso responsável:** use dados fictícios ou imagens autorizadas. YOLO não reconhece identidade e uma detecção não confirma que alguém foi localizado. OCR pode errar; revise todos os campos antes de cadastrar. A mudança para “Localizada” exige confirmação de autorização. Não há reconhecimento facial nem vigilância.

## Requisitos

- Windows 10/11, CMD e Python 3.11, 3.12 ou 3.14 (64 bits).
- Internet na primeira utilização se for necessário baixar os pesos do YOLO ou do EasyOCR.

## Instalação e execução no CMD

No CMD do VS Code, na pasta do projeto:

```cmd
py -3.14 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

O navegador abrirá `http://localhost:8501`. Para usar Python 3.11 ou 3.12, substitua `py -3.14` pela versão instalada. Para encerrar, pressione `Ctrl+C` no terminal.

Execute os testes automatizados:

```cmd
call .venv\Scripts\activate.bat
python -m pytest -q
```

## Como testar as funcionalidades

1. **Cadastro:** em “Cadastrar pessoa”, informe os campos, selecione uma fotografia JPG/PNG autorizada e confirme a autorização do status. Marque também a opção separada de publicação no mapa somente quando houver autorização para divulgar os dados e a foto.
2. **Galeria e cartaz:** pesquise por nome/cidade, filtre a situação, revise o cartaz gerado e baixe em PNG ou PDF. Os campos podem ser editados.
3. **Status:** para alterar para “Localizada” ou “Desaparecida”, edite o cadastro e marque a confirmação de autorização.
4. **YOLO:** em “Analisar imagem (YOLO)”, envie uma imagem; o resultado mostra caixas da classe pessoa e suas confianças. Isso não compara identidades nem altera status.
5. **OCR:** em “Ler cartaz (OCR)”, envie o cartaz, extraia o texto e revise/corrija os campos. Confirme a revisão, complete o cadastro e forneça uma fotografia antes de salvar.
6. **Painel:** os cadastros recebem um número sequencial permanente, exibido na coluna “ID” e ordenado numericamente. O identificador interno permanece separado.
7. **Mapa no painel inicial:** exibe contagens agregadas por cidade/UF dos cadastros desaparecidos com autorização de publicação. Use “Localizar cidades para o mapa inicial” para buscar centros municipais; a busca envia somente cidade e UF ao serviço OpenStreetMap/Nominatim, não nomes ou fotos. Sem resultado, o mapa usa a capital da UF como referência temporária.
8. **Mapa do Brasil:** o mapa geral exibe miniaturas menores para perfis autorizados; no mapa individual de cada registro, o local aproximado aparece como um ponto vermelho.
9. **Estatísticas:** o painel inicial exibe cadastros, pessoas desaparecidas/localizadas e quantidades de análises YOLO e leituras OCR.

Os testes incluem registros fictícios e imagens sintéticas; não há dados reais ou registros de demonstração inseridos automaticamente. O mapa não consulta uma base oficial: usa apenas os cadastros locais com autorização explícita.

## Estrutura

```text
app.py                  interface Streamlit e navegação
database.py             API de conveniência da persistência
database/               modelos SQLAlchemy, migração e conexão SQLite
detector.py              API do detector YOLO
ocr.py                   API do EasyOCR
cartaz.py                geração de cartazes PNG/PDF
services/                validação, arquivos e operações de registros
pages/                   painel, galeria, análise e cadastro via OCR
tests/                   testes de banco, validação, processamento e cartaz
uploads/                 fotografias e cartazes analisados, armazenados localmente
```

O SQLite padrão fica em `database\app.db`; imagens são salvas em `uploads\` com nomes aleatórios. O esquema inicializa automaticamente e adiciona campos ausentes quando encontra um banco criado por uma versão anterior do protótipo.

Variáveis opcionais no CMD:

```cmd
set MISSING_PERSONS_DB=C:\caminho\para\app.db
set MISSING_PERSONS_UPLOAD_DIR=C:\caminho\para\uploads
set YOLO_MODEL=yolov8n.pt
set MISSING_PERSONS_GEOCODER_URL=https://nominatim.openstreetmap.org/search
```

## Segurança e limitações

- Uploads aceitos: JPG/JPEG e PNG, até 5 MB e 25 megapixels, com validação do conteúdo.
- O aplicativo gera cartazes a partir dos dados revisados; não adiciona informações de contato ou localização não fornecidas.
- Um resultado YOLO é somente uma detecção visual genérica. Não identifica pessoas, confirma correspondência com registros nem define localização.
- O sistema não implementa comparação facial, identificação biométrica ou vigilância contínua. Qualquer trabalho futuro nessa direção requer etapa separada, autorização e avaliação ética.
- Para uso real, seriam necessários controles de acesso, proteção/retensão de dados, auditoria, autorização dos titulares e análise ética/jurídica.
- A autorização de publicação no mapa é desmarcada por padrão e inclui a foto e os dados do perfil. Antes de disponibilizar o app publicamente, implemente autenticação, controle de acesso e retirada de consentimento, além de validação jurídica; não use este protótipo como serviço oficial de busca.
- Coordenadas do último local visto são exibidas como pontos precisos públicos quando a publicação no mapa está autorizada. Só as informe com autorização apropriada; para locais sensíveis, deixe as coordenadas vazias para usar a aproximação por UF.
- A localização por cidade usa uma consulta sob demanda ao Nominatim, com cache em memória no servidor, intervalo entre solicitações e atribuição ao OpenStreetMap. Não são enviados nome, fotografia ou endereço.
- A consulta ao Nominatim respeita o limite de uma solicitação por segundo e a [política de uso](https://operations.osmfoundation.org/policies/nominatim/). É possível trocar o serviço compatível via `MISSING_PERSONS_GEOCODER_URL` (endpoint HTTPS de busca), sem alterar o código. O mapa só consulta quando o usuário solicita a busca das cidades.
