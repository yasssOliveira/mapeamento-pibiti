import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import os
import threading
import time
from PIL import Image, ImageTk

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.crud import atualizar_sessao_video, buscar_sessao_por_id, listar_marcacoes

try:
    import pygame
    pygame.mixer.init()
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False


class PlayerVideo(ctk.CTkFrame):
    """
    Widget reutilizável de player de vídeo com:
    - Sincronização de áudio separado
    - Barra de progresso arrastável
    - Callbacks de marcação no tempo atual
    """

    def __init__(self, parent, on_marcar=None, on_sair=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._cap          = None
        self._total_frames = 0
        self._fps          = 30
        self._tocando      = False
        self._frame_atual  = 0
        self._after_id     = None
        self._audio_path   = None
        self._on_marcar    = on_marcar
        self._on_sair      = on_sair

        self._audio_offset      = 0.0
        self._video_duration    = 0.0
        self._audio_duration    = None
        self._px_per_sec        = 50
        self._drag_start_x      = None
        self._drag_start_offset = 0.0
        self._sessao_id         = None
        self._audio_after_id    = None
        self._audio_start_time  = None
        self._audio_start_pos   = 0.0

        self._marcacoes_cache   = []     # cache local, evita bater no banco a cada frame
        self._preview_after_id  = None   # controla o loop de atualização da prévia

        self._build()   

    def _build(self):
        # --- Linha superior: carregar vídeo/áudio + sair da sessão, na mesma direção ---
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", padx=10, pady=(6, 0))

        ctk.CTkButton(topo, text="📁 Carregar Vídeo", width=130,
                      command=self.carregar_video).pack(side="left", padx=(0, 6))
        ctk.CTkButton(topo, text="🎵 Carregar Áudio", width=130,
                      command=self.carregar_audio).pack(side="left", padx=(0, 6))

        ctk.CTkButton(topo, text="✖ Sair da Sessão", width=140,
                      fg_color="#c0392b",
                      command=self._sair_da_sessao).pack(side="right")

        # Tela de vídeo
        self.lbl_video = ctk.CTkLabel(self, text="Nenhum vídeo carregado.",
                                       width=640, height=360)
        self.lbl_video.pack(padx=10, pady=(10, 4))

        # --- Nomes dos arquivos carregados ---
        nomes_row = ctk.CTkFrame(self, fg_color="transparent")
        nomes_row.pack(fill="x", padx=10)
        self.lbl_nome_video = ctk.CTkLabel(nomes_row, text="🎬 Nenhum vídeo",
                                            anchor="w", text_color="gray")
        self.lbl_nome_video.pack(side="left", padx=(0, 12))
        self.lbl_nome_audio = ctk.CTkLabel(nomes_row, text="🎵 Nenhum áudio",
                                            anchor="w", text_color="gray")
        self.lbl_nome_audio.pack(side="left")

        # Barra de progresso (slider) do vídeo
        self.slider = ctk.CTkSlider(self, from_=0, to=100, command=self._ao_mover_slider)
        self.slider.set(0)
        self.slider.pack(fill="x", padx=10, pady=4)

        # --- Timeline de marcações (barras verticais sobre o vídeo) ---
        self.canvas_marcacoes = tk.Canvas(self, width=640, height=20,
                                           bg="#1a1a1a", highlightthickness=0)
        self.canvas_marcacoes.pack(fill="x", padx=10, pady=(0, 2))
        self.canvas_marcacoes.bind("<Button-1>", self._clicar_marcacao_timeline)

        # Tempo
        self.lbl_tempo = ctk.CTkLabel(self, text="00:00 / 00:00")
        self.lbl_tempo.pack()

        # --- Prévia das marcações (feitas e por vir) ---
        ctk.CTkLabel(self, text="Marcações:", anchor="w").pack(fill="x", padx=10, pady=(4, 0))
        self.frame_preview_marcacoes = ctk.CTkScrollableFrame(
            self, height=54, orientation="horizontal"
        )
        self.frame_preview_marcacoes.pack(fill="x", padx=10, pady=(2, 6))

        # --- Controles principais: Play/Stop e Marcar aqui, alinhados à esquerda ---
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=10, pady=6)

        self.btn_play = ctk.CTkButton(ctrl, text="▶ Play", width=90,
                                       command=self._alternar_play_pause)
        self.btn_play.grid(row=0, column=0, padx=(0, 6), sticky="w")

        ctk.CTkButton(ctrl, text="⏹ Stop", width=90,
                      command=self.stop).grid(row=0, column=1, padx=6, sticky="w")

        ctk.CTkButton(ctrl, text="📍 Marcar aqui", width=120,
                      fg_color="#c0392b",
                      command=self._marcar_atual).grid(row=0, column=2, padx=6, sticky="w")

        # --- Timeline visual de sincronização (arrastável) ---
        ctk.CTkLabel(self, text="Arraste a trilha de áudio para sincronizar:",
                     anchor="w").pack(fill="x", padx=10, pady=(6, 0))

        zoom_row = ctk.CTkFrame(self, fg_color="transparent")
        zoom_row.pack(fill="x", padx=10, pady=(2, 0))
        ctk.CTkButton(zoom_row, text="🔍−", width=40,
                      command=lambda: self._zoom_timeline(-15)).pack(side="left", padx=2)
        ctk.CTkButton(zoom_row, text="🔍+", width=40,
                      command=lambda: self._zoom_timeline(15)).pack(side="left", padx=2)

        self.canvas_timeline = tk.Canvas(self, width=640, height=90,
                                          bg="#1a1a1a", highlightthickness=0)
        self.canvas_timeline.pack(fill="x", padx=10, pady=(4, 4))

        self.canvas_timeline.tag_bind("audio_bar", "<Button-1>", self._iniciar_drag_audio)
        self.canvas_timeline.tag_bind("audio_bar", "<B1-Motion>", self._arrastar_audio)
        self.canvas_timeline.tag_bind("audio_bar", "<ButtonRelease-1>", self._soltar_audio)

        # --- Botões de ajuste fino do offset, abaixo da trilha de arrastar ---
        sync = ctk.CTkFrame(self)
        sync.pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkLabel(sync, text="Sincronizar áudio:").pack(side="left", padx=(0, 8))

        ctk.CTkButton(sync, text="◀◀ -1s", width=60,
                      command=lambda: self._ajustar_offset(-1.0)).pack(side="left", padx=2)
        ctk.CTkButton(sync, text="◀ -0.1s", width=60,
                      command=lambda: self._ajustar_offset(-0.1)).pack(side="left", padx=2)

        self.lbl_offset = ctk.CTkLabel(sync, text="+0.00s", width=70)
        self.lbl_offset.pack(side="left", padx=6)

        ctk.CTkButton(sync, text="+0.1s ▶", width=60,
                      command=lambda: self._ajustar_offset(0.1)).pack(side="left", padx=2)
        ctk.CTkButton(sync, text="+1s ▶▶", width=60,
                      command=lambda: self._ajustar_offset(1.0)).pack(side="left", padx=2)

        ctk.CTkButton(sync, text="↺ Reset", width=70, fg_color="#555",
                      command=self._reset_offset).pack(side="left", padx=(10, 0))

        self.e_offset = ctk.CTkEntry(sync, width=70, placeholder_text="ex: 1.5")
        self.e_offset.pack(side="left", padx=(10, 2))
        ctk.CTkButton(sync, text="Aplicar", width=70,
                      command=self._aplicar_offset_manual).pack(side="left")

        self._desenhar_timeline()

        # --- Progresso do áudio ---
        ctk.CTkLabel(self, text="Progresso do áudio:", anchor="w").pack(
            fill="x", padx=10, pady=(6, 0)
        )
        self.audio_progress = ctk.CTkProgressBar(self, width=640)
        self.audio_progress.set(0)
        self.audio_progress.pack(fill="x", padx=10, pady=(2, 0))

        self.lbl_audio_tempo = ctk.CTkLabel(self, text="00:00 / 00:00")
        self.lbl_audio_tempo.pack(pady=(0, 6))

    def _desenhar_timeline(self):
        """Redesenha as duas trilhas (vídeo fixo, áudio na posição do offset)."""
        c = self.canvas_timeline
        c.delete("all")

        largura  = int(c["width"])
        altura   = int(c["height"])
        marker_x = largura // 2  # ponto que representa o segundo 0 do vídeo

        # Linha de referência (segundo 0)
        c.create_line(marker_x, 0, marker_x, altura, fill="#e74c3c", dash=(3, 2))
        c.create_text(marker_x, 8, text="0:00", fill="#e74c3c", font=("Arial", 8))

        # Réguas de tempo (a cada segundo, visível só se houver espaço)
        if self._px_per_sec >= 15:
            passo = 1
        else:
            passo = 5
        max_s = largura // (2 * max(self._px_per_sec, 1))
        for s in range(-max_s, max_s + 1):
            if s == 0 or s % passo != 0:
                continue
            x = marker_x + s * self._px_per_sec
            c.create_line(x, altura - 6, x, altura, fill="#555")
            c.create_text(x, altura - 12, text=f"{s}s", fill="#888", font=("Arial", 7))

        # Trilha de VÍDEO (fixa, sempre começa no marker)
        dur_v = self._video_duration or 0
        fim_v = marker_x + dur_v * self._px_per_sec
        c.create_rectangle(marker_x, 15, fim_v, 38,
                            fill="#1f6aa5", outline="")
        c.create_text(marker_x + 6, 26, text="🎬 Vídeo", anchor="w",
                      fill="white", font=("Arial", 9, "bold"))

        # Trilha de ÁUDIO (móvel, posicionada pelo offset)
        dur_a = self._audio_duration or dur_v or 30
        inicio_a = marker_x + self._audio_offset * self._px_per_sec
        fim_a    = inicio_a + dur_a * self._px_per_sec
        c.create_rectangle(inicio_a, 48, fim_a, 71,
                            fill="#2d6a4f", outline="", tags="audio_bar")
        c.create_text(inicio_a + 6, 59, text="🎵 Áudio", anchor="w",
                      fill="white", font=("Arial", 9, "bold"), tags="audio_bar")

        self.lbl_offset.configure(text=f"{self._audio_offset:+.2f}s")
    # --- CARREGAMENTO ---
    def carregar_video(self):
        path = filedialog.askopenfilename(
            title="Selecionar Vídeo",
            filetypes=[("Vídeos", "*.mp4 *.avi *.mov *.mkv *.wmv")]
        )
        if not path:
            return
        self.stop()
        self._cap = cv2.VideoCapture(path)

        if not self._cap.isOpened():
            messagebox.showerror("Erro ao abrir vídeo",
                                  "Não foi possível abrir este arquivo de vídeo.\n"
                                  "Verifique o formato/codec.")
            self._cap = None
            return

        self._fps          = self._cap.get(cv2.CAP_PROP_FPS) or 30
        self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.slider.configure(to=self._total_frames)
        self._atualizar_tempo(0)

        self._video_duration = self._total_frames / self._fps if self._fps else 0
        self._desenhar_timeline()

        self.lbl_nome_video.configure(text=f"🎬 {os.path.basename(path)}",
                                       text_color="white")

        self._mostrar_frame_atual()

        self.lbl_nome_video.configure(text=f"🎬 {os.path.basename(path)}",
                                       text_color="white")

        self._mostrar_frame_atual()

        if self._sessao_id:
            atualizar_sessao_video(self._sessao_id, caminho_video=path)

        self.atualizar_marcacoes()

    def carregar_audio(self):
        if not AUDIO_OK:
            messagebox.showwarning("Pygame não instalado",
                                   "Instale pygame para usar áudio separado:\npip install pygame")
            return
        path = filedialog.askopenfilename(
            title="Selecionar Áudio",
            filetypes=[("Áudio", "*.mp3 *.wav *.ogg *.aac")]
        )
        if path:
            self._audio_path = path
            self._audio_offset = 0.0
            self._audio_duration = self._obter_duracao_audio(path)
            self._desenhar_timeline()
            self.lbl_nome_audio.configure(text=f"🎵 {os.path.basename(path)}",
                                           text_color="white")

            if self._sessao_id:
                atualizar_sessao_video(self._sessao_id,
                                        caminho_audio=path, audio_offset=0.0)
            
    # --- CONTROLES ---
    def play(self):
        if not self._cap:
            messagebox.showwarning("Atenção", "Carregue um vídeo primeiro.")
            return
        if self._tocando:
            return
        self._tocando = True

        segundo_atual = self._frame_atual / self._fps
        try:
            self._tocar_audio_sincronizado(segundo_atual)
        except Exception as e:
            print(f"[aviso] Falha ao sincronizar áudio: {e}")

        self._tick_video()
        self._tick_preview()

    def pause(self):
        self._tocando = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        if self._audio_after_id:
            self.after_cancel(self._audio_after_id)
            self._audio_after_id = None
        if AUDIO_OK and pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
        if self._preview_after_id:
            self.after_cancel(self._preview_after_id)
            self._preview_after_id = None

    def stop(self):
        self._tocando = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        if self._audio_after_id:
            self.after_cancel(self._audio_after_id)
            self._audio_after_id = None
        self._frame_atual = 0
        if AUDIO_OK and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        if self._cap:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        if self._preview_after_id:
            self.after_cancel(self._preview_after_id)
            self._preview_after_id = None
        self.slider.set(0)
        self._atualizar_tempo(0)
        self.audio_progress.set(0)
        self.lbl_audio_tempo.configure(text="00:00 / 00:00")
        self.btn_play.configure(text="▶ Play")

    # --- LOOP DE REPRODUÇÃO ---
    def _tick_video(self):
        if not self._tocando or not self._cap:
            return

        ret, frame = self._cap.read()
        if not ret:
            self._tocando = False
            self.btn_play.configure(text="▶ Play")
            return

        self._frame_atual = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb).resize((640, 360))
        imgtk = ImageTk.PhotoImage(image=img)

        self.lbl_video.configure(image=imgtk, text="")
        self.lbl_video.image = imgtk
        self.slider.set(self._frame_atual)
        self._atualizar_tempo(self._frame_atual)
        self._desenhar_marcacoes_timeline()

        delay_ms = int(1000 / self._fps) if self._fps else 33
        self._after_id = self.after(delay_ms, self._tick_video)

    # --- SLIDER ARRASTÁVEL ---
    def _ao_mover_slider(self, valor):
        if not self._cap:
            return
        frame = int(valor)
        self._frame_atual = frame
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame)

        if self._tocando:
            segundo = frame / self._fps
            self._tocar_audio_sincronizado(segundo)
        else:
            self._mostrar_frame_atual()

        self._atualizar_tempo(frame)

    # --- MARCAÇÃO ---
    def _marcar_atual(self):
        if self._on_marcar:
            segundo = self._frame_atual / self._fps
            self._on_marcar(segundo)

    # --- HELPERS ---
    def _atualizar_tempo(self, frame):
        def fmt(s): return f"{int(s)//60:02d}:{int(s)%60:02d}"
        atual = frame / self._fps
        total = self._total_frames / self._fps
        self.lbl_tempo.configure(text=f"{fmt(atual)} / {fmt(total)}")

    def segundo_atual(self):
        return self._frame_atual / self._fps if self._fps else 0

    def ir_para_segundo(self, segundo):
        """Pula o vídeo (e reposiciona o áudio, se tocando) para o tempo dado."""
        if not self._cap or not self._fps:
            return

        frame = int(segundo * self._fps)
        frame = max(0, min(frame, self._total_frames))

        self._frame_atual = frame
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
        self.slider.set(frame)
        self._atualizar_tempo(frame)
        self._desenhar_marcacoes_timeline()

        if self._tocando:
            self._tocar_audio_sincronizado(frame / self._fps)
        else:
            self._mostrar_frame_atual()
    
    def _ajustar_offset(self, delta):
        self._audio_offset += delta
        self._desenhar_timeline()
        if self._tocando:
            self._tocar_audio_sincronizado(self.segundo_atual())
        if self._sessao_id:
            atualizar_sessao_video(self._sessao_id, audio_offset=self._audio_offset)

    def _reset_offset(self):
        self._audio_offset = 0.0
        self._desenhar_timeline()
        if self._tocando:
            self._tocar_audio_sincronizado(self.segundo_atual())
        if self._sessao_id:
            atualizar_sessao_video(self._sessao_id, audio_offset=self._audio_offset)

    def _aplicar_offset_manual(self):
        texto = self.e_offset.get().strip().replace(",", ".")
        try:
            valor = float(texto)
        except ValueError:
            messagebox.showerror("Valor inválido", "Digite um número, ex: 1.5 ou -0.75")
            return
        self._audio_offset = valor
        self._desenhar_timeline()
        if self._tocando:
            self._tocar_audio_sincronizado(self.segundo_atual())
        if self._sessao_id:
            atualizar_sessao_video(self._sessao_id, audio_offset=self._audio_offset)

    def _tocar_audio_sincronizado(self, segundo_video):
        """
        Toca o áudio já considerando o offset de sincronização configurado.

        Convenção: offset positivo significa que a trilha de áudio começa
        MAIS TARDE em relação ao vídeo. offset negativo significa que o
        áudio começa ANTES do vídeo.
        """
        if not (AUDIO_OK and self._audio_path):
            return

        posicao_audio = segundo_video - self._audio_offset

        # cancela um loop de progresso anterior, se houver
        if self._audio_after_id:
            self.after_cancel(self._audio_after_id)
            self._audio_after_id = None

        try:
            if posicao_audio >= 0:
                pygame.mixer.music.load(self._audio_path)
                pygame.mixer.music.play(start=posicao_audio)
                self._audio_start_time = time.time()
                self._audio_start_pos  = posicao_audio
                self._tick_audio_progress()
            else:
                delay = -posicao_audio
                pygame.mixer.music.stop()

                def _tocar_apos_delay():
                    time.sleep(delay)
                    if self._tocando:
                        try:
                            pygame.mixer.music.load(self._audio_path)
                            pygame.mixer.music.play(start=0)
                            self._audio_start_time = time.time()
                            self._audio_start_pos  = 0.0
                            self._tick_audio_progress()
                        except Exception as e:
                            print(f"[aviso] Falha ao tocar áudio atrasado: {e}")

                threading.Thread(target=_tocar_apos_delay, daemon=True).start()
        except Exception as e:
            print(f"[aviso] Falha ao carregar/tocar áudio: {e}")

    def _iniciar_drag_audio(self, event):
        self._drag_start_x = event.x
        self._drag_start_offset = self._audio_offset
    
    def _arrastar_audio(self, event):
        if self._drag_start_x is None:
            return
        delta_px = event.x - self._drag_start_x
        self._audio_offset = self._drag_start_offset + (delta_px / self._px_per_sec)
        self._desenhar_timeline()

    def _soltar_audio(self, event):
        self._drag_start_x = None
        if self._tocando:
            self._tocar_audio_sincronizado(self.segundo_atual())
        if self._sessao_id:
            atualizar_sessao_video(self._sessao_id, audio_offset=self._audio_offset)
    
    def _zoom_timeline(self, delta):
        self._px_per_sec = max(10, min(200, self._px_per_sec + delta))
        self._desenhar_timeline()

    def _obter_duracao_audio(self, path):
        """Tenta obter a duração do áudio para desenhar a barra proporcionalmente."""
        if not AUDIO_OK:
            return None
        try:
            som = pygame.mixer.Sound(path)
            return som.get_length()
        except Exception:
            return None  # ex: mp3 às vezes não é suportado pelo Sound()
    
    def _mostrar_frame_atual(self):
        """Lê e exibe o frame atual do vídeo, sem avançar a reprodução."""
        if not self._cap:
            return
        ret, frame = self._cap.read()
        if not ret:
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb).resize((640, 360))
        imgtk = ImageTk.PhotoImage(image=img)

        self.lbl_video.configure(image=imgtk, text="")
        self.lbl_video.image = imgtk

        # Volta o ponteiro para o frame que estava antes da leitura,
        # já que .read() avança a posição
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, self._frame_atual)


    def _sair_da_sessao(self):
        self.stop()
        if self._on_sair:
            self._on_sair()

    def _alternar_play_pause(self):
        if self._tocando:
            self.pause()
            self.btn_play.configure(text="▶ Play")
        else:
            self.play()
            self.btn_play.configure(text="⏸ Pause")

    def carregar_sessao_salva(self, sessao_id):
        """Chamado ao abrir uma sessão: recarrega vídeo/áudio/offset salvos, se existirem."""
        self._sessao_id = sessao_id
        sessao = buscar_sessao_por_id(sessao_id)
        if not sessao:
            return

        caminho_video = sessao.get("CaminhoVideo")
        caminho_audio = sessao.get("CaminhoAudio")
        offset        = sessao.get("AudioOffset") or 0.0

        if caminho_video and os.path.isfile(caminho_video):
            self._cap = cv2.VideoCapture(caminho_video)
            if self._cap.isOpened():
                self._fps          = self._cap.get(cv2.CAP_PROP_FPS) or 30
                self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.slider.configure(to=self._total_frames)
                self._atualizar_tempo(0)
                self._video_duration = self._total_frames / self._fps if self._fps else 0
                self.lbl_nome_video.configure(
                    text=f"🎬 {os.path.basename(caminho_video)}", text_color="white"
                )
                self._mostrar_frame_atual()
            else:
                self._cap = None

        if caminho_audio and os.path.isfile(caminho_audio):
            self._audio_path = caminho_audio
            self._audio_duration = self._obter_duracao_audio(caminho_audio)
            self.lbl_nome_audio.configure(
                text=f"🎵 {os.path.basename(caminho_audio)}", text_color="white"
            )

        self._audio_offset = offset
        self._desenhar_timeline()
        self.atualizar_marcacoes()

    def _tick_audio_progress(self):
        """
        Atualiza a barra de progresso do áudio com base em tempo real decorrido,
        de forma independente do loop de vídeo — continua rodando mesmo que o
        vídeo já tenha terminado, mantendo o áudio como referência.
        """
        if not (AUDIO_OK and self._audio_path):
            return

        # Fallback: se não conseguimos detectar a duração real do áudio
        # (comum com MP3, que o pygame.mixer.Sound não lê bem), usa a
        # duração do vídeo como referência aproximada para a barra não
        # ficar travada.
        duracao_ref = self._audio_duration or self._video_duration or 60

        if not pygame.mixer.music.get_busy():
            if self._tocando:
                self.audio_progress.set(1.0)
                def fmt(s):
                    return f"{int(s)//60:02d}:{int(s)%60:02d}"
                self.lbl_audio_tempo.configure(
                    text=f"{fmt(duracao_ref)} / {fmt(duracao_ref)}"
                )
            return

        decorrido = time.time() - self._audio_start_time
        pos_audio = self._audio_start_pos + decorrido
        pos_audio = max(0, min(pos_audio, duracao_ref))
        ratio = pos_audio / duracao_ref if duracao_ref else 0

        self.audio_progress.set(ratio)

        def fmt(s):
            return f"{int(s)//60:02d}:{int(s)%60:02d}"
        self.lbl_audio_tempo.configure(
            text=f"{fmt(pos_audio)} / {fmt(duracao_ref)}"
        )

        self._audio_after_id = self.after(200, self._tick_audio_progress)

    def _recarregar_cache_marcacoes(self):
        if not self._sessao_id:
            self._marcacoes_cache = []
            return
        try:
            self._marcacoes_cache = listar_marcacoes(self._sessao_id)
        except Exception as e:
            print(f"[aviso] Falha ao carregar marcações: {e}")
            self._marcacoes_cache = []

    def _desenhar_marcacoes_timeline(self):
        """Desenha as barras de marcação e a posição atual (playhead) sobre a timeline do vídeo."""
        c = self.canvas_marcacoes
        c.delete("all")

        duracao_total = self._video_duration
        if not duracao_total:
            return

        largura = c.winfo_width()
        if largura <= 1:
            # widget ainda não foi renderizado (largura real indisponível);
            # tenta de novo no próximo ciclo em vez de desenhar errado
            self.after(50, self._desenhar_marcacoes_timeline)
            return

        for m in self._marcacoes_cache:
            seg = m.get("SegundoMarca", 0)
            cor = m.get("Cor") or "#e74c3c"
            x = (seg / duracao_total) * largura
            c.create_line(x, 0, x, 20, fill=cor, width=2)

        # Playhead: posição atual do vídeo
        seg_atual = self.segundo_atual()
        x_atual = (seg_atual / duracao_total) * largura
        c.create_line(x_atual, 0, x_atual, 20, fill="white", width=1, dash=(2, 1))

    def _clicar_marcacao_timeline(self, event):
        """Clicar na timeline de marcações pula o vídeo para aquele ponto."""
        if not self._cap or not self._total_frames or not self._video_duration:
            return
        largura = self.canvas_marcacoes.winfo_width()
        if largura <= 1:
            return
        segundo = (event.x / largura) * self._video_duration
        frame = int(segundo * self._fps)
        frame = max(0, min(frame, self._total_frames))

        self._frame_atual = frame
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
        self.slider.set(frame)
        self._atualizar_tempo(frame)
        self._desenhar_marcacoes_timeline()

        if not self._tocando:
            self._mostrar_frame_atual()

    def _atualizar_preview_marcacoes(self):
        for w in self.frame_preview_marcacoes.winfo_children():
            w.destroy()

        if not self._marcacoes_cache:
            ctk.CTkLabel(self.frame_preview_marcacoes, text="Nenhuma marcação ainda.",
                         text_color="gray").pack(side="left", padx=6, pady=10)
            return

        atual = self.segundo_atual()

        def fmt(s):
            return f"{int(s)//60:02d}:{int(s)%60:02d}"

        for m in self._marcacoes_cache:
            seg    = m.get("SegundoMarca", 0)
            cor    = m.get("Cor") or "#555555"
            rotulo = m.get("Reacao") or "📝 Nota"
            feita  = seg <= atual

            chip = ctk.CTkFrame(self.frame_preview_marcacoes, fg_color=cor, corner_radius=6)
            chip.pack(side="left", padx=4, pady=4)

            texto = f"{'✔' if feita else '⏳'} {fmt(seg)}  {rotulo}"
            ctk.CTkLabel(chip, text=texto, text_color="white",
                         font=ctk.CTkFont(size=10)).pack(padx=8, pady=4)

    def _tick_preview(self):
        """Loop leve (a cada 500ms) que atualiza os ✔/⏳ da prévia enquanto o vídeo toca."""
        if not self._tocando:
            self._preview_after_id = None
            return
        self._atualizar_preview_marcacoes()
        self._preview_after_id = self.after(500, self._tick_preview)

    def atualizar_marcacoes(self):
        """
        Chamado externamente (pelo PainelAnotacoes) sempre que uma marcação é
        criada, conectada ou removida — atualiza a timeline e a prévia.
        """
        self._recarregar_cache_marcacoes()
        self._desenhar_marcacoes_timeline()
        self._atualizar_preview_marcacoes()
