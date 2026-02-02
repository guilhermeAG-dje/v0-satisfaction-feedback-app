from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
import csv
import io

app = Flask(__name__)
app.secret_key = 'chave_secreta_muito_segura_2026'

# Credenciais admin
ADMIN_USER = 'admin'
ADMIN_PASS = 'admin123'

# Configuracoes
REGISTOS_POR_PAGINA = 10
TIMEOUT_SEGUNDOS = 5

def init_db():
    """Inicializa a base de dados SQLite automaticamente"""
    conn = sqlite3.connect('satisfacao.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS avaliacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grau_satisfacao TEXT NOT NULL,
            data TEXT NOT NULL,
            hora TEXT NOT NULL,
            dia_semana TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_db():
    """Retorna conexao a base de dados"""
    conn = sqlite3.connect('satisfacao.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    """Decorator para proteger rotas admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============ ROTAS PUBLICAS ============

@app.route('/')
def index():
    """Pagina principal com interface de avaliacao"""
    return render_template('index.html', timeout=TIMEOUT_SEGUNDOS)

@app.route('/registar', methods=['POST'])
def registar():
    """Regista uma nova avaliacao"""
    data = request.get_json()
    grau = data.get('grau')
    
    graus_validos = ['muito_satisfeito', 'satisfeito', 'insatisfeito']
    if grau not in graus_validos:
        return jsonify({'error': 'Grau de satisfacao invalido'}), 400
    
    now = datetime.now()
    dias_pt = ['Segunda-feira', 'Terca-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sabado', 'Domingo']
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO avaliacoes (grau_satisfacao, data, hora, dia_semana, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        grau, 
        now.strftime('%Y-%m-%d'), 
        now.strftime('%H:%M:%S'), 
        dias_pt[now.weekday()],
        now.isoformat()
    ))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'timeout': TIMEOUT_SEGUNDOS})

# ============ ROTAS ADMIN ============

@app.route('/admin_2026')
def admin_redirect():
    """Redireciona para login"""
    return redirect(url_for('login'))

