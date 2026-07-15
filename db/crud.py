import sqlite3
from datetime import date
import random
import string

DB_PATH = 'TorneiosData.db'

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.row_factory = sqlite3.Row  # retorna dicionários em vez de tuplas
    return conn


# ============================================================
# MODALIDADE
# ============================================================

def listar_modalidades(apenas_ativas=True):
    with get_conn() as conn:
        if apenas_ativas:
            rows = conn.execute(
                'SELECT * FROM Modalidade WHERE Ativo = 1 ORDER BY Nome'
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT * FROM Modalidade ORDER BY Nome'
            ).fetchall()
        return [dict(r) for r in rows]


def adicionar_modalidade(nome):
    with get_conn() as conn:
        conn.execute(
            'INSERT INTO Modalidade (Nome) VALUES (?)', (nome,)
        )
    print(f"Modalidade '{nome}' adicionada.")


def desativar_modalidade(modalidade_id):
    with get_conn() as conn:
        conn.execute(
            'UPDATE Modalidade SET Ativo = 0 WHERE Id = ?', (modalidade_id,)
        )
    print(f"Modalidade {modalidade_id} desativada.")


# ============================================================
# PESSOA
# ============================================================
def cadastrar_pessoa(nome, cpf, nascimento, email=None, telefone=None, tipo="ATLETA", numero_serie=None):
    with get_conn() as conn:
        cursor = conn.execute('''
            INSERT INTO Pessoa (NomeCompleto, CPF, DataNascimento, Email, Telefone, TipoPessoa, NumeroSerie)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (nome, cpf, nascimento, email, telefone, tipo, numero_serie))
        return cursor.lastrowid


def buscar_pessoa_por_cpf(cpf):
    with get_conn() as conn:
        row = conn.execute(
            'SELECT * FROM Pessoa WHERE CPF = ?', (cpf.strip(),)
        ).fetchone()
        return dict(row) if row else None


def buscar_pessoa_por_id(pessoa_id):
    with get_conn() as conn:
        row = conn.execute(
            'SELECT * FROM Pessoa WHERE Id = ?', (pessoa_id,)
        ).fetchone()
        return dict(row) if row else None


def listar_pessoas():
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM Pessoa ORDER BY NomeCompleto'
        ).fetchall()
        return [dict(r) for r in rows]


def atualizar_pessoa(pessoa_id, nome_completo=None, data_nascimento=None, email=None, telefone=None):
    pessoa = buscar_pessoa_por_id(pessoa_id)
    if not pessoa:
        print(f"Pessoa {pessoa_id} não encontrada.")
        return

    novo_nome      = nome_completo    or pessoa['NomeCompleto']
    novo_nasc      = data_nascimento  or pessoa['DataNascimento']
    novo_email     = email            or pessoa['Email']
    novo_telefone  = telefone         or pessoa['Telefone']

    with get_conn() as conn:
        conn.execute('''
            UPDATE Pessoa
            SET NomeCompleto   = ?,
                DataNascimento = ?,
                Email          = ?,
                Telefone       = ?
            WHERE Id = ?
        ''', (novo_nome, novo_nasc, novo_email, novo_telefone, pessoa_id))
    print(f"Pessoa {pessoa_id} atualizada.")


def buscar_historico_atleta(pessoa_id):
    """Retorna os times e torneios vinculados a um atleta"""
    with get_conn() as conn:
        # Busca times fixos
        times = conn.execute('''
            SELECT t.Nome, m.Nome as Modalidade 
            FROM Time t 
            JOIN TimeAtleta ta ON t.Id = ta.TimeId 
            JOIN Modalidade m ON t.ModalidadeId = m.Id
            WHERE ta.PessoaId = ?
        ''', (pessoa_id,)).fetchall()
        
        # Busca participações em torneios
        torneios = conn.execute('''
            SELECT tr.Nome as Torneio, ti.Nome as TimeNome
            FROM MembroInscricao mi
            JOIN InscricaoTimeTorneio itt ON mi.InscricaoTimeId = itt.Id
            JOIN Torneio tr ON itt.TorneioId = tr.Id
            JOIN Time ti ON itt.TimeId = ti.Id
            WHERE mi.PessoaId = ? AND mi.Ativo = 1
        ''', (pessoa_id,)).fetchall()
        
        return [dict(r) for r in times], [dict(r) for r in torneios]

def buscar_times_treinados(pessoa_id):
    """Retorna os times que um treinador comanda"""
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT t.Nome, m.Nome as Modalidade 
            FROM Time t
            JOIN Modalidade m ON t.ModalidadeId = m.Id
            WHERE t.TreinadorId = ?
        ''', (pessoa_id,)).fetchall()
        return [dict(r) for r in rows]


