import sqlite3
from contextlib import contextmanager

BANCO_NOME = 'barbearia.db'

@contextmanager
def obter_conexao():
    """Context manager para conexões com o banco"""
    conn = sqlite3.connect(BANCO_NOME, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=1000')
    conn.execute('PRAGMA temp_store=MEMORY')
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def inicializar_banco():
    """Cria todas as tabelas necessárias"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        
        # Tabela de usuários com campos adicionais
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                telefone TEXT,
                whatsapp TEXT,
                foto_perfil TEXT DEFAULT '/static/uploads/default-user.jpg',
                tipo TEXT NOT NULL DEFAULT 'cliente',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de funcionários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS funcionarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                valor_corte DECIMAL(10,2) NOT NULL,
                tipo_pagamento TEXT NOT NULL DEFAULT 'fixo',
                ativo BOOLEAN DEFAULT 1,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        ''')
        
        # Tabela de serviços
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS servicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco DECIMAL(10,2) NOT NULL,
                duracao INTEGER NOT NULL,
                ativo BOOLEAN DEFAULT 1
            )
        ''')
        
        # Tabela de agendamentos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                funcionario_id INTEGER NOT NULL,
                servico_id INTEGER NOT NULL,
                data_hora TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'pendente',
                valor DECIMAL(10,2),
                observacoes TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES usuarios (id),
                FOREIGN KEY (funcionario_id) REFERENCES funcionarios (id),
                FOREIGN KEY (servico_id) REFERENCES servicos (id)
            )
        ''')
        
        # Tabela de programa de fidelidade
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fidelidade (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                cortes_realizados INTEGER DEFAULT 0,
                cortes_gratuitos_disponiveis INTEGER DEFAULT 0,
                data_ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES usuarios (id),
                UNIQUE(cliente_id)
            )
        ''')
        
        # Tabela de configurações da barbearia
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_barbearia TEXT DEFAULT 'Barbearia Premium',
                logo_url TEXT DEFAULT '/static/uploads/logo-barbearia.jpg',
                telefone_contato TEXT,
                whatsapp_contato TEXT,
                endereco TEXT,
                horario_funcionamento TEXT DEFAULT '08:00-18:00',
                dias_funcionamento TEXT DEFAULT 'Segunda a Sábado',
                descricao TEXT DEFAULT 'A melhor barbearia da cidade',
                instagram TEXT,
                facebook TEXT
            )
        ''')
        
        conn.commit()
        
        # Inserir dados iniciais
        inserir_dados_iniciais(cursor, conn)

def inserir_dados_iniciais(cursor, conn):
    """Insere dados iniciais no banco"""
    from werkzeug.security import generate_password_hash
    
    # Verificar se já existem dados
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] > 0:
        return  # Dados já existem
    
    # Usuário administrador padrão
    senha_admin = generate_password_hash('admin123')
    cursor.execute('''
        INSERT INTO usuarios (nome, email, senha, telefone, whatsapp, tipo)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('Administrador', 'admin@barbearia.com', senha_admin, '(11) 99999-9999', '11999999999', 'admin'))
    
    # Serviços padrão
    servicos_padrao = [
        ('Corte Masculino', 25.00, 30),
        ('Barba', 15.00, 20),
        ('Corte + Barba', 35.00, 45),
        ('Sobrancelha', 10.00, 15),
        ('Lavagem + Corte', 30.00, 40)
    ]
    
    cursor.executemany('''
        INSERT INTO servicos (nome, preco, duracao)
        VALUES (?, ?, ?)
    ''', servicos_padrao)
    
    # Configurações iniciais da barbearia
    cursor.execute('''
        INSERT INTO configuracoes (nome_barbearia, telefone_contato, whatsapp_contato, endereco, descricao)
        VALUES (?, ?, ?, ?, ?)
    ''', ('Barbearia Premium', '(11) 3333-4444', '11333344444', 'Rua das Flores, 123 - Centro', 'A melhor barbearia da cidade com profissionais qualificados'))
    
    conn.commit()