@app.route('/admin_2026/login', methods=['GET', 'POST'])
def login():
    """Pagina de login da administracao"""
    if session.get('logged_in'):
        return redirect(url_for('admin'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        return render_template('login.html', error='Credenciais invalidas. Tente novamente.')
    
    return render_template('login.html')

@app.route('/admin_2026/logout')
def logout():
    """Termina sessao admin"""
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin_2026/dashboard')
@login_required
def admin():
    """Dashboard de administracao com estatisticas"""
    conn = get_db()
    c = conn.cursor()
    
    # Estatisticas totais
    c.execute('SELECT grau_satisfacao, COUNT(*) FROM avaliacoes GROUP BY grau_satisfacao')
    stats = dict(c.fetchall())
    total = sum(stats.values()) if stats else 0
    
    # Parametros de filtro
    filtro_data = request.args.get('data', '')
    ver_hoje = request.args.get('hoje', '')
    pagina = request.args.get('pagina', 1, type=int)
    
    # Se pediu para ver hoje
    if ver_hoje == '1':
        filtro_data = datetime.now().strftime('%Y-%m-%d')
    
    # Todas as datas disponiveis
    c.execute('SELECT DISTINCT data FROM avaliacoes ORDER BY data DESC')
    datas = [row[0] for row in c.fetchall()]
    
    # Query base para registos
    if filtro_data:
        c.execute('SELECT COUNT(*) FROM avaliacoes WHERE data = ?', (filtro_data,))
        total_registos = c.fetchone()[0]
        
        # Estatisticas do dia filtrado
        c.execute('SELECT grau_satisfacao, COUNT(*) FROM avaliacoes WHERE data = ? GROUP BY grau_satisfacao', (filtro_data,))
        stats_filtro = dict(c.fetchall())
        total_filtro = sum(stats_filtro.values()) if stats_filtro else 0
    else:
        c.execute('SELECT COUNT(*) FROM avaliacoes')
        total_registos = c.fetchone()[0]
        stats_filtro = stats
        total_filtro = total
    
    # Paginacao
    total_paginas = max(1, (total_registos + REGISTOS_POR_PAGINA - 1) // REGISTOS_POR_PAGINA)
    pagina = max(1, min(pagina, total_paginas))
    offset = (pagina - 1) * REGISTOS_POR_PAGINA
    
    # Registos paginados
    if filtro_data:
        c.execute('''
            SELECT * FROM avaliacoes 
            WHERE data = ? 
            ORDER BY data DESC, hora DESC 
            LIMIT ? OFFSET ?
        ''', (filtro_data, REGISTOS_POR_PAGINA, offset))
    else:
        c.execute('''
            SELECT * FROM avaliacoes 
            ORDER BY data DESC, hora DESC 
            LIMIT ? OFFSET ?
        ''', (REGISTOS_POR_PAGINA, offset))
    
    registos = c.fetchall()
    
    # Dados para comparacao entre dias (ultimos 7 dias)
    c.execute('''
        SELECT data, grau_satisfacao, COUNT(*) 
        FROM avaliacoes 
        WHERE data >= date('now', '-7 days')
        GROUP BY data, grau_satisfacao
        ORDER BY data
    ''')
    dados_comparacao = {}
    for row in c.fetchall():
        data_row = row[0]
        if data_row not in dados_comparacao:
            dados_comparacao[data_row] = {'muito_satisfeito': 0, 'satisfeito': 0, 'insatisfeito': 0}
        dados_comparacao[data_row][row[1]] = row[2]
    
    conn.close()
    
    return render_template('admin.html', 
                         stats=stats,
                         stats_filtro=stats_filtro,
                         total=total,
                         total_filtro=total_filtro,
                         registos=registos,
                         datas=datas,
                         filtro_data=filtro_data,
                         pagina=pagina,
                         total_paginas=total_paginas,
                         total_registos=total_registos,
                         dados_comparacao=dados_comparacao)

@app.route('/admin_2026/exportar/<formato>')
@login_required
def exportar(formato):
    """Exporta dados para CSV ou TXT"""
    filtro_data = request.args.get('data', '')
    
    conn = get_db()
    c = conn.cursor()
    
    if filtro_data:
        c.execute('SELECT * FROM avaliacoes WHERE data = ? ORDER BY hora DESC', (filtro_data,))
        nome_ficheiro = f'avaliacoes_{filtro_data}'
    else:
        c.execute('SELECT * FROM avaliacoes ORDER BY data DESC, hora DESC')
        nome_ficheiro = 'avaliacoes_todas'
    
    registos = c.fetchall()
    conn.close()
    
    if formato == 'csv':
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(['ID', 'Grau de Satisfacao', 'Data', 'Hora', 'Dia da Semana'])
        
        graus_formatados = {
            'muito_satisfeito': 'Muito Satisfeito',
            'satisfeito': 'Satisfeito',
            'insatisfeito': 'Insatisfeito'
        }
        
        for r in registos:
            writer.writerow([
                r['id'], 
                graus_formatados.get(r['grau_satisfacao'], r['grau_satisfacao']), 
                r['data'], 
                r['hora'], 
                r['dia_semana']
            ])
        
        return Response(
            output.getvalue(),
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename={nome_ficheiro}.csv'}
        )
    
    elif formato == 'txt':
        output = io.StringIO()
        output.write('=' * 60 + '\n')
        output.write('         RELATORIO DE AVALIACOES DE SATISFACAO\n')
        output.write('=' * 60 + '\n')
        output.write(f'Data de exportacao: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        if filtro_data:
            output.write(f'Filtro aplicado: {filtro_data}\n')
        output.write(f'Total de registos: {len(registos)}\n')
        output.write('=' * 60 + '\n\n')
        
        graus_formatados = {
            'muito_satisfeito': 'Muito Satisfeito',
            'satisfeito': 'Satisfeito',
            'insatisfeito': 'Insatisfeito'
        }
        
        for r in registos:
            output.write(f'Registo #{r["id"]}\n')
            output.write(f'  Satisfacao: {graus_formatados.get(r["grau_satisfacao"], r["grau_satisfacao"])}\n')
            output.write(f'  Data: {r["data"]}\n')
            output.write(f'  Hora: {r["hora"]}\n')
            output.write(f'  Dia: {r["dia_semana"]}\n')
            output.write('-' * 40 + '\n')
        
        output.write('\n' + '=' * 60 + '\n')
        output.write('                  FIM DO RELATORIO\n')
        output.write('=' * 60 + '\n')
        
        return Response(
            output.getvalue(),
            mimetype='text/plain; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename={nome_ficheiro}.txt'}
        )
    
    return redirect(url_for('admin'))

@app.route('/admin_2026/api/stats')
@login_required
def api_stats():
    """API para obter estatisticas em JSON"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT grau_satisfacao, COUNT(*) FROM avaliacoes GROUP BY grau_satisfacao')
    stats = dict(c.fetchall())
    
    c.execute('SELECT COUNT(*) FROM avaliacoes')
    total = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'stats': stats,
        'total': total,
        'percentagens': {
            'muito_satisfeito': round((stats.get('muito_satisfeito', 0) / total * 100), 1) if total > 0 else 0,
            'satisfeito': round((stats.get('satisfeito', 0) / total * 100), 1) if total > 0 else 0,
            'insatisfeito': round((stats.get('insatisfeito', 0) / total * 100), 1) if total > 0 else 0
        }
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