def gerar_numero_serie():
    """
    Gera um número de série único no formato:
    2 dígitos + 1 letra + 3 dígitos  →  ex: 47B293, 12A804
    Garante que não existe no banco antes de retornar.
    """
    with get_conn() as conn:
        while True:
            parte1  = ''.join(random.choices(string.digits, k=2))
            letra   = random.choice(string.ascii_uppercase)
            parte2  = ''.join(random.choices(string.digits, k=3))
            serie   = f"{parte1}{letra}{parte2}"           # ex: 47B293

            existe = conn.execute(
                'SELECT 1 FROM Pessoa WHERE NumeroSerie = ?', (serie,)
            ).fetchone()

            if not existe:
                return serie


def buscar_por_serie(numero_serie):
    """Busca uma pessoa pelo número de série."""
    with get_conn() as conn:
        row = conn.execute(
            'SELECT * FROM Pessoa WHERE NumeroSerie = ?', (numero_serie.upper().strip(),)
        ).fetchone()
        return dict(row) if row else None

# ============================================================
# PESSOA <-> MODALIDADE
# ============================================================

def vincular_modalidade_pessoa(pessoa_id, modalidade_id):
    with get_conn() as conn:
        conn.execute('''
            INSERT OR IGNORE INTO PessoaModalidade (PessoaId, ModalidadeId)
            VALUES (?, ?)
        ''', (pessoa_id, modalidade_id))
    print(f"Modalidade {modalidade_id} vinculada à pessoa {pessoa_id}.")


def desvincular_modalidade_pessoa(pessoa_id, modalidade_id):
    with get_conn() as conn:
        conn.execute('''
            DELETE FROM PessoaModalidade
            WHERE PessoaId = ? AND ModalidadeId = ?
        ''', (pessoa_id, modalidade_id))
    print(f"Modalidade {modalidade_id} desvinculada da pessoa {pessoa_id}.")


def listar_modalidades_da_pessoa(pessoa_id):
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT m.Id, m.Nome
            FROM Modalidade m
            JOIN PessoaModalidade pm ON pm.ModalidadeId = m.Id
            WHERE pm.PessoaId = ?
            ORDER BY m.Nome
        ''', (pessoa_id,)).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# TORNEIO
# ============================================================

def criar_torneio(nome, descricao, data_inicio, data_fim, modalidade_id):
    status = calcular_status_torneio(data_inicio, data_fim)

    with get_conn() as conn:
        cursor = conn.execute('''
            INSERT INTO Torneio (Nome, Descricao, DataInicio, DataFim, ModalidadeId, Status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nome, descricao, data_inicio, data_fim, modalidade_id, status))
        return cursor.lastrowid


def listar_torneios(status=None):
    with get_conn() as conn:
        if status:
            rows = conn.execute('''
                SELECT t.*, m.Nome AS NomeModalidade
                FROM Torneio t
                LEFT JOIN Modalidade m ON m.Id = t.ModalidadeId
                WHERE t.Status = ?
                ORDER BY t.DataInicio
            ''', (status,)).fetchall()
        else:
            rows = conn.execute('''
                SELECT t.*, m.Nome AS NomeModalidade
                FROM Torneio t
                LEFT JOIN Modalidade m ON m.Id = t.ModalidadeId
                ORDER BY t.DataInicio
            ''').fetchall()
        return [dict(r) for r in rows]


