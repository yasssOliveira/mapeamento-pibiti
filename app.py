# app.py  ←  arquivo único, roda direto com: python app.py

import customtkinter as ctk
from tkinter import messagebox, ttk
from datetime import datetime
import re
from video.player     import PlayerVideo
from video.anotacoes  import PainelAnotacoes

# importa o banco
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))  # garante que acha o módulo db

from db.crud import (
    listar_modalidades,
    cadastrar_pessoa,
    listar_pessoas,
    buscar_pessoa_por_cpf,
    vincular_modalidade_pessoa,
    listar_modalidades_da_pessoa,
    criar_torneio,
    listar_torneios,
    criar_time,
    listar_times,
    listar_atletas,
    adicionar_atleta_ao_time,
    inscrever_time,
    atualizar_status_inscricao,
    listar_times_do_torneio,
    adicionar_membro,
    listar_membros_da_inscricao,
    buscar_por_serie,
    buscar_historico_atleta,
    buscar_times_treinados,
    gerar_numero_serie,
    atualizar_pessoa,
    criar_sessao,
    listar_sessoes,
    adicionar_integrante_sessao,
    listar_integrantes_sessao,
    remover_integrante_sessao,
    atualizar_sessao_video,
    buscar_sessao_por_id,
)

# ============================================================
# CONFIGURAÇÃO GLOBAL
# ============================================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ============================================================
# COMPONENTES REUTILIZÁVEIS
# ============================================================

def campo(parent, label, row, col=0, width=220, placeholder=""):
    ctk.CTkLabel(parent, text=label, anchor="w").grid(
        row=row, column=col, sticky="w", padx=10, pady=(8, 0)
    )
    entry = ctk.CTkEntry(parent, width=width, placeholder_text=placeholder)
    entry.grid(row=row, column=col + 1, sticky="w", padx=10, pady=(8, 0))
    return entry


def botao(parent, label, command, row, col, color="#1f6aa5", width=140):
    btn = ctk.CTkButton(parent, text=label, command=command,
                        fg_color=color, width=width)
    btn.grid(row=row, column=col, padx=10, pady=10, sticky="w")
    return btn


def tabela(parent, colunas, row, col, colspan=4, height=8):
    frame = ctk.CTkFrame(parent)
    frame.grid(row=row, column=col, columnspan=colspan,
               padx=10, pady=10, sticky="nsew")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview",
                    background="#2b2b2b",
                    foreground="white",
                    rowheight=26,
                    fieldbackground="#2b2b2b",
                    bordercolor="#2b2b2b",
                    borderwidth=0)
    style.map("Treeview", background=[("selected", "#1f6aa5")])
    style.configure("Treeview.Heading",
                    background="#1a1a2e",
                    foreground="white",
                    relief="flat")

    tree = ttk.Treeview(frame, columns=colunas, show="headings", height=height)
    for col_name in colunas:
        tree.heading(col_name, text=col_name)
        tree.column(col_name, width=130, anchor="center")

    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    return tree

def mascara_cpf(event):
    texto = re.sub(r"\D", "", event.widget.get())[:11]

    resultado = ""

    if len(texto) > 0:
        resultado += texto[:3]

    if len(texto) >= 4:
        resultado += "." + texto[3:6]

    if len(texto) >= 7:
        resultado += "." + texto[6:9]

    if len(texto) >= 10:
        resultado += "-" + texto[9:11]

    event.widget.delete(0, "end")
    event.widget.insert(0, resultado)


def mascara_telefone(event):
    texto = re.sub(r"\D", "", event.widget.get())[:11]

    resultado = ""

    if len(texto) >= 1:
        resultado += "(" + texto[:2]

    if len(texto) >= 3:
        resultado += ") " + texto[2:7]

    if len(texto) >= 8:
        resultado += "-" + texto[7:11]

    event.widget.delete(0, "end")
    event.widget.insert(0, resultado)


def mascara_data(event):
    texto = re.sub(r"\D", "", event.widget.get())[:8]

    resultado = ""

    if len(texto) >= 1:
        resultado += texto[:2]

    if len(texto) >= 3:
        resultado += "-" + texto[2:4]

    if len(texto) >= 5:
        resultado += "-" + texto[4:8]

    event.widget.delete(0, "end")
    event.widget.insert(0, resultado)

def validar_data(data_str, permitir_futuro=True):
    try:
        data = datetime.strptime(data_str, "%d-%m-%Y")
    except ValueError:
        return False, (
            "Data inválida.\n"
            "Verifique dia, mês e ano.\n"
            "Use o formato DD-MM-AAAA."
        )

    ano_atual = datetime.now().year

    if not permitir_futuro and data.year > ano_atual:
        return False, (
            f"O ano não pode ser maior que {ano_atual}."
        )

    return True, data

# ============================================================
# ABA PESSOAS
# ============================================================

