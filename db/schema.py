import sqlite3

conn = sqlite3.connect('TorneiosData.db')
cursor = conn.cursor()

# Ativa suporte a chaves estrangeiras no SQLite
cursor.execute('PRAGMA foreign_keys = ON')

# ------------------------------------------------------------
# MODALIDADE
# ------------------------------------------------------------
cursor.execute('''
CREATE TABLE IF NOT EXISTS Modalidade (
    Id    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    Nome  TEXT    NOT NULL UNIQUE,
    Ativo INTEGER NOT NULL DEFAULT 1
);
''')

# ------------------------------------------------------------
# PESSOA
# Cadastro base de atletas e treinadores
# ------------------------------------------------------------
cursor.execute('''
CREATE TABLE IF NOT EXISTS Pessoa (
    Id              INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    NomeCompleto    TEXT    NOT NULL,
    CPF             TEXT    NOT NULL UNIQUE,
    DataNascimento  TEXT    NOT NULL,
    Email           TEXT,
    Telefone        TEXT,
    TipoPessoa      TEXT    NOT NULL CHECK (TipoPessoa IN ('ATLETA', 'TREINADOR')),
    NumeroSerie     TEXT    UNIQUE,
    CriadoEm        TEXT    NOT NULL DEFAULT (datetime('now'))
);
''')

# ------------------------------------------------------------
# PESSOA_MODALIDADE
# Uma pessoa pode praticar várias modalidades
# ------------------------------------------------------------
cursor.execute('''
CREATE TABLE IF NOT EXISTS PessoaModalidade (
    Id          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    PessoaId    INTEGER NOT NULL,
    ModalidadeId INTEGER NOT NULL,
    FOREIGN KEY (PessoaId)     REFERENCES Pessoa(Id),
    FOREIGN KEY (ModalidadeId) REFERENCES Modalidade(Id),
    UNIQUE (PessoaId, ModalidadeId)
);
''')

# ------------------------------------------------------------
# TORNEIO
# ------------------------------------------------------------
cursor.execute('''
CREATE TABLE IF NOT EXISTS Torneio (
    Id           INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    Nome         TEXT    NOT NULL,
    Descricao    TEXT,
    DataInicio   TEXT,
    DataFim      TEXT,
    ModalidadeId INTEGER,
    Status       TEXT    NOT NULL DEFAULT 'aberto'
                         CHECK (Status IN ('aberto', 'em_andamento', 'encerrado')),
    CriadoEm    TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (ModalidadeId) REFERENCES Modalidade(Id)
);
''')

# ------------------------------------------------------------
# TIME
# ------------------------------------------------------------
cursor.execute('''
CREATE TABLE IF NOT EXISTS Time (
    Id           INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    Nome         TEXT    NOT NULL,
    ModalidadeId INTEGER NOT NULL,
    TreinadorId  INTEGER NOT NULL,
    CriadoEm     TEXT    NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (ModalidadeId)
        REFERENCES Modalidade(Id),

    FOREIGN KEY (TreinadorId)
        REFERENCES Pessoa(Id)
);
''')

# ------------------------------------------------------------
# TIME_ATLETA
# ------------------------------------------------------------
cursor.execute('''
CREATE TABLE IF NOT EXISTS TimeAtleta (
    Id       INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    TimeId   INTEGER NOT NULL,
    PessoaId INTEGER NOT NULL,

    FOREIGN KEY (TimeId)
        REFERENCES Time(Id),

    FOREIGN KEY (PessoaId)
        REFERENCES Pessoa(Id)
);
''')

# ------------------------------------------------------------
# INSCRICAO_TIME_TORNEIO
# Vincula um time a um torneio
# ------------------------------------------------------------
cursor.execute('''
CREATE TABLE IF NOT EXISTS InscricaoTimeTorneio (
    Id               INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    TorneioId        INTEGER NOT NULL,
    TimeId           INTEGER NOT NULL,
    DataInscricao    TEXT    NOT NULL DEFAULT (datetime('now')),
    StatusInscricao  TEXT    NOT NULL DEFAULT 'pendente'
                             CHECK (StatusInscricao IN ('pendente', 'confirmada', 'cancelada')),
    FOREIGN KEY (TorneioId) REFERENCES Torneio(Id),
    FOREIGN KEY (TimeId)    REFERENCES Time(Id),
    UNIQUE (TorneioId, TimeId)
);
''')