def calcular_status_torneio(data_inicio, data_fim):
    """
    Calcula o status do torneio comparando com a data atual.
    - Sem datas definidas      → aberto
    - Hoje < data_inicio       → aberto
    - data_inicio <= hoje <= data_fim → em_andamento
    - Hoje > data_fim          → encerrado
    """
    hoje = date.today()

    if not data_inicio or not data_fim:
        return "aberto"

    try:
        inicio = date.fromisoformat(data_inicio)
        fim    = date.fromisoformat(data_fim)
    except ValueError:
        return "aberto"

    if hoje < inicio:
        return "aberto"
    elif inicio <= hoje <= fim:
        return "em_andamento"
    else:
        return "encerrado"


def sincronizar_status_torneios():
    """
    Atualiza o status de todos os torneios no banco com base nas datas.
    Chame isso ao abrir o app.
    """
    with get_conn() as conn:
        torneios = conn.execute(
            'SELECT Id, DataInicio, DataFim FROM Torneio'
        ).fetchall()

        for t in torneios:
            novo_status = calcular_status_torneio(t['DataInicio'], t['DataFim'])
            conn.execute(
                'UPDATE Torneio SET Status = ? WHERE Id = ?',
                (novo_status, t['Id'])
            )
        conn.commit()


def buscar_torneio_por_id(torneio_id):
    with get_conn() as conn:
        row = conn.execute('''
            SELECT t.*, m.Nome AS NomeModalidade
            FROM Torneio t
            LEFT JOIN Modalidade m ON m.Id = t.ModalidadeId
            WHERE t.Id = ?
        ''', (torneio_id,)).fetchone()
        return dict(row) if row else None


# ============================================================
# TIME
# ============================================================

def criar_time(nome, modalidade_id, treinador_id):
    with get_conn() as conn:
        # Verifica se já existe um time com esse nome
        existe = conn.execute(
            'SELECT 1 FROM Time WHERE LOWER(Nome) = LOWER(?)', (nome,)
        ).fetchone()

        if existe:
            raise ValueError(f"Já existe um time com o nome '{nome}'.")

        cursor = conn.execute('''
            INSERT INTO Time (Nome, ModalidadeId, TreinadorId)
            VALUES (?, ?, ?)
        ''', (nome, modalidade_id, treinador_id))

        time_id = cursor.lastrowid

    print(f"Time '{nome}' criado com Id {time_id}.")
    return time_id



def buscar_time_por_id(time_id):
    with get_conn() as conn:
        row = conn.execute(
            'SELECT * FROM Time WHERE Id = ?', (time_id,)
        ).fetchone()
        return dict(row) if row else None


def listar_times():
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT
                t.Id,
                t.Nome,
                t.ModalidadeId,
                m.Nome AS NomeModalidade,
                t.TreinadorId,
                p.NomeCompleto AS NomeTreinador,
                t.CriadoEm
            FROM Time t
            JOIN Modalidade m
                ON m.Id = t.ModalidadeId
            JOIN Pessoa p
                ON p.Id = t.TreinadorId
            ORDER BY t.Nome
        ''').fetchall()

        return [dict(r) for r in rows]

def adicionar_atleta_ao_time(time_id, pessoa_id):
    with get_conn() as conn:
        existe = conn.execute("""
            SELECT 1
            FROM TimeAtleta
            WHERE TimeId = ?
            AND PessoaId = ?
        """, (time_id, pessoa_id)).fetchone()

        if existe:
            return

        conn.execute("""
            INSERT INTO TimeAtleta (
                TimeId,
                PessoaId
            )
            VALUES (?, ?)
        """, (time_id, pessoa_id))

def remover_atleta_do_time(time_id, pessoa_id):
    with get_conn() as conn:
        conn.execute('''
            DELETE FROM TimeAtleta
            WHERE TimeId = ?
              AND PessoaId = ?
        ''', (time_id, pessoa_id))

def listar_atletas_do_time(time_id):
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT
                p.Id,
                p.NomeCompleto,
                p.CPF
            FROM TimeAtleta ta
            JOIN Pessoa p
                ON p.Id = ta.PessoaId
            WHERE ta.TimeId = ?
            ORDER BY p.NomeCompleto
        ''', (time_id,)).fetchall()

        return [dict(r) for r in rows]

