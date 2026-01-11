from flask import Flask, render_template_string, request, redirect, session
import sqlite3
from collections import Counter
from urllib.parse import quote_plus

# ================== APP ==================
app = Flask(__name__)
app.secret_key = 'segredo123'
DB = 'agenda.db'

# ================== BANCO ==================
def get_db():
    return sqlite3.connect(DB)

with get_db() as con:
    con.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        senha TEXT
    );

    CREATE TABLE IF NOT EXISTS horarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hora TEXT,
        user_id INTEGER
    );

    CREATE TABLE IF NOT EXISTS agendamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        data TEXT,
        hora TEXT,
        user_id INTEGER
    );
    """)

    existe = con.execute(
        "SELECT id FROM usuarios WHERE usuario='samuka'"
    ).fetchone()

    if not existe:
        con.execute(
            "INSERT INTO usuarios (usuario, senha) VALUES ('samuka','123')"
        )

# ================== TEMPLATE BASE ==================
base = """
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>{{title}}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body { background:#000; color:#fff; }
.card { background:#111; border:1px solid #222; }
.navbar { background:#000; }
</style>
</head>
<body>

<nav class="navbar px-3">
<span class="navbar-brand text-white">AgendaBarber</span>
{% if session.get('user') %}
<a href="/logout" class="btn btn-danger btn-sm">Sair</a>
{% endif %}
</nav>

<div class="container mt-4">
{{content|safe}}
</div>

</body>
</html>
"""

# ================== LOGIN ==================
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['usuario']
        s = request.form['senha']

        cur = get_db().cursor()
        user = cur.execute(
            "SELECT id FROM usuarios WHERE usuario=? AND senha=?",
            (u, s)
        ).fetchone()

        if user:
            session['user'] = user[0]
            return redirect('/dashboard')

    return render_template_string(base, title="Login", content="""
    <form method="post" class="card p-4 col-md-4 mx-auto">
        <h4 class="text-center">Login</h4>
        <input name="usuario" class="form-control mb-2" placeholder="Usuário" required>
        <input name="senha" type="password" class="form-control mb-3" placeholder="Senha" required>
        <button class="btn btn-light w-100">Entrar</button>
    </form>
    """)

# ================== DASHBOARD ==================
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')

    cur = get_db().cursor()
    dados = cur.execute(
        "SELECT data FROM agendamentos WHERE user_id=?",
        (session['user'],)
    ).fetchall()

    cont = Counter([d[0] for d in dados])
    cards = ""

    for dia, qtd in cont.items():
        cards += f"""
        <div class="col card p-3 text-center">
            {dia}<br><b>{qtd}</b> horários
        </div>
        """

    return render_template_string(base, title="Painel", content=f"""
    <div class="row g-3 mb-4">{cards}</div>
    <div class="row g-3">
        <a class="btn btn-success col" href="/agendar">Novo Horário</a>
        <a class="btn btn-warning col" href="/horarios">Horários</a>
        <a class="btn btn-info col" href="/agenda">Agenda</a>
    </div>
    """)

# ================== HORÁRIOS ==================
@app.route('/horarios', methods=['GET', 'POST'])
def horarios():
    if 'user' not in session:
        return redirect('/')

    if request.method == 'POST':
        with get_db() as con:
            con.execute(
                "INSERT INTO horarios (hora, user_id) VALUES (?,?)",
                (request.form['hora'], session['user'])
            )

    cur = get_db().cursor()
    hrs = cur.execute(
        "SELECT hora FROM horarios WHERE user_id=?",
        (session['user'],)
    ).fetchall()

    lista = "".join([
        f"<li class='list-group-item bg-dark text-white'>{h[0]}</li>"
        for h in hrs
    ])

    return render_template_string(base, title="Horários", content=f"""
    <form method="post" class="card p-3 mb-3">
        <input type="time" name="hora" class="form-control mb-2" required>
        <button class="btn btn-success">Adicionar</button>
    </form>
    <ul class="list-group">{lista}</ul>
    """)

# ================== AGENDA ==================
@app.route('/agenda')
def agenda():
    if 'user' not in session:
        return redirect('/')

    cur = get_db().cursor()
    ag = cur.execute(
        "SELECT id, cliente, data, hora FROM agendamentos WHERE user_id=?",
        (session['user'],)
    ).fetchall()

    rows = ""
    for a in ag:
        msg = quote_plus(f"Olá {a[1]}, seu horário está marcado para {a[2]} às {a[3]}")
        rows += f"""
        <tr>
            <td>{a[1]}</td>
            <td>{a[2]}</td>
            <td>{a[3]}</td>
            <td>
                <a class="btn btn-sm btn-danger" href="/cancelar/{a[0]}">Cancelar</a>
                <a class="btn btn-sm btn-success" target="_blank"
                   href="https://wa.me/?text={msg}">WhatsApp</a>
            </td>
        </tr>
        """

    return render_template_string(base, title="Agenda", content=f"""
    <table class="table table-dark table-striped">
        <tr>
            <th>Cliente</th>
            <th>Data</th>
            <th>Hora</th>
            <th>Ações</th>
        </tr>
        {rows}
    </table>
    """)

# ================== CLIENTE (LINK PÚBLICO) ==================
@app.route('/cliente', methods=['GET', 'POST'])
def cliente():
    con = get_db()
    cur = con.cursor()

    # horários cadastrados
    horas = cur.execute(
        "SELECT hora FROM horarios WHERE user_id=1"
    ).fetchall()

    erro = None

    if request.method == 'POST':
        cliente_nome = request.form['cliente']
        data = request.form['data']
        hora = request.form['hora']

        # 🔒 VERIFICA SE JÁ EXISTE AGENDAMENTO
        existe = cur.execute("""
            SELECT id FROM agendamentos
            WHERE data=? AND hora=? AND user_id=1
        """, (data, hora)).fetchone()

        if existe:
            erro = "⚠️ Esse horário já está ocupado. Escolha outro."
        else:
            con.execute("""
                INSERT INTO agendamentos (cliente, data, hora, user_id)
                VALUES (?,?,?,1)
            """, (cliente_nome, data, hora))
            con.commit()

            return render_template_string(base, title="Agendado", content="""
            <div class="card p-4 text-center">
                <h3>Horário agendado com sucesso ✅</h3>
            </div>
            """)

    options = "".join([f"<option>{h[0]}</option>" for h in horas])

    alerta = f"<div class='alert alert-danger'>{erro}</div>" if erro else ""

    return render_template_string(base, title="Agendar", content=f"""
    <form method="post" class="card p-4 col-md-4 mx-auto">
        <h4 class="text-center">Agendar horário</h4>
        {alerta}
        <input name="cliente" class="form-control mb-2" placeholder="Seu nome" required>
        <input type="date" name="data" class="form-control mb-2" required>
        <select name="hora" class="form-control mb-3" required>
            {options}
        </select>
        <button class="btn btn-success w-100">Agendar</button>
    </form>
    """)

# ================== CANCELAR ==================
@app.route('/cancelar/<int:id>')
def cancelar(id):
    with get_db() as con:
        con.execute("DELETE FROM agendamentos WHERE id=?", (id,))
    return redirect('/agenda')

# ================== LOGOUT ==================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ================== RUN ==================
if __name__ == '__main__':
    app.run(debug=True)