# ------------------------------------------------------------
# MEMBRO_INSCRICAO
# Atletas e treinadores vinculados a um time num torneio
# ------------------------------------------------------------
cursor.execute('''
CREATE TABLE IF NOT EXISTS MembroInscricao (
    Id               INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    InscricaoTimeId  INTEGER NOT NULL,
    PessoaId         INTEGER NOT NULL,
    NumeroCamisa     INTEGER CHECK (NumeroCamisa >= 0),
    Posicao          TEXT,
    Titular          INTEGER NOT NULL DEFAULT 0,
    Ativo            INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (InscricaoTimeId) REFERENCES InscricaoTimeTorneio(Id),
    FOREIGN KEY (PessoaId)        REFERENCES Pessoa(Id)
);
''')

# ============================================================
# DADOS INICIAIS: MODALIDADES
# ============================================================
modalidades = [
    ('Futebol',),
    ('Futsal',),
    ('Voleibol',),
    ('Basquetebol',),
    ('Handebol',),
    ('Atletismo',),
    ('Natação',),
    ('Rugby',),
    ('Tênis de Mesa',),
    ('Badminton',),
]

#Sessão de análise: vincula um vídeo a um torneio/time
cursor.execute('''
CREATE TABLE IF NOT EXISTS SessaoVideo (
    Id          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    Titulo      TEXT    NOT NULL,
    CaminhoVideo TEXT,
    CaminhoAudio TEXT,
    TimeId      INTEGER,
    TorneioId   INTEGER,
    CriadoEm   TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (TimeId)    REFERENCES Time(Id),
    FOREIGN KEY (TorneioId) REFERENCES Torneio(Id)
);
''')

#Integrantes vinculados à sessão
cursor.execute('''
CREATE TABLE IF NOT EXISTS SessaoIntegrante (
    Id          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    SessaoId    INTEGER NOT NULL,
    PessoaId    INTEGER NOT NULL,
    UNIQUE (SessaoId, PessoaId),
    FOREIGN KEY (SessaoId)  REFERENCES SessaoVideo(Id),
    FOREIGN KEY (PessoaId)  REFERENCES Pessoa(Id)
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS BotaoReacao (
    Id      INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    Rotulo  TEXT    NOT NULL UNIQUE,
    Cor     TEXT    NOT NULL DEFAULT '#1f6aa5',
    Icone   TEXT
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Marcacao (
    Id          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    SessaoId    INTEGER NOT NULL,
    SegundoMarca REAL   NOT NULL,           -- tempo exato em segundos
    Descricao   TEXT,
    BotaoId     INTEGER,                    -- reação de botão (opcional)
    CriadoEm   TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (SessaoId) REFERENCES SessaoVideo(Id),
    FOREIGN KEY (BotaoId)  REFERENCES BotaoReacao(Id)
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS MarcacaoIntegrante (
    Id          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    MarcacaoId  INTEGER NOT NULL,
    PessoaId    INTEGER NOT NULL,
    FOREIGN KEY (MarcacaoId) REFERENCES Marcacao(Id),
    FOREIGN KEY (PessoaId)   REFERENCES Pessoa(Id)
);

''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS MarcacaoConexao (
    Id          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    MarcacaoId  INTEGER NOT NULL,
    PessoaId1   INTEGER NOT NULL,
    PessoaId2   INTEGER NOT NULL,
    TipoReacao  TEXT,
    FOREIGN KEY (MarcacaoId) REFERENCES Marcacao(Id),
    FOREIGN KEY (PessoaId1)  REFERENCES Pessoa(Id),
    FOREIGN KEY (PessoaId2)  REFERENCES Pessoa(Id)
);
''')

cursor.execute('''
// Dados iniciais: botões padrão
INSERT OR IGNORE INTO BotaoReacao (Rotulo, Cor) VALUES
    ('👍 Positivo',          '#2d6a4f'),
    ('👎 Negativo',          '#c0392b'),
    ('💬 Conversa Paralela', '#1f6aa5'),
    ('😠 Conflito',          '#e67e22'),
    ('🤝 Colaboração',       '#8e44ad'),
    ('❓ Dúvida',            '#7f8c8d');
''')

cursor.executemany('''
    INSERT OR IGNORE INTO Modalidade (Nome) VALUES (?)
''', modalidades)

conn.commit()
print("Banco criado e conectado com sucesso.")
conn.close()
