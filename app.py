from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import banco
import models

app = Flask(__name__)
app.secret_key = 'chave_secreta_barbearia_2025'

# Inicializar banco de dados
banco.inicializar_banco()

@app.context_processor
def inject_datetime():
    """Injeta datetime e timedelta nos templates"""
    return dict(datetime=datetime, timedelta=timedelta)

@app.context_processor
def inject_configuracoes():
    """Injeta configurações da barbearia em todos os templates"""
    configuracoes = models.obter_configuracoes_barbearia()
    return dict(configuracoes_barbearia=configuracoes)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        
        usuario = models.buscar_usuario_por_email(email)
        
        if usuario and check_password_hash(usuario[3], senha):
            session['usuario_id'] = usuario[0]
            session['nome_usuario'] = usuario[1]
            session['tipo_usuario'] = usuario[7]
            
            if usuario[7] == 'admin':
                return redirect(url_for('dashboard_admin'))
            elif usuario[7] == 'funcionario':
                return redirect(url_for('dashboard_funcionario'))
            else:
                return redirect(url_for('dashboard_cliente'))
        else:
            flash('Email ou senha incorretos!', 'erro')
    
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']
        whatsapp = request.form['whatsapp']
        senha = request.form['senha']
        tipo = request.form.get('tipo', 'cliente')
        
        if models.buscar_usuario_por_email(email):
            flash('Este email já está cadastrado!', 'erro')
            return render_template('cadastro.html')
        
        senha_hash = generate_password_hash(senha)
        usuario_id = models.criar_usuario(nome, email, senha_hash, telefone, whatsapp, tipo)
        
        if usuario_id:
            flash('Cadastro realizado com sucesso!', 'sucesso')
            return redirect(url_for('login'))
        else:
            flash('Erro ao realizar cadastro!', 'erro')
    
    return render_template('cadastro.html')

@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form['telefone']
        whatsapp = request.form['whatsapp']
        
        models.atualizar_perfil_usuario(session['usuario_id'], nome, telefone, whatsapp)
        session['nome_usuario'] = nome
        flash('Perfil atualizado com sucesso!', 'sucesso')
        
        return redirect(url_for('perfil'))
    
    usuario = models.obter_usuario_por_id(session['usuario_id'])
    fidelidade = None
    
    if session['tipo_usuario'] == 'cliente':
        fidelidade = models.obter_fidelidade_cliente(session['usuario_id'])
    
    return render_template('perfil.html', usuario=usuario, fidelidade=fidelidade)

@app.route('/dashboard_admin')
def dashboard_admin():
    if 'usuario_id' not in session or session['tipo_usuario'] != 'admin':
        return redirect(url_for('login'))
    
    estatisticas = models.obter_estatisticas_admin()
    funcionarios = models.listar_funcionarios()
    agendamentos_pendentes = models.listar_agendamentos_por_status('aguardando_confirmacao')
    clientes = models.listar_clientes_detalhado()
    
    return render_template('dashboard_admin.html', 
                         estatisticas=estatisticas,
                         funcionarios=funcionarios,
                         agendamentos_pendentes=agendamentos_pendentes,
                         clientes=clientes)

@app.route('/dashboard_funcionario')
def dashboard_funcionario():
    if 'usuario_id' not in session or session['tipo_usuario'] != 'funcionario':
        return redirect(url_for('login'))
    
    funcionario_id = models.obter_funcionario_por_usuario(session['usuario_id'])
    if not funcionario_id:
        flash('Funcionário não encontrado!', 'erro')
        return redirect(url_for('login'))
    
    agendamentos = models.listar_agendamentos_funcionario(funcionario_id)
    
    return render_template('dashboard_funcionario.html', agendamentos=agendamentos)

