from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import zipfile
import os
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None
from datetime import datetime
import csv
from sqlalchemy import text
import pandas as pd
import io
try:
    from authlib.integrations.flask_client import OAuth
except Exception:
    OAuth = None

app = Flask(__name__)
app.secret_key = "supersecretkey"
if load_dotenv:
    load_dotenv()
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID', '')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET', '')
PUBLIC_MODE = os.getenv('PUBLIC_MODE', 'true').lower() in ('1', 'true', 'yes', 'on')

oauth = OAuth(app) if OAuth else None
if oauth:
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

# --- Configuração Database ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Login Manager ---
login_manager = LoginManager()
login_manager.login_view = 'login_page'
login_manager.init_app(app)

@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/api/') or request.path.startswith('/auth/'):
        return jsonify({'ok': False, 'message': 'Não autorizado'}), 401
    return redirect(url_for('login_page'))

def is_admin():
    return current_user.is_authenticated and current_user.email == 'admin@local'

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not is_admin():
            return redirect(url_for('admin_login'))
        return fn(*args, **kwargs)
    return wrapper

def login_or_public(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if PUBLIC_MODE:
            return fn(*args, **kwargs)
        if not current_user.is_authenticated:
            return unauthorized()
        return fn(*args, **kwargs)
    return wrapper

_public_user_id = None

def get_public_user():
    global _public_user_id
    if _public_user_id:
        return User.query.get(_public_user_id)
    user = User.query.filter_by(email='public@local').first()
    if not user:
        user = User(email='public@local')
        user.set_password(os.urandom(12).hex())
        db.session.add(user)
        db.session.commit()
    _public_user_id = user.id
    return user

def effective_user():
    if current_user.is_authenticated:
        return current_user
    return get_public_user()

def parse_date_ymd(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None

def get_sqlite_db_path():
    uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if uri.startswith('sqlite:///'):
        path = uri.replace('sqlite:///', '', 1)
        if not os.path.isabs(path):
            path = os.path.join(app.root_path, path)
        return path
    return None


# --- Modelos ---
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    grau_satisfacao = db.Column(db.String(20))
    data = db.Column(db.String(20))
    hora = db.Column(db.String(20))
    dia_semana = db.Column(db.String(20))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(30), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Medicamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    dose = db.Column(db.String(120), nullable=False)
    hora = db.Column(db.String(10), nullable=False)
    data = db.Column(db.String(10), nullable=True)


class Toma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    med_id = db.Column(db.Integer, db.ForeignKey('medicamento.id'), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    dose = db.Column(db.String(120), nullable=False)
    data = db.Column(db.String(10), nullable=False)
    hora = db.Column(db.String(8), nullable=False)
    nota = db.Column(db.Text)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Criar DB se não existir ---
with app.app_context():
    db.create_all()
    # Migração simples: adicionar coluna "nota" se não existir
    try:
        cols = db.session.execute(text("PRAGMA table_info(toma)")).fetchall()
        col_names = {c[1] for c in cols}
        if cols and 'nota' not in col_names:
            db.session.execute(text("ALTER TABLE toma ADD COLUMN nota TEXT"))
            db.session.commit()
    except Exception:
        db.session.rollback()
    # Migração simples: adicionar coluna "phone" em user se não existir
    try:
        cols = db.session.execute(text("PRAGMA table_info(user)")).fetchall()
        col_names = {c[1] for c in cols}
        if cols and 'phone' not in col_names:
            db.session.execute(text("ALTER TABLE user ADD COLUMN phone TEXT"))
            db.session.commit()
    except Exception:
        db.session.rollback()
    # Migração simples: adicionar coluna "data" em medicamento se não existir
    try:
        cols = db.session.execute(text("PRAGMA table_info(medicamento)")).fetchall()
        col_names = {c[1] for c in cols}
        if cols and 'data' not in col_names:
            db.session.execute(text("ALTER TABLE medicamento ADD COLUMN data TEXT"))
            db.session.commit()
    except Exception:
        db.session.rollback()
    if PUBLIC_MODE:
        try:
            get_public_user()
        except Exception:
            db.session.rollback()

# --- Rotas públicas ---
@app.route('/')
@login_or_public
def index():
    return send_from_directory(app.root_path, 'index.html')

@app.route('/index.html')
@login_or_public
def index_html():
    return send_from_directory(app.root_path, 'index.html')

@app.route('/login')
def login_page():
    return send_from_directory(app.root_path, 'login.html')

@app.route('/<path:filename>')
def static_files(filename):
    # Serve arquivos estáticos (css/js/manifest) que estão na raiz do projeto
    if filename == 'index.html':
        return redirect(url_for('login_page'))
    return send_from_directory(app.root_path, filename)

@app.route('/public/db')
def public_db_download():
    if not PUBLIC_MODE:
        return jsonify({'ok': False, 'message': 'Modo público desativado'}), 403
    path = get_sqlite_db_path()
    if not path:
        return jsonify({'ok': False, 'message': 'Base de dados não é SQLite'}), 400
    if not os.path.exists(path):
        return jsonify({'ok': False, 'message': 'Base de dados não encontrada'}), 404
    return send_file(path, mimetype='application/octet-stream', download_name='database.db', as_attachment=True)

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    grau = request.form.get('grau')
    now = datetime.now()
    feedback = Feedback(
        grau_satisfacao=grau,
        data=now.strftime("%Y-%m-%d"),
        hora=now.strftime("%H:%M:%S"),
        dia_semana=now.strftime("%A")
    )
    db.session.add(feedback)
    db.session.commit()
    return "ok"

# --- API medicamentos ---
@app.route('/api/medicamentos', methods=['GET', 'POST'])
@login_or_public
def medicamentos_api():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        nome = (data.get('nome') or '').strip()
        dose = (data.get('dose') or '').strip()
        hora = (data.get('hora') or '').strip()
        data_med = (data.get('data') or '').strip()
        if not nome or not dose or not hora or not data_med:
            return jsonify({'ok': False, 'message': 'Nome, dose, hora e data são obrigatórios'}), 400
        parsed_date = parse_date_ymd(data_med)
        if not parsed_date:
            return jsonify({'ok': False, 'message': 'Data inválida'}), 400
        if parsed_date < datetime.now().date():
            return jsonify({'ok': False, 'message': 'Não é possível marcar dias anteriores a hoje'}), 400
        user = effective_user()
        med = Medicamento(user_id=user.id, nome=nome, dose=dose, hora=hora, data=data_med or None)
        db.session.add(med)
        db.session.commit()
        return jsonify({'ok': True, 'id': med.id})

    if PUBLIC_MODE:
        meds = Medicamento.query.all()
    else:
        meds = Medicamento.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': m.id,
        'nome': m.nome,
        'dose': m.dose,
        'hora': m.hora,
        'data': m.data
    } for m in meds])