def listar_atletas():
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT *
            FROM Pessoa
            WHERE TipoPessoa = 'ATLETA'
            ORDER BY NomeCompleto
        ''').fetchall()

        return [dict(r) for r in rows]
    
# ============================================================
# INSCRIÇÃO: TIME NO TORNEIO
# ============================================================

def inscrever_time(torneio_id, time_id):
    with get_conn() as conn:
        cursor = conn.execute('''
            INSERT INTO InscricaoTimeTorneio (TorneioId, TimeId)
            VALUES (?, ?)
        ''', (torneio_id, time_id))
        inscricao_id = cursor.lastrowid
    print(f"Time {time_id} inscrito no torneio {torneio_id}. InscricaoId: {inscricao_id}.")
    return inscricao_id


def atualizar_status_inscricao(inscricao_id, status):
    opcoes = ('pendente', 'confirmada', 'cancelada')
    if status not in opcoes:
        print(f"Status inválido. Use um de: {opcoes}")
        return
    with get_conn() as conn:
        conn.execute(
            'UPDATE InscricaoTimeTorneio SET StatusInscricao = ? WHERE Id = ?',
            (status, inscricao_id)
        )
    print(f"Inscrição {inscricao_id} atualizada para '{status}'.")


def listar_times_do_torneio(torneio_id):
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT itt.Id AS InscricaoId, itt.StatusInscricao,
                   ti.Id AS TimeId, ti.Nome AS NomeTime
            FROM InscricaoTimeTorneio itt
            JOIN Time ti ON ti.Id = itt.TimeId
            WHERE itt.TorneioId = ?
            ORDER BY ti.Nome
        ''', (torneio_id,)).fetchall()
        return [dict(r) for r in rows]


def buscar_inscricao_por_id(inscricao_id):
    with get_conn() as conn:
        row = conn.execute(
            'SELECT * FROM InscricaoTimeTorneio WHERE Id = ?', (inscricao_id,)
        ).fetchone()
        return dict(row) if row else None


# ============================================================
# MEMBRO: ATLETA OU TREINADOR NA INSCRIÇÃO
# ============================================================

def adicionar_membro(inscricao_time_id, pessoa_id,
                     numero_camisa=None,
                     posicao=None,
                     titular=False):

    inscricao = buscar_inscricao_por_id(inscricao_time_id)

    if not inscricao:
        raise ValueError("Inscrição não encontrada.")

    torneio = buscar_torneio_por_id(inscricao["TorneioId"])

    if not torneio:
        raise ValueError("Torneio não encontrado.")

    modalidade_torneio = torneio["ModalidadeId"]

    modalidades_pessoa = listar_modalidades_da_pessoa(pessoa_id)

    ids_modalidades_pessoa = [
        m["Id"] for m in modalidades_pessoa
    ]

    # valida se a pessoa possui a modalidade do torneio
    if modalidade_torneio not in ids_modalidades_pessoa:
        raise ValueError(
            f"Esta pessoa não possui a modalidade "
            f"'{torneio['NomeModalidade']}' necessária para este torneio."
        )

    with get_conn() as conn:

        # impede adicionar a mesma pessoa duas vezes
        existente = conn.execute('''
            SELECT 1
            FROM MembroInscricao
            WHERE InscricaoTimeId = ?
              AND PessoaId = ?
              AND Ativo = 1
        ''', (
            inscricao_time_id,
            pessoa_id
        )).fetchone()

        if existente:
            raise ValueError(
                "Esta pessoa já foi adicionada a este time."
            )

        cursor = conn.execute('''
            INSERT INTO MembroInscricao
                (
                    InscricaoTimeId,
                    PessoaId,
                    NumeroCamisa,
                    Posicao,
                    Titular
                )
            VALUES (?, ?, ?, ?, ?)
        ''', (
            inscricao_time_id,
            pessoa_id,
            numero_camisa,
            posicao,
            1 if titular else 0
        ))

        membro_id = cursor.lastrowid

    print(
        f"Pessoa {pessoa_id} adicionada na inscrição {inscricao_time_id}."
    )

    return membro_id


