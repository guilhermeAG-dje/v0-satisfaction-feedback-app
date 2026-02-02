# Sistema de Avaliacao de Satisfacao

Aplicacao web full-stack para recolha e analise de avaliacoes de satisfacao de clientes/utentes.

## Funcionalidades

### Interface Publica
- 3 botoes de avaliacao com emojis (Muito Satisfeito, Satisfeito, Insatisfeito)
- Interface fullscreen, otimizada para tablets e telemoveis
- Feedback visual apos cada avaliacao
- Mensagem de agradecimento temporaria
- Bloqueio de cliques consecutivos (timeout configuravel)
- Registo automatico de data, hora e dia da semana

### Area de Administracao
- URL protegida: `/admin_2026`
- Autenticacao com utilizador e password
- Dashboard com estatisticas em tempo real
- Graficos interativos (barras, circular, linha temporal)
- Filtragem por data
- Comparacao entre dias (ultimos 7 dias)
- Tabela com todos os registos e paginacao
- Exportacao de dados para CSV e TXT

## Tecnologias

- **Backend:** Python 3, Flask
- **Base de Dados:** SQLite (criada automaticamente)
- **Frontend:** HTML5, CSS3, JavaScript
- **Graficos:** Chart.js
- **Design:** Responsivo e acessivel (WCAG)

## Como Executar

### Pre-requisitos
- Python 3.8 ou superior
- pip (gestor de pacotes Python)

### Instalacao

1. **Clonar o repositorio:**
```bash
git clone https://github.com/SEU_USUARIO/satisfacao-app.git
cd satisfacao-app
```

2. **Criar ambiente virtual (recomendado):**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

3. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

4. **Executar a aplicacao:**
```bash
python app.py
```

5. **Aceder no navegador:**
- Interface Publica: http://localhost:5000
- Area Admin: http://localhost:5000/admin_2026

### Credenciais de Administracao
- **Utilizador:** admin
- **Password:** admin123

## Estrutura do Projeto

```
satisfacao-app/
├── app.py                 # Aplicacao principal Flask
├── requirements.txt       # Dependencias Python
├── README.md             # Documentacao
├── satisfacao.db         # Base de dados SQLite (criada automaticamente)
├── templates/
│   ├── index.html        # Interface publica
│   ├── login.html        # Pagina de login
│   └── admin.html        # Dashboard administrativo
└── static/
    ├── css/
    │   └── style.css     # Estilos CSS
    └── js/
        └── script.js     # JavaScript
```

## Deploy Gratuito

### Render.com
1. Criar conta em render.com
2. Conectar repositorio GitHub
3. Criar novo Web Service
4. Configurar:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`

### PythonAnywhere
1. Criar conta gratuita em pythonanywhere.com
2. Fazer upload dos ficheiros
3. Configurar aplicacao WSGI
4. Definir caminho para app Flask

### Railway
1. Criar conta em railway.app
2. Conectar repositorio GitHub
3. Deploy automatico

## Configuracoes

No ficheiro `app.py`, pode ajustar:

```python
ADMIN_USER = 'admin'           # Utilizador admin
ADMIN_PASS = 'admin123'        # Password admin
REGISTOS_POR_PAGINA = 10       # Registos por pagina na tabela
TIMEOUT_SEGUNDOS = 5           # Segundos entre avaliacoes
```

## Licenca

Projeto academico - 2026

## Autor

Desenvolvido para avaliacao de trabalho pratico.