@app.route('/api/medicamentos/<int:med_id>', methods=['DELETE'])
@login_or_public
def medicamentos_delete(med_id):
    if PUBLIC_MODE:
        med = Medicamento.query.filter_by(id=med_id).first()
    else:
        med = Medicamento.query.filter_by(id=med_id, user_id=current_user.id).first()
    if not med:
        return jsonify({'ok': False, 'message': 'Medicamento não encontrado'}), 404
    db.session.delete(med)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/medicamentos/<int:med_id>/take', methods=['POST'])
@login_or_public
def medicamentos_take(med_id):
    if PUBLIC_MODE:
        med = Medicamento.query.filter_by(id=med_id).first()
    else:
        med = Medicamento.query.filter_by(id=med_id, user_id=current_user.id).first()
    if not med:
        return jsonify({'ok': False, 'message': 'Medicamento não encontrado'}), 404
    data = request.get_json(silent=True) or {}
    nota = (data.get('nota') or '').strip()
    # Regista toma
    now = datetime.now()
    user = effective_user()
    t = Toma(
        user_id=user.id,
        med_id=med.id,
        nome=med.nome,
        dose=med.dose,
        nota=nota or None,
        data=now.strftime("%Y-%m-%d"),
        hora=now.strftime("%H:%M:%S")
    )
    db.session.add(t)
    # Remove medicamento (conforme pedido)
    db.session.delete(med)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/medicamentos/<int:med_id>', methods=['PUT'])
@login_or_public
def medicamentos_update(med_id):
    if PUBLIC_MODE:
        med = Medicamento.query.filter_by(id=med_id).first()
    else:
        med = Medicamento.query.filter_by(id=med_id, user_id=current_user.id).first()
    if not med:
        return jsonify({'ok': False, 'message': 'Medicamento não encontrado'}), 404
    data = request.get_json(silent=True) or {}
    nome = (data.get('nome') or '').strip()
    dose = (data.get('dose') or '').strip()
    hora = (data.get('hora') or '').strip()
    data_med = (data.get('data') or '').strip()
    if not nome or not dose or not hora or not data_med:
        return jsonify({'ok': False, 'message': 'Nome, dose, hora e data são obrigatórios'}), 400
    parsed_date = parse_date_ymd(data_med)
    if not parsed_date:
        return jsonify({'ok': False, 'message': 'Data inválida'}), 400
    if parsed_date < datetime.now().date():
        return jsonify({'ok': False, 'message': 'Não é possível marcar dias anteriores a hoje'}), 400
    med.nome = nome
    med.dose = dose
    med.hora = hora
    med.data = data_med or None
    db.session.commit()
    return jsonify({'ok': True})