class AbaPessoa(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Cadastro de Pessoa",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=4, pady=(14, 4), sticky="w", padx=10
        )

        self.e_nome = campo(self, "Nome completo", row=1)
        self.e_cpf  = campo(self, "CPF",           row=2, placeholder="000.000.000-00")
        self.e_nasc = campo(self, "Nascimento", row=3, placeholder="DD-MM-AAAA")
        self.e_tel  = campo(self, "Telefone",      row=4, placeholder="(00) 00000-0000")
        self.e_mail = campo(self, "E-mail",        row=5)

        ctk.CTkLabel(self, text="Tipo", anchor="w").grid(
            row=6, column=0, sticky="w", padx=10, pady=(8, 0)
        )

        self.combo_tipo = ctk.CTkComboBox(
            self,
            values=["ATLETA", "TREINADOR"],
            width=180
        )
        self.combo_tipo.set("ATLETA")
        self.combo_tipo.grid(
            row=6,
            column=1,
            padx=10,
            pady=(8, 0),
            sticky="w"
        )

        self.e_cpf.bind("<KeyRelease>", mascara_cpf)
        self.e_tel.bind("<KeyRelease>", mascara_telefone)
        self.e_nasc.bind("<KeyRelease>", mascara_data)

        ctk.CTkLabel(self, text="Modalidades", anchor="w").grid(
            row=7, column=0, sticky="w", padx=10, pady=(8, 0)
        )
        self.frame_modal = ctk.CTkScrollableFrame(self, width=380, height=120)
        self.frame_modal.grid(row=7, column=1, columnspan=3,
                               padx=10, pady=(8, 0), sticky="w")

        self._vars_modal = {}
        for m in listar_modalidades():
            var = ctk.BooleanVar()
            chk = ctk.CTkCheckBox(self.frame_modal, text=m['Nome'], variable=var)
            chk.pack(anchor="w", pady=2)
            self._vars_modal[m['Id']] = var

        botao(self, "Salvar pessoa",  self._salvar, row=8, col=1)
        botao(self, "Listar pessoas", self._listar, row=8, col=2, color="#2d6a4f")

        self.tree = tabela(
            self,
            ["Id", "Nome", "CPF", "Nascimento", "Tipo", "Telefone", "Modalidades"],
            row=9, col=0, colspan=4
        )

    def _salvar(self):
        nome = self.e_nome.get().strip()
        cpf  = self.e_cpf.get().strip()
        nasc = self.e_nasc.get().strip()
        tel  = self.e_tel.get().strip()
        mail = self.e_mail.get().strip()
        tipo = self.combo_tipo.get()

        if not nome or not cpf or not nasc:
            messagebox.showwarning("Atenção", "Nome, CPF e Nascimento são obrigatórios.")
            return

        existente = buscar_pessoa_por_cpf(cpf)
        if existente:
            messagebox.showerror("CPF duplicado",
                                f"CPF já cadastrado para: {existente['NomeCompleto']}")
            return

        if not re.fullmatch(r"\d{3}\.\d{3}\.\d{3}-\d{2}", cpf):
            messagebox.showerror(
                "CPF inválido",
                "Use o formato 000.000.000-00"
            )
            return

        if tel and not re.fullmatch(r"\(\d{2}\)\s\d{5}-\d{4}", tel):
            messagebox.showerror(
                "Telefone inválido",
                "Use o formato (00) 00000-0000"
            )
            return

        ok, resultado = validar_data(nasc, permitir_futuro=False)
        if not ok:
            messagebox.showerror("Data inválida", resultado)
            return

        try:
            # Gera o número de série antes de cadastrar
            serie = gerar_numero_serie()

            pid = cadastrar_pessoa(
                nome,
                cpf,
                nasc,
                mail or None,
                tel  or None,
                tipo,
                serie          # passa a série para o cadastrar_pessoa
            )
            for mid, var in self._vars_modal.items():
                if var.get():
                    vincular_modalidade_pessoa(pid, mid)

            messagebox.showinfo(
                "Cadastro Realizado",
                f"✅ {tipo.capitalize()} '{nome}' cadastrado com sucesso!\n\n"
                f"Número de Série:  {serie}\n\n"
                f"Guarde este código — ele identifica esta pessoa no sistema."
            )
            self._limpar()
            self._listar()
        except Exception as e:
            messagebox.showerror("Erro", str(e))


    def _listar(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for p in listar_pessoas():
            mods = listar_modalidades_da_pessoa(p['Id'])
            nomes_mods = ", ".join(m['Nome'] for m in mods) or "—"
            self.tree.insert("", "end", values=(
                p['Id'], p['NomeCompleto'], p['CPF'],
                p['DataNascimento'], p['TipoPessoa'], p['Telefone'] or "—", nomes_mods
            ))

    def _limpar(self):
        for e in [self.e_nome, self.e_cpf, self.e_nasc, self.e_tel, self.e_mail]:
            e.delete(0, "end")
        for var in self._vars_modal.values():
            var.set(False)


# ============================================================
# ABA TORNEIOS
# ============================================================

class AbaTorneio(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Torneios",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=4, pady=(14, 4), sticky="w", padx=10
        )

        self.e_nome      = campo(self, "Nome",      row=1)
        self.e_inicio = campo(self, "Início", row=2, placeholder="DD-MM-AAAA")
        self.e_fim    = campo(self, "Fim", row=3, placeholder="DD-MM-AAAA")
        self.e_descricao = campo(self, "Descrição", row=4)

        self.e_inicio.bind("<KeyRelease>", mascara_data)
        self.e_fim.bind("<KeyRelease>", mascara_data)

        ctk.CTkLabel(self, text="Modalidade", anchor="w").grid(
            row=5, column=0, sticky="w", padx=10, pady=(8, 0)
        )
        self._modal_ids   = []
        self._modal_nomes = []
        for m in listar_modalidades():
            self._modal_ids.append(m['Id'])
            self._modal_nomes.append(m['Nome'])

        self.combo_modal = ctk.CTkComboBox(self, values=self._modal_nomes, width=220)
        self.combo_modal.grid(row=5, column=1, padx=10, pady=(8, 0), sticky="w")

        botao(self, "Salvar torneio",  self._salvar, row=6, col=1)
        botao(self, "Listar torneios", self._listar, row=6, col=2, color="#2d6a4f")

        self.tree = tabela(
            self,
            ["Id", "Nome", "Modalidade", "Início", "Fim", "Status"],
            row=9, col=0, colspan=4
        )

    def _salvar(self):
        nome      = self.e_nome.get().strip()
        inicio    = self.e_inicio.get().strip()
        fim       = self.e_fim.get().strip()
        descricao = self.e_descricao.get().strip()
        modal_nome = self.combo_modal.get()

        if not nome or not modal_nome:
            messagebox.showwarning("Atenção", "Nome e Modalidade são obrigatórios.")
            return

        try:
            modal_id = self._modal_ids[self._modal_nomes.index(modal_nome)]
            inicio_banco = None
            fim_banco = None

            dt_inicio = None
            dt_fim = None

            if inicio:
                ok, resultado = validar_data(
                    inicio,
                    permitir_futuro=True
                )

                if not ok:
                    messagebox.showerror(
                        "Data inválida",
                        f"Data de início: {resultado}"
                    )
                    return

                dt_inicio = resultado

            if fim:
                ok, resultado = validar_data(
                    fim,
                    permitir_futuro=True
                )

                if not ok:
                    messagebox.showerror(
                        "Data inválida",
                        f"Data de fim: {resultado}"
                    )
                    return

                dt_fim = resultado

            if dt_inicio and dt_fim and dt_fim < dt_inicio:
                messagebox.showerror(
                    "Data inválida",
                    "A data de término não pode ser anterior à data de início."
                )
                return
                
            criar_torneio(
                nome=nome, modalidade_id=modal_id,
                descricao=descricao or None,
                data_inicio=inicio or None,
                data_fim=fim or None,
            )
            messagebox.showinfo("Sucesso", f"Torneio '{nome}' criado!")
            self._limpar()
            self._listar()
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    '''def _listar(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for t in listar_torneios():
            self.tree.insert("", "end", values=(
                t['Id'], t['Nome'], t.get('NomeModalidade', '—'),
                t['DataInicio'] or '—',
                t['DataFim'] or '—', t['Status']
            ))'''
    def _listar(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Badge visual por status
        cores = {
            "aberto":       "🟢",
            "em_andamento": "🟡",
            "encerrado":    "🔴",
        }

        for t in listar_torneios(apenas_ativas=False):
            badge = cores.get(t["Status"], "⚪")
            self.tree.insert("", "end", values=(
                t["Id"],
                t["Nome"],
                t.get("NomeModalidade", "—"),
                t["DataInicio"] or "—",
                t["DataFim"]    or "—",
                f"{badge} {t['Status']}"
            ))


    def _limpar(self):
        for e in [self.e_nome,
                  self.e_inicio, self.e_fim, self.e_descricao]:
            e.delete(0, "end")


# ============================================================
# ABA TIMES
# ============================================================
class AbaTime(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self._time_em_edicao_id = None
        self._treinador_selecionado = None  # guarda o objeto do treinador
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Times",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=4, pady=(14, 4), sticky="w", padx=10
        )

        # --- Seção 1: Criar o Time ---
        ctk.CTkLabel(self, text="── 1. Criar o Time ──",
                     font=ctk.CTkFont(size=13)).grid(
            row=1, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 2)
        )

        self.e_nome = campo(self, "Nome do Time", row=2)

        ctk.CTkLabel(self, text="Modalidade").grid(row=3, column=0, padx=10, pady=4, sticky="w")
        self.combo_modalidade = ctk.CTkComboBox(
            self,
            values=[m["Nome"] for m in listar_modalidades()],
            command=self._ao_mudar_modalidade
        )
        self.combo_modalidade.grid(row=3, column=1, padx=10, pady=4, sticky="ew")

        # Busca de Treinador
        ctk.CTkLabel(self, text="Buscar Treinador").grid(row=4, column=0, padx=10, pady=4, sticky="w")
        self.e_busca_treinador = ctk.CTkEntry(self, placeholder_text="Digite o nome do treinador...", width=260)
        self.e_busca_treinador.grid(row=4, column=1, padx=10, pady=4, sticky="ew")
        ctk.CTkButton(self, text="🔍", width=40, command=self._buscar_treinador).grid(row=4, column=2, padx=(0, 10))

        self.lbl_treinador_sel = ctk.CTkLabel(self, text="Nenhum treinador selecionado.", text_color="gray")
        self.lbl_treinador_sel.grid(row=5, column=1, columnspan=2, sticky="w", padx=10)

        # Resultado da busca de treinador
        self.tree_busca_treinador = tabela(self, ["Id", "Nome", "CPF"], row=6, col=0, colspan=4, height=4)
        self.tree_busca_treinador.bind("<ButtonRelease-1>", self._selecionar_treinador)

        self.btn_criar = ctk.CTkButton(
            self, text="✅ Criar Time e Continuar",
            command=self._criar_time, fg_color="#1f6aa5"
        )
        self.btn_criar.grid(row=7, column=1, padx=10, pady=10, sticky="w")

        botao(self, "↺ Atualizar Listas", self._atualizar_dados, row=7, col=2, color="#555", width=140)

        self.lbl_status = ctk.CTkLabel(self, text="Nenhum time em edição.", text_color="gray")
        self.lbl_status.grid(row=7, column=3, sticky="w", padx=10)

        # --- Seção 2: Adicionar Atletas ---
        ctk.CTkLabel(self, text="── 2. Adicionar Atletas ao Time ──",
                     font=ctk.CTkFont(size=13)).grid(
            row=8, column=0, columnspan=4, sticky="w", padx=10, pady=(14, 2)
        )

        ctk.CTkLabel(self, text="Buscar Atleta").grid(row=9, column=0, padx=10, pady=4, sticky="w")
        self.e_busca_atleta = ctk.CTkEntry(self, placeholder_text="Digite o nome do atleta...", width=260)
        self.e_busca_atleta.grid(row=9, column=1, padx=10, pady=4, sticky="ew")
        ctk.CTkButton(self, text="🔍", width=40, command=self._buscar_atleta).grid(row=9, column=2, padx=(0, 10))

        # Resultado da busca de atleta
        self.tree_busca_atleta = tabela(self, ["Id", "Nome", "CPF"], row=10, col=0, colspan=4, height=4)
        self.tree_busca_atleta.bind("<ButtonRelease-1>", self._selecionar_atleta)

        self.btn_add_atleta = ctk.CTkButton(
            self, text="➕ Adicionar Atleta Selecionado",
            command=self._adicionar_atleta, fg_color="#2d6a4f",
            state="disabled"
        )
        self.btn_add_atleta.grid(row=11, column=1, padx=10, pady=6, sticky="w")

        self.btn_finalizar = ctk.CTkButton(
            self, text="🏁 Finalizar Time",
            command=self._finalizar_time, fg_color="#555",
            state="disabled"
        )
        self.btn_finalizar.grid(row=11, column=2, padx=10, pady=6, sticky="w")

        # Atletas já adicionados ao time em edição
        ctk.CTkLabel(self, text="Atletas no time em edição:").grid(
            row=12, column=0, columnspan=4, sticky="w", padx=10, pady=(8, 0)
        )
        self.tree_atletas = tabela(self, ["Id", "Nome", "CPF"], row=13, col=0, colspan=4, height=4)

        # --- Seção 3: Times Cadastrados (só aparece com modalidade selecionada) ---
        ctk.CTkLabel(self, text="── Times Cadastrados ──",
                     font=ctk.CTkFont(size=13)).grid(
            row=14, column=0, columnspan=4, sticky="w", padx=10, pady=(14, 2)
        )

        self.lbl_filtro_modal = ctk.CTkLabel(
            self, text="Selecione uma modalidade acima para ver os times.", text_color="gray"
        )
        self.lbl_filtro_modal.grid(row=15, column=0, columnspan=4, sticky="w", padx=10)

        self.tree = tabela(self, ["Id", "Nome", "Modalidade", "Treinador"], row=16, col=0, colspan=4)
        # Começa oculta até modalidade ser selecionada
        self.tree.master.grid_remove()
        self.lbl_filtro_modal.grid()

    # --- BUSCA DE TREINADOR ---
    def _buscar_treinador(self):
        termo = self.e_busca_treinador.get().strip().lower()
        for row in self.tree_busca_treinador.get_children():
            self.tree_busca_treinador.delete(row)

        todos = [p for p in listar_pessoas() if p["TipoPessoa"] == "TREINADOR"]
        filtrados = [p for p in todos if termo in p["NomeCompleto"].lower()]

        if not filtrados:
            messagebox.showinfo("Busca", "Nenhum treinador encontrado.")
            return

        for p in filtrados:
            self.tree_busca_treinador.insert("", "end", values=(p["Id"], p["NomeCompleto"], p["CPF"]))

    def _selecionar_treinador(self, event):
        sel = self.tree_busca_treinador.focus()
        if not sel:
            return
        valores = self.tree_busca_treinador.item(sel)["values"]
        self._treinador_selecionado = {"Id": valores[0], "NomeCompleto": valores[1]}
        self.lbl_treinador_sel.configure(
            text=f"✅ Treinador: {valores[1]} (Id {valores[0]})",
            text_color="#1f9e5e"
        )

    # --- BUSCA DE ATLETA ---
    def _buscar_atleta(self):
        termo = self.e_busca_atleta.get().strip().lower()
        for row in self.tree_busca_atleta.get_children():
            self.tree_busca_atleta.delete(row)

        filtrados = [a for a in listar_atletas() if termo in a["NomeCompleto"].lower()]

        if not filtrados:
            messagebox.showinfo("Busca", "Nenhum atleta encontrado.")
            return

        for a in filtrados:
            self.tree_busca_atleta.insert("", "end", values=(a["Id"], a["NomeCompleto"], a["CPF"]))

    def _selecionar_atleta(self, event):
        # Apenas marca visualmente; a adição acontece no botão
        pass

    # --- FILTRO DE MODALIDADE NA LISTA DE TIMES ---
    def _ao_mudar_modalidade(self, escolha):
        self._listar(modalidade_filtro=escolha)

    # --- CRIAR TIME ---
    def _criar_time(self):
        nome = self.e_nome.get().strip()
        modalidade_nome = self.combo_modalidade.get()

        if not nome:
            messagebox.showwarning("Atenção", "Nome do time é obrigatório.")
            return

        if not self._treinador_selecionado:
            messagebox.showwarning("Atenção", "Selecione um treinador antes de criar o time.")
            return

        if self._time_em_edicao_id is not None:
            messagebox.showwarning("Atenção", "Finalize o time em edição antes de criar um novo.")
            return

        try:
            modalidade = next(m for m in listar_modalidades() if m["Nome"] == modalidade_nome)
            time_id = criar_time(nome, modalidade["Id"], self._treinador_selecionado["Id"])
            self._time_em_edicao_id = time_id

            self.lbl_status.configure(
                text=f"✏️ Editando: {nome} (Id {time_id})",
                text_color="#1f9e5e"
            )
            self.btn_add_atleta.configure(state="normal")
            self.btn_finalizar.configure(state="normal")
            self.btn_criar.configure(state="disabled")
            self._listar(modalidade_filtro=modalidade_nome)

        except ValueError as e:
            messagebox.showerror("Nome duplicado", str(e))
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # --- ADICIONAR ATLETA ---
    def _adicionar_atleta(self):
        if self._time_em_edicao_id is None:
            messagebox.showwarning("Atenção", "Crie um time primeiro.")
            return

        sel = self.tree_busca_atleta.focus()
        if not sel:
            messagebox.showwarning("Atenção", "Clique em um atleta na tabela de busca para selecioná-lo.")
            return

        valores = self.tree_busca_atleta.item(sel)["values"]
        atleta_id = valores[0]
        atleta_nome = valores[1]
        atleta_cpf = valores[2]

        modalidade_time_nome = self.combo_modalidade.get()
        modalidades_do_atleta = [m['Nome'] for m in listar_modalidades_da_pessoa(atleta_id)]

        if modalidade_time_nome not in modalidades_do_atleta:
            messagebox.showerror(
                "Erro de Modalidade",
                f"'{atleta_nome}' não possui a modalidade '{modalidade_time_nome}' no perfil.\n\n"
                f"Vincule a modalidade na aba 'Pessoas' antes de continuar."
            )
            return

        ids_ja_adicionados = [
            self.tree_atletas.item(i)['values'][0]
            for i in self.tree_atletas.get_children()
        ]
        if atleta_id in ids_ja_adicionados:
            messagebox.showwarning("Atenção", "Este atleta já foi adicionado.")
            return

        try:
            adicionar_atleta_ao_time(self._time_em_edicao_id, atleta_id)
            self.tree_atletas.insert("", "end", values=(atleta_id, atleta_nome, atleta_cpf))
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # --- FINALIZAR TIME ---
    def _finalizar_time(self):
        nome = self.e_nome.get().strip()
        messagebox.showinfo("Time Finalizado", f"Time '{nome}' salvo com sucesso!")

        self._time_em_edicao_id = None
        self._treinador_selecionado = None

        self.lbl_status.configure(text="Nenhum time em edição.", text_color="gray")
        self.lbl_treinador_sel.configure(text="Nenhum treinador selecionado.", text_color="gray")
        self.btn_add_atleta.configure(state="disabled")
        self.btn_finalizar.configure(state="disabled")
        self.btn_criar.configure(state="normal")

        self.e_nome.delete(0, "end")
        self.e_busca_treinador.delete(0, "end")
        self.e_busca_atleta.delete(0, "end")

        for row in self.tree_atletas.get_children():
            self.tree_atletas.delete(row)
        for row in self.tree_busca_treinador.get_children():
            self.tree_busca_treinador.delete(row)
        for row in self.tree_busca_atleta.get_children():
            self.tree_busca_atleta.delete(row)

        self._listar(modalidade_filtro=self.combo_modalidade.get())

    # --- LISTAR TIMES (filtrado por modalidade) ---
    def _listar(self, modalidade_filtro=None):
        if not modalidade_filtro:
            self.tree.master.grid_remove()
            self.lbl_filtro_modal.grid()
            return

        self.lbl_filtro_modal.grid_remove()
        self.tree.master.grid()

        for row in self.tree.get_children():
            self.tree.delete(row)

        for t in listar_times():
            if t["NomeModalidade"] == modalidade_filtro:
                self.tree.insert("", "end", values=(
                    t["Id"], t["Nome"], t["NomeModalidade"], t["NomeTreinador"]
                ))

    # --- ATUALIZAR COMBOS ---
    def _atualizar_dados(self):
        self.combo_modalidade.configure(
            values=[m["Nome"] for m in listar_modalidades()]
        )

# ============================================================
# ABA INSCRIÇÕES
# ============================================================
class AbaInscricao(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self._torneio_selecionado = None
        self._time_selecionado = None
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Inscrição de Time em Torneio",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=4, pady=(14, 4), sticky="w", padx=10
        )

        # --- Busca de Torneio ---
        ctk.CTkLabel(self, text="── 1. Selecionar Torneio ──",
                     font=ctk.CTkFont(size=13)).grid(
            row=1, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 2)
        )

        ctk.CTkLabel(self, text="Buscar Torneio").grid(row=2, column=0, padx=10, pady=4, sticky="w")
        self.e_busca_torneio = ctk.CTkEntry(self, placeholder_text="Digite o nome do torneio...", width=260)
        self.e_busca_torneio.grid(row=2, column=1, padx=10, pady=4, sticky="ew")
        ctk.CTkButton(self, text="🔍", width=40, command=self._buscar_torneio).grid(row=2, column=2, padx=(0, 10))

        self.tree_busca_torneio = tabela(self, ["Id", "Nome", "Modalidade", "Status"], row=3, col=0, colspan=4, height=4)
        self.tree_busca_torneio.bind("<ButtonRelease-1>", self._selecionar_torneio)

        self.lbl_torneio_sel = ctk.CTkLabel(self, text="Nenhum torneio selecionado.", text_color="gray")
        self.lbl_torneio_sel.grid(row=4, column=0, columnspan=4, sticky="w", padx=10, pady=(2, 8))

        # --- Busca de Time ---
        ctk.CTkLabel(self, text="── 2. Selecionar Time ──",
                     font=ctk.CTkFont(size=13)).grid(
            row=5, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 2)
        )

        ctk.CTkLabel(self, text="Buscar Time").grid(row=6, column=0, padx=10, pady=4, sticky="w")
        self.e_busca_time = ctk.CTkEntry(self, placeholder_text="Digite o nome do time...", width=260)
        self.e_busca_time.grid(row=6, column=1, padx=10, pady=4, sticky="ew")
        ctk.CTkButton(self, text="🔍", width=40, command=self._buscar_time).grid(row=6, column=2, padx=(0, 10))

        self.tree_busca_time = tabela(self, ["Id", "Nome", "Modalidade", "Treinador"], row=7, col=0, colspan=4, height=4)
        self.tree_busca_time.bind("<ButtonRelease-1>", self._selecionar_time)

        self.lbl_time_sel = ctk.CTkLabel(self, text="Nenhum time selecionado.", text_color="gray")
        self.lbl_time_sel.grid(row=8, column=0, columnspan=4, sticky="w", padx=10, pady=(2, 8))

        # --- Ações ---
        ctk.CTkButton(
            self, text="📋 Inscrever Time", command=self._inscrever, fg_color="#1f6aa5"
        ).grid(row=9, column=1, padx=10, pady=10, sticky="w")

        ctk.CTkButton(
            self, text="👁 Ver Times Inscritos", command=self._listar, fg_color="#2d6a4f"
        ).grid(row=9, column=2, padx=10, pady=10, sticky="w")

        # --- Lista de times inscritos no torneio selecionado ---
        ctk.CTkLabel(self, text="── Times Inscritos no Torneio Selecionado ──",
                     font=ctk.CTkFont(size=13)).grid(
            row=10, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 2)
        )

        self.tree_inscritos = tabela(
            self, ["InscricaoId", "Time", "Status"],
            row=11, col=0, colspan=4, height=4
        )

    # --- BUSCA DE TORNEIO ---
    def _buscar_torneio(self):
        termo = self.e_busca_torneio.get().strip().lower()
        for row in self.tree_busca_torneio.get_children():
            self.tree_busca_torneio.delete(row)

        filtrados = [t for t in listar_torneios() if termo in t["Nome"].lower()]

        if not filtrados:
            messagebox.showinfo("Busca", "Nenhum torneio encontrado.")
            return

        for t in filtrados:
            self.tree_busca_torneio.insert("", "end", values=(
                t["Id"], t["Nome"], t.get("NomeModalidade", "—"), t["Status"]
            ))

    def _selecionar_torneio(self, event):
        sel = self.tree_busca_torneio.focus()
        if not sel:
            return
        valores = self.tree_busca_torneio.item(sel)["values"]
        self._torneio_selecionado = {"Id": valores[0], "Nome": valores[1], "Modalidade": valores[2]}
        self.lbl_torneio_sel.configure(
            text=f"✅ Torneio: {valores[1]} — {valores[2]} (Id {valores[0]})",
            text_color="#1f9e5e"
        )

    # --- BUSCA DE TIME ---
    def _buscar_time(self):
        termo = self.e_busca_time.get().strip().lower()
        for row in self.tree_busca_time.get_children():
            self.tree_busca_time.delete(row)

        filtrados = [t for t in listar_times() if termo in t["Nome"].lower()]

        if not filtrados:
            messagebox.showinfo("Busca", "Nenhum time encontrado.")
            return

        for t in filtrados:
            self.tree_busca_time.insert("", "end", values=(
                t["Id"], t["Nome"], t["NomeModalidade"], t["NomeTreinador"]
            ))

    def _selecionar_time(self, event):
        sel = self.tree_busca_time.focus()
        if not sel:
            return
        valores = self.tree_busca_time.item(sel)["values"]
        self._time_selecionado = {"Id": valores[0], "Nome": valores[1], "Modalidade": valores[2]}
        self.lbl_time_sel.configure(
            text=f"✅ Time: {valores[1]} — {valores[2]} (Id {valores[0]})",
            text_color="#1f9e5e"
        )

    # --- INSCREVER ---
    def _inscrever(self):
        if not self._torneio_selecionado:
            messagebox.showwarning("Atenção", "Selecione um torneio primeiro.")
            return

        if not self._time_selecionado:
            messagebox.showwarning("Atenção", "Selecione um time primeiro.")
            return

        # Validação de modalidade
        if self._torneio_selecionado["Modalidade"] != self._time_selecionado["Modalidade"]:
            messagebox.showerror(
                "Modalidade incompatível",
                f"O torneio é de '{self._torneio_selecionado['Modalidade']}' "
                f"mas o time é de '{self._time_selecionado['Modalidade']}'.\n\n"
                f"Só é possível inscrever times da mesma modalidade do torneio."
            )
            return

        try:
            iid = inscrever_time(self._torneio_selecionado["Id"], self._time_selecionado["Id"])
            atualizar_status_inscricao(iid, "confirmada")
            messagebox.showinfo("Sucesso", "Time inscrito e confirmado!")
            self._listar()
        except Exception as e:
            messagebox.showerror("Erro", "Time já inscrito neste torneio ou erro inesperado.")

    # --- LISTAR TIMES INSCRITOS ---
    def _listar(self):
        if not self._torneio_selecionado:
            messagebox.showwarning("Atenção", "Selecione um torneio para ver os inscritos.")
            return

        for row in self.tree_inscritos.get_children():
            self.tree_inscritos.delete(row)

        for t in listar_times_do_torneio(self._torneio_selecionado["Id"]):
            self.tree_inscritos.insert("", "end", values=(
                t["InscricaoId"], t["NomeTime"], t["StatusInscricao"]
            ))