def remover_membro(membro_id):
    """Desativa o membro sem deletar o registro."""
    with get_conn() as conn:
        conn.execute(
            'UPDATE MembroInscricao SET Ativo = 0 WHERE Id = ?', (membro_id,)
        )
    print(f"Membro {membro_id} desativado.")

def listar_membros_da_inscricao(inscricao_time_id):
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT
                mi.Id AS MembroId,
                p.TipoPessoa,
                mi.NumeroCamisa,
                mi.Posicao,
                mi.Titular,
                mi.Ativo,
                p.NomeCompleto,
                p.CPF,
                p.DataNascimento
            FROM MembroInscricao mi
            JOIN Pessoa p
                ON p.Id = mi.PessoaId
            WHERE mi.InscricaoTimeId = ?
            ORDER BY p.TipoPessoa, mi.NumeroCamisa
        ''', (inscricao_time_id,)).fetchall()

        return [dict(r) for r in rows]


def listar_treinadores_da_inscricao(inscricao_time_id):
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT mi.Id AS MembroId,
                   p.NomeCompleto, p.CPF, p.DataNascimento
            FROM MembroInscricao mi
            JOIN Pessoa p ON p.Id = mi.PessoaId
            WHERE mi.InscricaoTimeId = ? AND p.TipoPessoa = 'TREINADOR' AND mi.Ativo = 1
        ''', (inscricao_time_id,)).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# CONSULTAS GERAIS (visão completa)
# ============================================================

def ver_torneio_completo(torneio_id):
    """
    Retorna o torneio com todos os times inscritos
    e todos os membros de cada time.
    """
    torneio = buscar_torneio_por_id(torneio_id)
    if not torneio:
        print(f"Torneio {torneio_id} não encontrado.")
        return None

    times = listar_times_do_torneio(torneio_id)
    for time in times:
        time['membros'] = listar_membros_da_inscricao(time['InscricaoId'])

    torneio['times'] = times
    return torneio


#--------------------------------------------------------------------------------------------------------------------------------------------#


# ============================================================
# SESSÃO DE VÍDEO
# ============================================================

def criar_sessao(titulo, caminho_video=None, caminho_audio=None, time_id=None, torneio_id=None):
    with get_conn() as conn:
        cursor = conn.execute('''
            INSERT INTO SessaoVideo (Titulo, CaminhoVideo, CaminhoAudio, TimeId, TorneioId)
            VALUES (?, ?, ?, ?, ?)
        ''', (titulo, caminho_video, caminho_audio, time_id, torneio_id))
        return cursor.lastrowid

def listar_sessoes():
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT sv.*, t.Nome as NomeTime, tr.Nome as NomeTorneio
            FROM SessaoVideo sv
            LEFT JOIN Time t ON sv.TimeId = t.Id
            LEFT JOIN Torneio tr ON sv.TorneioId = tr.Id
            ORDER BY sv.CriadoEm DESC
        ''').fetchall()
        return [dict(r) for r in rows]

def adicionar_integrante_sessao(sessao_id, pessoa_id):
    with get_conn() as conn:
        conn.execute('''
            INSERT OR IGNORE INTO SessaoIntegrante (SessaoId, PessoaId)
            VALUES (?, ?)
        ''', (sessao_id, pessoa_id))

def listar_integrantes_sessao(sessao_id):
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT p.Id, p.NomeCompleto, p.TipoPessoa, p.NumeroSerie
            FROM SessaoIntegrante si
            JOIN Pessoa p ON si.PessoaId = p.Id
            WHERE si.SessaoId = ?
            ORDER BY p.NomeCompleto
        ''', (sessao_id,)).fetchall()
        return [dict(r) for r in rows]