@app.route('/dashboard_cliente')
def dashboard_cliente():
    if 'usuario_id' not in session or session['tipo_usuario'] != 'cliente':
        return redirect(url_for('login'))
    
    agendamentos = models.listar_agendamentos_cliente(session['usuario_id'])
    fidelidade = models.obter_fidelidade_cliente(session['usuario_id'])
    
    return render_template('dashboard_cliente.html', 
                         agendamentos=agendamentos, 
                         fidelidade=fidelidade)

@app.route('/agendamento', methods=['GET', 'POST'])
def agendamento():
    if 'usuario_id' not in session or session['tipo_usuario'] != 'cliente':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        funcionario_id = request.form['funcionario_id']
        servico_id = request.form['servico_id']
        data_hora = request.form['data_hora']
        usar_corte_gratuito = 'usar_corte_gratuito' in request.form
        
        # Verificar se horário está disponível
        if not models.verificar_horario_disponivel(funcionario_id, data_hora):
            flash('Este horário não está mais disponível!', 'erro')
            return redirect(url_for('agendamento'))
        
        # Criar agendamento
        agendamento_id = models.criar_agendamento(
            session['usuario_id'], funcionario_id, servico_id, data_hora, usar_corte_gratuito
        )
        
        if agendamento_id:
            if usar_corte_gratuito:
                # Confirmar automaticamente se for corte gratuito
                models.atualizar_status_agendamento(agendamento_id, 'confirmado')
                flash('Agendamento confirmado! Corte gratuito utilizado.', 'sucesso')
                return redirect(url_for('dashboard_cliente'))
            else:
                flash('Agendamento criado! Sua reserva só será confirmada após o pagamento via PIX.', 'info')
                return redirect(url_for('pagamento_pix', agendamento_id=agendamento_id))
        else:
            flash('Erro ao criar agendamento. Tente novamente.', 'erro')
    
    funcionarios = models.listar_funcionarios()
    servicos = models.listar_servicos()
    fidelidade = models.obter_fidelidade_cliente(session['usuario_id'])
    
    return render_template('agendamento.html', 
                         funcionarios=funcionarios, 
                         servicos=servicos,
                         fidelidade=fidelidade)

@app.route('/api/horarios_disponiveis')
def api_horarios_disponiveis():
    """API para verificar horários disponíveis"""
    funcionario_id = request.args.get('funcionario_id')
    data = request.args.get('data')
    
    if funcionario_id and data:
        horarios_ocupados = models.obter_horarios_ocupados(funcionario_id, data)
        
        # Gerar horários disponíveis (8h às 18h, intervalos de 30min)
        horarios_disponiveis = []
        hora_inicio = 8
        hora_fim = 18
        
        for hora in range(hora_inicio, hora_fim):
            for minuto in [0, 30]:
                horario = f"{hora:02d}:{minuto:02d}"
                if horario not in horarios_ocupados:
                    horarios_disponiveis.append(horario)
        
        return jsonify({'horarios_disponiveis': horarios_disponiveis})
    
    return jsonify({'horarios_disponiveis': []})