# ============================================================
# ABA MEMBROS
# ============================================================

class AbaMembro(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Adicionar Membro à Inscrição",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=4, pady=(14, 4), sticky="w", padx=10
        )

        ctk.CTkLabel(self, text="Inscrição", anchor="w").grid(
            row=1, column=0, sticky="w", padx=10, pady=(8, 0)
        )
        self._insc_ids   = []
        self._insc_nomes = []
        self.combo_insc = ctk.CTkComboBox(self, values=[], width=340)
        self.combo_insc.grid(row=1, column=1, columnspan=2,
                              padx=10, pady=(8, 0), sticky="w")

        ctk.CTkLabel(self, text="Pessoa", anchor="w").grid(
            row=2, column=0, sticky="w", padx=10, pady=(8, 0)
        )
        self._pessoa_ids   = []
        self._pessoa_nomes = []
        self.combo_pessoa = ctk.CTkComboBox(self, values=[], width=340)
        self.combo_pessoa.grid(row=2, column=1, columnspan=2,
                                padx=10, pady=(8, 0), sticky="w")
        

        self.e_camisa  = campo(self, "Nº Camisa", row=3, width=80)
        self.e_posicao = campo(self, "Posição", row=4)

        self.var_titular = ctk.BooleanVar()
        ctk.CTkCheckBox(self, text="Titular", variable=self.var_titular).grid(
            row=5, column=1, sticky="w", padx=10, pady=(8, 0)
        )

        botao(self, "↺ Atualizar",      self._carregar, row=6, col=0, color="#555", width=120)
        botao(self, "Adicionar membro", self._adicionar, row=6, col=1)
        botao(self, "Ver membros",      self._listar,    row=6, col=2, color="#2d6a4f")

        self.tree = tabela(
            self,
            ["MembroId", "Nome", "CPF", "Tipo", "Camisa", "Posição", "Titular"],
            row=7, col=0, colspan=4
        )

        self._carregar()

    def _carregar(self):
        self._insc_ids, self._insc_nomes = [], []
        for t in listar_torneios():
            for insc in listar_times_do_torneio(t['Id']):
                self._insc_ids.append(insc['InscricaoId'])
                self._insc_nomes.append(
                    f"{insc['InscricaoId']} – {t['Nome']} / {insc['NomeTime']}"
                )
        self.combo_insc.configure(values=self._insc_nomes)
        if self._insc_nomes:
            self.combo_insc.set(self._insc_nomes[0])

        self._pessoa_ids, self._pessoa_nomes = [], []
        for p in listar_pessoas():
            self._pessoa_ids.append(p['Id'])
            self._pessoa_nomes.append(f"{p['Id']} – {p['NomeCompleto']} ({p['TipoPessoa']})")
        self.combo_pessoa.configure(values=self._pessoa_nomes)
        if self._pessoa_nomes:
            self.combo_pessoa.set(self._pessoa_nomes[0])

    def _adicionar(self):
        try:
            iidx    = self._insc_nomes.index(self.combo_insc.get())
            pidx    = self._pessoa_nomes.index(self.combo_pessoa.get())
            camisa  = self.e_camisa.get().strip()
            posicao = self.e_posicao.get().strip()

            adicionar_membro(
                inscricao_time_id=self._insc_ids[iidx],
                pessoa_id=self._pessoa_ids[pidx],
                numero_camisa=int(camisa) if camisa else None,
                posicao=posicao or None,
                titular=self.var_titular.get()
            )
            messagebox.showinfo("Sucesso", "Membro adicionado!")
            self._listar()
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def _listar(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        try:
            iidx = self._insc_nomes.index(self.combo_insc.get())
            iid  = self._insc_ids[iidx]
            for m in listar_membros_da_inscricao(iid):
                self.tree.insert("", "end", values=(
                    m['MembroId'], m['NomeCompleto'], m['CPF'],
                    m['TipoPessoa'], m['NumeroCamisa'] or '—',
                    m['Posicao'] or '—',
                    'Sim' if m['Titular'] else 'Não'
                ))
        except Exception as e:
            messagebox.showerror("Erro", str(e))

# ============================================================
# PERFIS E FILTROS
# ============================================================
class AbaPerfil(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self._pessoa_atual = None   # guarda o objeto da pessoa em exibição
        self._editando = False
        self._build()

# --- CONTROLE DE EDIÇÃO ---
    def _habilitar_edicao(self):
        self._editando = True
        # Habilita só os campos editáveis (não CPF, Tipo nem Série — são imutáveis)
        editaveis = ["NomeCompleto", "DataNascimento", "Email", "Telefone"]
        self._set_campos_estado("disabled")
        for chave in editaveis:
            self.campos[chave].configure(state="normal")

        self.btn_editar.configure(state="disabled")
        self.btn_salvar.configure(state="normal")
        self.btn_cancelar.configure(state="normal")

    def _cancelar_edicao(self):
        self._editando = False
        # Restaura os valores originais
        if self._pessoa_atual:
            self._preencher_campos(self._pessoa_atual)
        self.btn_editar.configure(state="normal")
        self.btn_salvar.configure(state="disabled")
        self.btn_cancelar.configure(state="disabled")

    def _salvar_edicao(self):
        if not self._pessoa_atual:
            return

        novo_nome = self.campos["NomeCompleto"].get().strip()
        novo_nasc = self.campos["DataNascimento"].get().strip()
        novo_mail = self.campos["Email"].get().strip()
        novo_tel  = self.campos["Telefone"].get().strip()

        if not novo_nome or not novo_nasc:
            messagebox.showwarning("Atenção", "Nome e Nascimento são obrigatórios.")
            return

        try:
            atualizar_pessoa(
                self._pessoa_atual["Id"],
                novo_nome,
                novo_nasc,
                novo_mail or None,
                novo_tel  or None
            )
            # Atualiza o objeto local para refletir a edição
            self._pessoa_atual["NomeCompleto"]   = novo_nome
            self._pessoa_atual["DataNascimento"] = novo_nasc
            self._pessoa_atual["Email"]          = novo_mail
            self._pessoa_atual["Telefone"]       = novo_tel

            messagebox.showinfo("Sucesso", "Perfil atualizado com sucesso!")
            self._cancelar_edicao()
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def _build(self):
        ctk.CTkLabel(self, text="Perfis",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=4, pady=(14, 4), sticky="w", padx=10
        )

        # --- Busca unificada ---
        ctk.CTkLabel(self, text="Buscar").grid(row=1, column=0, padx=10, pady=4, sticky="w")
        self.e_busca = ctk.CTkEntry(
            self, placeholder_text="Nome, CPF ou Nº de Série...", width=300
        )
        self.e_busca.grid(row=1, column=1, padx=10, pady=4, sticky="ew")
        ctk.CTkButton(self, text="🔍", width=40, command=self._pesquisar).grid(
            row=1, column=2, padx=(0, 10)
        )

        # Tabela de resultados da busca
        self.tree_resultados = tabela(
            self, ["Id", "Nome", "Tipo", "Nº Série"], row=2, col=0, colspan=4, height=4
        )
        self.tree_resultados.bind("<ButtonRelease-1>", self._ao_selecionar)

        # --- Separador ---
        ctk.CTkLabel(self, text="── Perfil ──",
                     font=ctk.CTkFont(size=13)).grid(
            row=3, column=0, columnspan=4, sticky="w", padx=10, pady=(12, 2)
        )

        # --- Campos do perfil (somente leitura por padrão) ---
        self.campos = {}
        labels = [
            ("NomeCompleto", "Nome Completo"),
            ("CPF",          "CPF"),
            ("DataNascimento","Nascimento"),
            ("Email",        "Email"),
            ("Telefone",     "Telefone"),
            ("TipoPessoa",   "Tipo"),
            ("NumeroSerie",  "Nº de Série"),
        ]

        for i, (chave, rotulo) in enumerate(labels):
            ctk.CTkLabel(self, text=rotulo).grid(
                row=4 + i, column=0, padx=10, pady=3, sticky="w"
            )
            entry = ctk.CTkEntry(self, width=320, state="disabled")
            entry.grid(row=4 + i, column=1, columnspan=2, padx=10, pady=3, sticky="ew")
            self.campos[chave] = entry

        # Modalidades (só leitura, exibida como texto)
        ctk.CTkLabel(self, text="Modalidades").grid(
            row=4 + len(labels), column=0, padx=10, pady=3, sticky="w"
        )
        self.lbl_modalidades = ctk.CTkLabel(self, text="—", anchor="w")
        self.lbl_modalidades.grid(
            row=4 + len(labels), column=1, columnspan=2, padx=10, pady=3, sticky="ew"
        )

        # Times / Torneios (texto informativo)
        self.txt_historico = ctk.CTkTextbox(self, width=500, height=100, font=("Courier New", 12))
        self.txt_historico.grid(
            row=4 + len(labels) + 1, column=0, columnspan=4, padx=10, pady=6, sticky="ew"
        )
        self.txt_historico.configure(state="disabled")

        # --- Botões de ação ---
        self.btn_editar = ctk.CTkButton(
            self, text="✏️ Editar Perfil",
            command=self._habilitar_edicao,
            fg_color="#1f6aa5",
            state="disabled"    # só habilita após selecionar alguém
        )
        self.btn_editar.grid(row=4 + len(labels) + 2, column=1, padx=10, pady=10, sticky="w")

        self.btn_salvar = ctk.CTkButton(
            self, text="💾 Salvar Alterações",
            command=self._salvar_edicao,
            fg_color="#2d6a4f",
            state="disabled"    # só habilita em modo edição
        )
        self.btn_salvar.grid(row=4 + len(labels) + 2, column=2, padx=10, pady=10, sticky="w")

        self.btn_cancelar = ctk.CTkButton(
            self, text="✖ Cancelar",
            command=self._cancelar_edicao,
            fg_color="#555",
            state="disabled"
        )
        self.btn_cancelar.grid(row=4 + len(labels) + 2, column=3, padx=10, pady=10, sticky="w")

    # --- BUSCA UNIFICADA ---
    def _pesquisar(self):
        termo = self.e_busca.get().strip()
        if not termo:
            return

        # Limpa o campo após buscar
        self.e_busca.delete(0, "end")

        for row in self.tree_resultados.get_children():
            self.tree_resultados.delete(row)

        pessoas = listar_pessoas()

        # Tenta bater com nome, CPF ou número de série
        encontrados = [
            p for p in pessoas
            if termo.lower() in p["NomeCompleto"].lower()
            or termo in p["CPF"]
            or termo.upper() == (p.get("NumeroSerie") or "").upper()
        ]

        if not encontrados:
            messagebox.showinfo("Busca", "Nenhuma pessoa encontrada.")
            return

        for p in encontrados:
            self.tree_resultados.insert("", "end", values=(
                p["Id"], p["NomeCompleto"], p["TipoPessoa"], p.get("NumeroSerie") or "—"
            ))

    # --- SELECIONAR DA TABELA E PREENCHER PERFIL ---
    def _ao_selecionar(self, event):
        sel = self.tree_resultados.focus()
        if not sel:
            return

        valores = self.tree_resultados.item(sel)["values"]
        pessoa_id = valores[0]

        # Busca completa da pessoa pelo Id
        todas = listar_pessoas()
        pessoa = next((p for p in todas if p["Id"] == pessoa_id), None)
        if not pessoa:
            return

        self._pessoa_atual = pessoa
        self._preencher_campos(pessoa)
        self.btn_editar.configure(state="normal")

    def _preencher_campos(self, p):
        # Garante campos desabilitados ao preencher
        self._set_campos_estado("disabled")

        for chave, entry in self.campos.items():
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.insert(0, p.get(chave) or "")
            entry.configure(state="disabled")

        # Modalidades
        mods = listar_modalidades_da_pessoa(p["Id"])
        self.lbl_modalidades.configure(
            text=", ".join(m["Nome"] for m in mods) or "Nenhuma"
        )

        # Histórico
        self.txt_historico.configure(state="normal")
        self.txt_historico.delete("0.0", "end")

        if p["TipoPessoa"] == "ATLETA":
            times, torneios = buscar_historico_atleta(p["Id"])
            linhas  = "TIMES:\n"
            linhas += "\n".join(f"  - {t['Nome']} ({t['Modalidade']})" for t in times) or "  Sem time"
            linhas += "\n\nTORNEIOS:\n"
            linhas += "\n".join(f"  - {tr['Torneio']} (pelo {tr['TimeNome']})" for tr in torneios) or "  Nenhuma participação"
        else:
            treina  = buscar_times_treinados(p["Id"])
            linhas  = "TIMES QUE TREINA:\n"
            linhas += "\n".join(f"  - {t['Nome']} ({t['Modalidade']})" for t in treina) or "  Nenhum time"

        self.txt_historico.insert("end", linhas)
        self.txt_historico.configure(state="disabled")

    

    def _set_campos_estado(self, estado):
        for entry in self.campos.values():
            entry.configure(state=estado)

# ============================================================
# ABA VIDEO
# ============================================================
class AbaVideo(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self._sessao_id = None
        self._build()

    def _build(self):
        # Divide em esquerda (player) e direita (anotações)
        self.frame_esq = ctk.CTkFrame(self)
        self.frame_esq.pack(side="left", fill="both", expand=True, padx=(10, 4), pady=10)

        self.frame_dir = ctk.CTkFrame(self, width=320)
        self.frame_dir.pack(side="right", fill="y", padx=(4, 10), pady=10)
        self.frame_dir.pack_propagate(False)

        self._build_sessao()

    def _build_sessao(self):
        ctk.CTkLabel(self.frame_esq, text="Análise de Vídeo",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 4))

        # --- Criar sessão ---
        row_criar = ctk.CTkFrame(self.frame_esq)
        row_criar.pack(fill="x", padx=10, pady=6)

        self.e_titulo = ctk.CTkEntry(row_criar, placeholder_text="Título da sessão...", width=240)
        self.e_titulo.pack(side="left", padx=(0, 6))
        ctk.CTkButton(row_criar, text="✅ Criar Sessão",
                      command=self._criar_sessao).pack(side="left")

        # --- Buscar sessão existente ---
        row_busca = ctk.CTkFrame(self.frame_esq)
        row_busca.pack(fill="x", padx=10, pady=(0, 6))

        self.e_busca_sessao = ctk.CTkEntry(row_busca, placeholder_text="Buscar sessão existente...", width=240)
        self.e_busca_sessao.pack(side="left", padx=(0, 6))
        ctk.CTkButton(row_busca, text="🔍", width=40,
                      command=self._buscar_sessao).pack(side="left")

        # --- Tabela de sessões (usando CTkScrollableFrame em vez de tabela()) ---
        ctk.CTkLabel(self.frame_esq, text="Sessões encontradas:").pack(anchor="w", padx=12)

        import tkinter.ttk as ttk
        frame_tree_sessoes = ctk.CTkFrame(self.frame_esq)
        frame_tree_sessoes.pack(fill="x", padx=10, pady=4)

        self.tree_sessoes = ttk.Treeview(
            frame_tree_sessoes,
            columns=["Id", "Título", "Time", "Torneio", "Criado em"],
            show="headings", height=3
        )
        for col in ["Id", "Título", "Time", "Torneio", "Criado em"]:
            self.tree_sessoes.heading(col, text=col)
            self.tree_sessoes.column(col, width=100)
        self.tree_sessoes.pack(fill="x")
        self.tree_sessoes.bind("<ButtonRelease-1>", self._abrir_sessao)

        # Hint inicial
        self.lbl_hint = ctk.CTkLabel(
            self.frame_esq,
            text="Crie ou selecione uma sessão acima para começar.",
            text_color="gray"
        )
        self.lbl_hint.pack(pady=20)

        # --- Painel direito: integrantes ---
        ctk.CTkLabel(self.frame_dir, text="Integrantes na Sessão",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 4))

        row_add = ctk.CTkFrame(self.frame_dir)
        row_add.pack(fill="x", padx=8, pady=4)

        self.e_busca_integ = ctk.CTkEntry(row_add, placeholder_text="Nome ou série...", width=160)
        self.e_busca_integ.pack(side="left", padx=(0, 4))
        ctk.CTkButton(row_add, text="🔍", width=36,
                      command=self._buscar_integrante).pack(side="left")

        # Tabela resultado busca integrante
        frame_busca_integ = ctk.CTkFrame(self.frame_dir)
        frame_busca_integ.pack(fill="x", padx=8, pady=4)

        self.tree_busca_integ = ttk.Treeview(
            frame_busca_integ,
            columns=["Id", "Nome", "Tipo"],
            show="headings", height=3
        )
        for col in ["Id", "Nome", "Tipo"]:
            self.tree_busca_integ.heading(col, text=col)
            self.tree_busca_integ.column(col, width=80)
        self.tree_busca_integ.pack(fill="x")
        self.tree_busca_integ.bind("<ButtonRelease-1>", self._adicionar_integrante)

        ctk.CTkLabel(self.frame_dir, text="Na sessão:").pack(anchor="w", padx=8, pady=(8, 2))

        frame_integ_sessao = ctk.CTkFrame(self.frame_dir)
        frame_integ_sessao.pack(fill="x", padx=8, pady=4)

        self.tree_integ_sessao = ttk.Treeview(
            frame_integ_sessao,
            columns=["Id", "Nome", "Tipo"],
            show="headings", height=4
        )
        for col in ["Id", "Nome", "Tipo"]:
            self.tree_integ_sessao.heading(col, text=col)
            self.tree_integ_sessao.column(col, width=80)
        self.tree_integ_sessao.pack(fill="x")

        ctk.CTkButton(self.frame_dir, text="➖ Remover Selecionado",
                      command=self._remover_integrante, fg_color="#555").pack(pady=4)

    # --- SESSÕES ---
    def _criar_sessao(self):
        titulo = self.e_titulo.get().strip()
        if not titulo:
            messagebox.showwarning("Atenção", "Digite um título para a sessão.")
            return
        self._sessao_id = criar_sessao(titulo)
        self.e_titulo.delete(0, "end")
        messagebox.showinfo("Sessão criada", f"Sessão '{titulo}' pronta!")
        self._iniciar_player()

    def _buscar_sessao(self):
        termo = self.e_busca_sessao.get().strip().lower()
        self.e_busca_sessao.delete(0, "end")

        for row in self.tree_sessoes.get_children():
            self.tree_sessoes.delete(row)

        for s in listar_sessoes():
            if termo in s["Titulo"].lower():
                self.tree_sessoes.insert("", "end", values=(
                    s["Id"], s["Titulo"],
                    s.get("NomeTime") or "—",
                    s.get("NomeTorneio") or "—",
                    s["CriadoEm"][:10]
                ))

    def _abrir_sessao(self, event):
        sel = self.tree_sessoes.focus()
        if not sel:
            return
        valores = self.tree_sessoes.item(sel)["values"]
        self._sessao_id = valores[0]
        self._iniciar_player()
        self._atualizar_integrantes_sessao()

    def _sair_da_sessao(self):
            if hasattr(self, "_player_widget"):
                self._player_widget.destroy()
                del self._player_widget
            if hasattr(self, "_painel_widget"):
                self._painel_widget.destroy()
                del self._painel_widget

            self._sessao_id = None
            self.lbl_hint.pack(pady=20)

    def _iniciar_player(self):
        self.lbl_hint.pack_forget()
        if hasattr(self, "_player_widget"):
            self._player_widget.destroy()
        if hasattr(self, "_painel_widget"):
            self._painel_widget.destroy()

        self._player_widget = PlayerVideo(
            self.frame_esq,
            on_marcar=lambda s: self._painel_widget._marcar(),
            on_sair=self._sair_da_sessao
        )
        self._player_widget.pack(fill="both", expand=True, padx=10, pady=6)

        self._painel_widget = PainelAnotacoes(
            self.frame_dir,
            sessao_id=self._sessao_id,
            player=self._player_widget
        )
        self._painel_widget.pack(fill="both", expand=True, padx=4, pady=4)

        # Restaura vídeo/áudio salvos, se existirem
        self._player_widget.carregar_sessao_salva(self._sessao_id)

    # --- INTEGRANTES ---
    def _buscar_integrante(self):
        termo = self.e_busca_integ.get().strip().lower()
        self.e_busca_integ.delete(0, "end")

        for row in self.tree_busca_integ.get_children():
            self.tree_busca_integ.delete(row)

        filtrados = [
            p for p in listar_pessoas()
            if termo in p["NomeCompleto"].lower()
            or termo in (p.get("NumeroSerie") or "").lower()
        ]
        for p in filtrados:
            self.tree_busca_integ.insert("", "end", values=(
                p["Id"], p["NomeCompleto"], p["TipoPessoa"]
            ))

    def _adicionar_integrante(self, event):
        if not self._sessao_id:
            messagebox.showwarning("Atenção", "Abra uma sessão primeiro.")
            return
        sel = self.tree_busca_integ.focus()
        if not sel:
            return
        valores = self.tree_busca_integ.item(sel)["values"]
        adicionar_integrante_sessao(self._sessao_id, valores[0])
        self._atualizar_integrantes_sessao()
        if hasattr(self, "_painel_widget"):
            self._painel_widget._atualizar_combos_integrantes()

    def _remover_integrante(self):
        sel = self.tree_integ_sessao.focus()
        if not sel:
            return
        valores = self.tree_integ_sessao.item(sel)["values"]
        remover_integrante_sessao(self._sessao_id, valores[0])
        self._atualizar_integrantes_sessao()
        if hasattr(self, "_painel_widget"):
            self._painel_widget._atualizar_combos_integrantes()

    def _atualizar_integrantes_sessao(self):
        for row in self.tree_integ_sessao.get_children():
            self.tree_integ_sessao.delete(row)
        if not self._sessao_id:
            return
        for p in listar_integrantes_sessao(self._sessao_id):
            self.tree_integ_sessao.insert("", "end", values=(
                p["Id"], p["NomeCompleto"], p["TipoPessoa"]
            ))


# ============================================================
# JANELA PRINCIPAL  ← definida por último, depois de todas as abas
# ============================================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Torneios")
        self.geometry("960x680")
        self.resizable(True, True)
        from db.crud import sincronizar_status_torneios
        sincronizar_status_torneios()
        self._build_ui()

    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        abas = [
            (AbaPessoa,    "  👤 Pessoas  "),
            (AbaTorneio,   "  🏆 Torneios  "),
            (AbaTime,      "  👥 Times  "),
            (AbaInscricao, "  📝 Inscrições  "),
            (AbaMembro,    "  Membros  "),
            (AbaPerfil,    "  🔍 Perfis  "),
            (AbaVideo,     "  🎬 Análise  "),
        ]
        for Classe, titulo in abas:
            # página real do notebook: um frame comum, filho direto dele
            pagina = ctk.CTkFrame(notebook, fg_color="transparent")
            notebook.add(pagina, text=titulo)
            pagina.pack_propagate(True)

            # dentro da página, o scroll
            scroll = ctk.CTkScrollableFrame(pagina, fg_color="transparent")
            scroll.pack(fill="both", expand=True)

            # a aba de verdade vai dentro do scroll
            aba = Classe(scroll)
            aba.pack(fill="both", expand=True)

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    app = App()
    app.mainloop()