def remover_integrante_sessao(sessao_id, pessoa_id):
    with get_conn() as conn:
        conn.execute('''
            DELETE FROM SessaoIntegrante
            WHERE SessaoId = ? AND PessoaId = ?
        ''', (sessao_id, pessoa_id))

# ============================================================
# BOTÕES DE REAÇÃO
# ============================================================

def listar_botoes():
    with get_conn() as conn:
        rows = conn.execute('SELECT * FROM BotaoReacao ORDER BY Rotulo').fetchall()
        return [dict(r) for r in rows]

def criar_botao(rotulo, cor='#1f6aa5', icone=None):
    with get_conn() as conn:
        conn.execute('''
            INSERT INTO BotaoReacao (Rotulo, Cor, Icone)
            VALUES (?, ?, ?)
        ''', (rotulo, cor, icone))

def deletar_botao(botao_id):
    with get_conn() as conn:
        conn.execute('DELETE FROM BotaoReacao WHERE Id = ?', (botao_id,))

# ============================================================
# MARCAÇÕES
# ============================================================

def criar_marcacao(sessao_id, segundo, descricao=None, botao_id=None):
    with get_conn() as conn:
        cursor = conn.execute('''
            INSERT INTO Marcacao (SessaoId, SegundoMarca, Descricao, BotaoId)
            VALUES (?, ?, ?, ?)
        ''', (sessao_id, segundo, descricao, botao_id))
        return cursor.lastrowid

def listar_marcacoes(sessao_id):
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT m.*, b.Rotulo as Reacao, b.Cor
            FROM Marcacao m
            LEFT JOIN BotaoReacao b ON m.BotaoId = b.Id
            WHERE m.SessaoId = ?
            ORDER BY m.SegundoMarca
        ''', (sessao_id,)).fetchall()
        return [dict(r) for r in rows]

def vincular_integrante_marcacao(marcacao_id, pessoa_id):
    with get_conn() as conn:
        conn.execute('''
            INSERT OR IGNORE INTO MarcacaoIntegrante (MarcacaoId, PessoaId)
            VALUES (?, ?)
        ''', (marcacao_id, pessoa_id))

def listar_integrantes_marcacao(marcacao_id):
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT p.Id, p.NomeCompleto
            FROM MarcacaoIntegrante mi
            JOIN Pessoa p ON mi.PessoaId = p.Id
            WHERE mi.MarcacaoId = ?
        ''', (marcacao_id,)).fetchall()
        return [dict(r) for r in rows]

def criar_conexao(marcacao_id, pessoa_id1, pessoa_id2, tipo_reacao=None):
    with get_conn() as conn:
        conn.execute('''
            INSERT INTO MarcacaoConexao (MarcacaoId, PessoaId1, PessoaId2, TipoReacao)
            VALUES (?, ?, ?, ?)
        ''', (marcacao_id, pessoa_id1, pessoa_id2, tipo_reacao))

def listar_conexoes(marcacao_id):
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT mc.TipoReacao,
                   p1.NomeCompleto as Pessoa1,
                   p2.NomeCompleto as Pessoa2
            FROM MarcacaoConexao mc
            JOIN Pessoa p1 ON mc.PessoaId1 = p1.Id
            JOIN Pessoa p2 ON mc.PessoaId2 = p2.Id
            WHERE mc.MarcacaoId = ?
        ''', (marcacao_id,)).fetchall()
        return [dict(r) for r in rows]

def deletar_marcacao(marcacao_id):
    with get_conn() as conn:
        conn.execute('DELETE FROM MarcacaoIntegrante WHERE MarcacaoId = ?', (marcacao_id,))
        conn.execute('DELETE FROM MarcacaoConexao    WHERE MarcacaoId = ?', (marcacao_id,))
        conn.execute('DELETE FROM Marcacao           WHERE Id = ?',         (marcacao_id,))