# --- API tomas (histórico) ---
@app.route('/api/tomas', methods=['GET', 'POST'])
@login_or_public
def tomas_api():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        med_id = data.get('med_id')
        nome = (data.get('nome') or '').strip()
        dose = (data.get('dose') or '').strip()
        nota = (data.get('nota') or '').strip()
        now = datetime.now()
        if not med_id or not nome or not dose:
            return jsonify({'ok': False, 'message': 'Dados incompletos'}), 400
        user = effective_user()
        t = Toma(
            user_id=user.id,
            med_id=med_id,
            nome=nome,
            dose=dose,
            nota=nota or None,
            data=now.strftime("%Y-%m-%d"),
            hora=now.strftime("%H:%M:%S")
        )
        db.session.add(t)
        db.session.commit()
        return jsonify({'ok': True, 'id': t.id})

    month = request.args.get('month')
    start = request.args.get('start')
    end = request.args.get('end')
    if PUBLIC_MODE:
        q = Toma.query
    else:
        q = Toma.query.filter_by(user_id=current_user.id)
    if month:
        q = q.filter(Toma.data.startswith(month))
    if start:
        q = q.filter(Toma.data >= start)
    if end:
        q = q.filter(Toma.data <= end)
    tomas = q.order_by(Toma.data.desc(), Toma.hora.desc()).all()
    return jsonify([{
        'id': t.id,
        'med_id': t.med_id,
        'nome': t.nome,
        'dose': t.dose,
        'data': t.data,
        'hora': t.hora,
        'nota': t.nota
    } for t in tomas])

@app.route('/api/tomas/export')
@login_or_public
def tomas_export():
    month = request.args.get('month')
    start = request.args.get('start')
    end = request.args.get('end')
    if PUBLIC_MODE:
        q = Toma.query
    else:
        q = Toma.query.filter_by(user_id=current_user.id)
    if month:
        q = q.filter(Toma.data.startswith(month))
    if start:
        q = q.filter(Toma.data >= start)
    if end:
        q = q.filter(Toma.data <= end)
    tomas = q.order_by(Toma.data.desc(), Toma.hora.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Medicamento', 'Dose', 'Data', 'Hora', 'Nota'])
    for t in tomas:
        writer.writerow([t.id, t.nome, t.dose, t.data, t.hora, t.nota or ""])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        download_name="historico_tomas.csv",
        as_attachment=True
    )

# --- Rotas admin ---
@app.route('/admin_2026/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == '123':
            user = User.query.filter_by(email='admin@local').first()
            if not user:
                user = User(email='admin@local')
                user.set_password('123')
                db.session.add(user)
                db.session.commit()
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Credenciais incorretas')
    return render_template('admin_login.html')

@app.route('/admin_2026/logout')
@admin_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

@app.route('/admin_2026')
@admin_required
def admin_dashboard():
    # Estatísticas básicas
    total = Feedback.query.count()
    muito_satisfeito = Feedback.query.filter_by(grau_satisfacao="Muito Satisfeito").count()
    satisfeito = Feedback.query.filter_by(grau_satisfacao="Satisfeito").count()
    insatisfeito = Feedback.query.filter_by(grau_satisfacao="Insatisfeito").count()
    
    # Percentagens
    if total > 0:
        pct_muito = round(muito_satisfeito / total * 100, 1)
        pct_satisfeito = round(satisfeito / total * 100, 1)
        pct_insatisfeito = round(insatisfeito / total * 100, 1)
    else:
        pct_muito = pct_satisfeito = pct_insatisfeito = 0

    feedbacks = Feedback.query.order_by(Feedback.data.desc(), Feedback.hora.desc()).all()

    users = User.query.order_by(User.id.desc()).all()
    users_data = []
    for u in users:
        meds_count = Medicamento.query.filter_by(user_id=u.id).count()
        tomas_count = Toma.query.filter_by(user_id=u.id).count()
        users_data.append({
            'id': u.id,
            'email': u.email,
            'meds': meds_count,
            'tomas': tomas_count
        })

    return render_template('admin.html',
                           total=total,
                           muito_satisfeito=muito_satisfeito,
                           satisfeito=satisfeito,
                           insatisfeito=insatisfeito,
                           pct_muito=pct_muito,
                           pct_satisfeito=pct_satisfeito,
                           pct_insatisfeito=pct_insatisfeito,
                           feedbacks=feedbacks,
                           users=users_data)

# --- Exportação ---
@app.route('/admin_2026/export/<tipo>')
@admin_required
def export_data(tipo):
    feedbacks = Feedback.query.all()
    df = pd.DataFrame([{
        'ID': f.id,
        'Grau Satisfacao': f.grau_satisfacao,
        'Data': f.data,
        'Hora': f.hora,
        'Dia Semana': f.dia_semana
    } for f in feedbacks])
    
    if tipo == 'csv':
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode()),
                         mimetype="text/csv",
                         download_name="feedback.csv",
                         as_attachment=True)
    elif tipo == 'txt':
        output = io.StringIO()
        df.to_csv(output, index=False, sep='\t')
        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode()),
                         mimetype="text/plain",
                         download_name="feedback.txt",
                         as_attachment=True)
    else:
        return "Tipo inválido"