@app.route('/pagamento_pix/<int:agendamento_id>')
def pagamento_pix(agendamento_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    agendamento = models.obter_agendamento_completo(agendamento_id)
    if not agendamento or agendamento[1] != session['usuario_id']:
        flash('Agendamento não encontrado!', 'erro')
        return redirect(url_for('dashboard_cliente'))
    
    configuracoes = models.obter_configuracoes_barbearia()
    chave_pix = configuracoes['whatsapp_contato'] if configuracoes else "11999999999"
    
    return render_template('pagamento_pix.html', 
                         agendamento=agendamento, 
                         chave_pix=chave_pix)

@app.route('/confirmar_pagamento/<int:agendamento_id>')
def confirmar_pagamento(agendamento_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    agendamento = models.obter_agendamento_completo(agendamento_id)
    if not agendamento or agendamento[1] != session['usuario_id']:
        flash('Agendamento não encontrado!', 'erro')
        return redirect(url_for('dashboard_cliente'))
    
    models.atualizar_status_agendamento(agendamento_id, 'aguardando_confirmacao')
    flash('Pagamento informado! Aguarde a confirmação do administrador.', 'sucesso')
    
    return redirect(url_for('dashboard_cliente'))

@app.route('/confirmar_agendamento/<int:agendamento_id>')
def confirmar_agendamento(agendamento_id):
    if 'usuario_id' not in session or session['tipo_usuario'] != 'admin':
        return redirect(url_for('login'))
    
    models.atualizar_status_agendamento(agendamento_id, 'confirmado')
    flash('Agendamento confirmado com sucesso!', 'sucesso')
    
    return redirect(url_for('dashboard_admin'))

@app.route('/cancelar_agendamento/<int:agendamento_id>')
def cancelar_agendamento(agendamento_id):
    if 'usuario_id' not in session or session['tipo_usuario'] != 'admin':
        return redirect(url_for('login'))
    
    models.atualizar_status_agendamento(agendamento_id, 'cancelado')
    flash('Agendamento cancelado. O horário foi liberado.', 'sucesso')
    
    return redirect(url_for('dashboard_admin'))

@app.route('/concluir_atendimento/<int:agendamento_id>')
def concluir_atendimento(agendamento_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Verificar se é admin ou funcionário responsável
    if session['tipo_usuario'] == 'funcionario':
        funcionario_id = models.obter_funcionario_por_usuario(session['usuario_id'])
        agendamento = models.obter_agendamento_completo(agendamento_id)
        if not agendamento or agendamento[5] != funcionario_id:
            flash('Você não tem permissão para concluir este atendimento!', 'erro')
            return redirect(url_for('dashboard_funcionario'))
    elif session['tipo_usuario'] != 'admin':
        return redirect(url_for('login'))
    
    models.atualizar_status_agendamento(agendamento_id, 'concluido')
    flash('Atendimento concluído! Fidelidade do cliente atualizada.', 'sucesso')
    
    if session['tipo_usuario'] == 'admin':
        return redirect(url_for('dashboard_admin'))
    else:
        return redirect(url_for('dashboard_funcionario'))

@app.route('/gerenciar_funcionarios')
def gerenciar_funcionarios():
    if 'usuario_id' not in session or session['tipo_usuario'] != 'admin':
        return redirect(url_for('login'))
    
    funcionarios = models.listar_funcionarios_detalhado()
    return render_template('gerenciar_funcionarios.html', funcionarios=funcionarios)

@app.route('/adicionar_funcionario', methods=['POST'])
def adicionar_funcionario():
    if 'usuario_id' not in session or session['tipo_usuario'] != 'admin':
        return redirect(url_for('login'))
    
    nome = request.form['nome']
    email = request.form['email']
    telefone = request.form['telefone']
    whatsapp = request.form['whatsapp']
    senha = request.form['senha']
    valor_corte = float(request.form['valor_corte'])
    tipo_pagamento = request.form['tipo_pagamento']
    
    if models.buscar_usuario_por_email(email):
        flash('Este email já está cadastrado!', 'erro')
        return redirect(url_for('gerenciar_funcionarios'))
    
    senha_hash = generate_password_hash(senha)
    usuario_id = models.criar_usuario(nome, email, senha_hash, telefone, whatsapp, 'funcionario')
    
    if usuario_id:
        models.criar_funcionario(usuario_id, valor_corte, tipo_pagamento)
        flash('Funcionário adicionado com sucesso!', 'sucesso')
    else:
        flash('Erro ao adicionar funcionário!', 'erro')
    
    return redirect(url_for('gerenciar_funcionarios'))

@app.route('/clientes')
def listar_clientes():
    if 'usuario_id' not in session or session['tipo_usuario'] != 'admin':
        return redirect(url_for('login'))
    
    clientes = models.listar_clientes_detalhado()
    return render_template('clientes.html', clientes=clientes)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)