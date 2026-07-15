import customtkinter as ctk
from tkinter import messagebox, simpledialog

# video/anotacoes.py — primeiras linhas
import sys
import os

# Sobe um nível (de video/ para pbt/) e adiciona ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.crud import (
    listar_marcacoes,
    criar_marcacao,
    deletar_marcacao,
    vincular_integrante_marcacao,
    listar_integrantes_marcacao,
    criar_conexao,
    listar_conexoes,
    listar_integrantes_sessao,
    listar_botoes,
    criar_botao,
    deletar_botao,
)



def fmt_tempo(s):
    return f"{int(s)//60:02d}:{int(s)%60:02d}"


class PainelAnotacoes(ctk.CTkFrame):
    """
    Painel lateral de marcações.
    Recebe sessao_id e player (para pegar o segundo atual).
    """

    def __init__(self, parent, sessao_id, player, **kwargs):
        super().__init__(parent, **kwargs)
        self.sessao_id = sessao_id
        self.player    = player
        self._build()
        self._carregar_botoes()
        self._carregar_marcacoes()

    def _build(self):
        ctk.CTkLabel(self, text="Marcações",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(10, 4))

        # --- Botões de reação ---
        ctk.CTkLabel(self, text="Reações rápidas:").pack(anchor="w", padx=8)
        self.frame_botoes = ctk.CTkFrame(self)
        self.frame_botoes.pack(fill="x", padx=8, pady=4)

        # Criar botão personalizado
        row_custom = ctk.CTkFrame(self)
        row_custom.pack(fill="x", padx=8, pady=(0, 6))
        self.e_novo_botao = ctk.CTkEntry(row_custom, placeholder_text="Nome da reação...", width=160)
        self.e_novo_botao.pack(side="left", padx=(0, 4))
        ctk.CTkButton(row_custom, text="➕ Criar Reação", width=120,
                      command=self._criar_botao_custom).pack(side="left")

        # --- Campo de descrição da marcação ---
        ctk.CTkLabel(self, text="Descrição da marcação:").pack(anchor="w", padx=8)
        self.e_descricao = ctk.CTkEntry(self, placeholder_text="Ex: ficou com raiva, saiu da roda...", width=280)
        self.e_descricao.pack(fill="x", padx=8, pady=4)

        # --- Integrantes da marcação ---
        ctk.CTkLabel(self, text="Integrantes envolvidos:").pack(anchor="w", padx=8)
        self.frame_integrantes = ctk.CTkScrollableFrame(self, height=80)
        self.frame_integrantes.pack(fill="x", padx=8, pady=4)

        # --- Conexão entre integrantes ---
        ctk.CTkLabel(self, text="Conectar dois integrantes:").pack(anchor="w", padx=8)
        row_con = ctk.CTkFrame(self)
        row_con.pack(fill="x", padx=8, pady=4)

        self.combo_p1 = ctk.CTkComboBox(row_con, values=[], width=120)
        self.combo_p1.pack(side="left", padx=2)
        ctk.CTkLabel(row_con, text="↔").pack(side="left")
        self.combo_p2 = ctk.CTkComboBox(row_con, values=[], width=120)
        self.combo_p2.pack(side="left", padx=2)

        self.combo_tipo_reacao = ctk.CTkComboBox(
            self,
            values=["Conversa Paralela", "Conflito", "Colaboração", "Outro"],
            width=280
        )
        self.combo_tipo_reacao.pack(fill="x", padx=8, pady=2)

        ctk.CTkButton(self, text="🔗 Registrar Conexão",
                      command=self._registrar_conexao).pack(pady=4)

        # --- Botão de marcação manual ---
        ctk.CTkButton(self, text="📍 Marcar no tempo atual",
                      fg_color="#c0392b",
                      command=lambda: self._marcar(botao_id=None)).pack(pady=6)

        # --- Lista de marcações ---
        ctk.CTkLabel(self, text="Timeline:",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=8, pady=(8, 2))

        self.lista_marcacoes = ctk.CTkScrollableFrame(self, height=200)
        self.lista_marcacoes.pack(fill="both", expand=True, padx=8, pady=(0, 10))

    # --- BOTÕES DE REAÇÃO ---
    def _carregar_botoes(self):
        for w in self.frame_botoes.winfo_children():
            w.destroy()

        for b in listar_botoes():
            btn = ctk.CTkButton(
                self.frame_botoes,
                text=b["Rotulo"],
                fg_color=b["Cor"],
                width=120,
                command=lambda bid=b["Id"]: self._marcar(botao_id=bid)
            )
            btn.pack(side="left", padx=3, pady=3)

        self._atualizar_combos_integrantes()

    def _criar_botao_custom(self):
        nome = self.e_novo_botao.get().strip()
        if not nome:
            messagebox.showwarning("Atenção", "Digite o nome da reação.")
            return
        criar_botao(nome)
        self.e_novo_botao.delete(0, "end")
        self._carregar_botoes()

    # --- INTEGRANTES ---
    def _atualizar_combos_integrantes(self):
        integrantes = listar_integrantes_sessao(self.sessao_id)
        nomes = [p["NomeCompleto"] for p in integrantes]

        # Limpa checkboxes de integrantes
        for w in self.frame_integrantes.winfo_children():
            w.destroy()

        self._vars_integrantes = {}
        for p in integrantes:
            var = ctk.BooleanVar()
            ctk.CTkCheckBox(self.frame_integrantes, text=p["NomeCompleto"], variable=var).pack(anchor="w")
            self._vars_integrantes[p["Id"]] = var

        # Atualiza combos de conexão
        self.combo_p1.configure(values=nomes)
        self.combo_p2.configure(values=nomes)
        if nomes:
            self.combo_p1.set(nomes[0])
            self.combo_p2.set(nomes[-1] if len(nomes) > 1 else nomes[0])

    # --- MARCAÇÕES ---
    def _marcar(self, botao_id=None):
        segundo = self.player.segundo_atual()
        descricao = self.e_descricao.get().strip() or None

        mid = criar_marcacao(self.sessao_id, segundo, descricao, botao_id)

        # Vincula integrantes selecionados
        for pid, var in self._vars_integrantes.items():
            if var.get():
                vincular_integrante_marcacao(mid, pid)

        self.e_descricao.delete(0, "end")
        # Desmarca todos os checkboxes
        for var in self._vars_integrantes.values():
            var.set(False)

        self._carregar_marcacoes()

    def _registrar_conexao(self):
        segundo = self.player.segundo_atual()
        integrantes = listar_integrantes_sessao(self.sessao_id)

        nome_p1 = self.combo_p1.get()
        nome_p2 = self.combo_p2.get()
        tipo    = self.combo_tipo_reacao.get()

        p1 = next((p for p in integrantes if p["NomeCompleto"] == nome_p1), None)
        p2 = next((p for p in integrantes if p["NomeCompleto"] == nome_p2), None)

        if not p1 or not p2 or p1["Id"] == p2["Id"]:
            messagebox.showwarning("Atenção", "Selecione dois integrantes diferentes.")
            return

        mid = criar_marcacao(
            self.sessao_id, segundo,
            descricao=f"{nome_p1} ↔ {nome_p2}: {tipo}"
        )
        vincular_integrante_marcacao(mid, p1["Id"])
        vincular_integrante_marcacao(mid, p2["Id"])
        criar_conexao(mid, p1["Id"], p2["Id"], tipo)

        self._carregar_marcacoes()

    def _carregar_marcacoes(self):
        for w in self.lista_marcacoes.winfo_children():
            w.destroy()

        for m in listar_marcacoes(self.sessao_id):
            self._renderizar_marcacao(m)

    def _renderizar_marcacao(self, m):
        card = ctk.CTkFrame(self.lista_marcacoes, fg_color="#2b2b2b", corner_radius=6)
        card.pack(fill="x", pady=3, padx=2)

        tempo   = fmt_tempo(m["SegundoMarca"])
        reacao  = m.get("Reacao") or "📝 Nota"
        desc    = m.get("Descricao") or ""
        cor     = m.get("Cor") or "#555555"

        header = ctk.CTkFrame(card, fg_color=cor, corner_radius=4)
        header.pack(fill="x", padx=4, pady=(4, 0))
        ctk.CTkLabel(header, text=f"⏱ {tempo}  |  {reacao}",
                     font=ctk.CTkFont(weight="bold")).pack(side="left", padx=6)

        # Botão deletar
        ctk.CTkButton(header, text="✖", width=28, fg_color="transparent",
                      command=lambda mid=m["Id"]: self._deletar(mid)).pack(side="right", padx=4)

        if desc:
            ctk.CTkLabel(card, text=desc, anchor="w", wraplength=260).pack(
                fill="x", padx=8, pady=2
            )

        # Integrantes
        pessoas = listar_integrantes_marcacao(m["Id"])
        if pessoas:
            nomes = ", ".join(p["NomeCompleto"] for p in pessoas)
            ctk.CTkLabel(card, text=f"👤 {nomes}", anchor="w",
                         text_color="gray").pack(fill="x", padx=8, pady=(0, 2))

        # Conexões
        conexoes = listar_conexoes(m["Id"])
        for c in conexoes:
            ctk.CTkLabel(card,
                         text=f"🔗 {c['Pessoa1']} ↔ {c['Pessoa2']} ({c['TipoReacao']})",
                         anchor="w", text_color="#aaa").pack(fill="x", padx=8)

    def _deletar(self, marcacao_id):
        if messagebox.askyesno("Confirmar", "Deletar esta marcação?"):
            deletar_marcacao(marcacao_id)
            self._carregar_marcacoes()