@app.route('/admin_2026/users/<int:user_id>')
@admin_required
def admin_user_detail(user_id):
    user = User.query.get_or_404(user_id)
    meds = Medicamento.query.filter_by(user_id=user_id).all()
    tomas = Toma.query.filter_by(user_id=user_id).order_by(Toma.data.desc(), Toma.hora.desc()).all()
    return render_template('admin_user.html', user=user, meds=meds, tomas=tomas)

@app.route('/admin_2026/users/<int:user_id>/reset', methods=['POST'])
@admin_required
def admin_user_reset(user_id):
    user = User.query.get_or_404(user_id)
    new_password = (request.form.get('new_password') or '').strip()
    if not new_password:
        flash('Nova palavra-passe inválida')
        return redirect(url_for('admin_user_detail', user_id=user_id))
    user.set_password(new_password)
    db.session.commit()
    flash('Palavra-passe atualizada')
    return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route('/admin_2026/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_user_delete(user_id):
    user = User.query.get_or_404(user_id)
    if user.email == 'admin@local':
        flash('Não é possível apagar o admin')
        return redirect(url_for('admin_dashboard'))
    Medicamento.query.filter_by(user_id=user_id).delete()
    Toma.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    flash('Utilizador removido')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_2026/export/all')
@admin_required
def export_all():
    users = User.query.all()
    meds = Medicamento.query.all()
    tomas = Toma.query.all()

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        users_csv = io.StringIO()
        w = csv.writer(users_csv)
        w.writerow(['ID', 'Email'])
        for u in users:
            w.writerow([u.id, u.email])
        zf.writestr('users.csv', users_csv.getvalue())

        meds_csv = io.StringIO()
        w = csv.writer(meds_csv)
        w.writerow(['ID', 'UserID', 'Nome', 'Dose', 'Hora', 'Data'])
        for m in meds:
            w.writerow([m.id, m.user_id, m.nome, m.dose, m.hora, m.data or ""])
        zf.writestr('medicamentos.csv', meds_csv.getvalue())

        tomas_csv = io.StringIO()
        w = csv.writer(tomas_csv)
        w.writerow(['ID', 'UserID', 'MedID', 'Nome', 'Dose', 'Data', 'Hora', 'Nota'])
        for t in tomas:
            w.writerow([t.id, t.user_id, t.med_id, t.nome, t.dose, t.data, t.hora, t.nota or ""])
        zf.writestr('tomas.csv', tomas_csv.getvalue())

    mem.seek(0)
    return send_file(mem, mimetype='application/zip', download_name='admin_export.zip', as_attachment=True)

# --- Autenticação simples (login/registro) ---
@app.route('/auth/register', methods=['POST'])
def auth_register():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'ok': False, 'message': 'Email e palavra-passe são obrigatórios'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'ok': False, 'message': 'Este email já está registado'}), 400

    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'ok': True, 'message': 'Conta criada com sucesso'})


@app.route('/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'ok': False, 'message': 'Email e palavra-passe são obrigatórios'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'ok': False, 'message': 'Credenciais inválidas'}), 401

    login_user(user)
    return jsonify({'ok': True})


@app.route('/auth/logout', methods=['POST'])
@login_or_public
def auth_logout():
    logout_user()
    return jsonify({'ok': True})

# --- Google OAuth ---
@app.route('/auth/google')
def auth_google():
    if not oauth or not app.config['GOOGLE_CLIENT_ID'] or not app.config['GOOGLE_CLIENT_SECRET']:
        return "OAuth Google não configurado", 400
    redirect_uri = url_for('auth_google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def auth_google_callback():
    if not oauth or not app.config['GOOGLE_CLIENT_ID'] or not app.config['GOOGLE_CLIENT_SECRET']:
        return "OAuth Google não configurado", 400
    token = oauth.google.authorize_access_token()
    userinfo = oauth.google.parse_id_token(token)
    email = (userinfo.get('email') or '').strip().lower()
    if not email:
        return "Email não disponível", 400
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)
        user.set_password(os.urandom(12).hex())
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
