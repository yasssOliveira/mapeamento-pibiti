import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import threading
import time
from PIL import Image, ImageTk

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

    def __init__(self, parent, on_marcar=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._cap          = None      # cv2.VideoCapture
        self._total_frames = 0
        self._fps          = 30
        self._tocando      = False
        self._frame_atual  = 0
        self._thread       = None
        self._audio_path   = None
        self._on_marcar    = on_marcar  # callback: recebe o segundo atual
        self._build()

    def _build(self):
        # Tela de vídeo
        self.lbl_video = ctk.CTkLabel(self, text="Nenhum vídeo carregado.",
                                       width=640, height=360)
        self.lbl_video.pack(padx=10, pady=(10, 4))

        # Barra de progresso (slider)
        self.slider = ctk.CTkSlider(self, from_=0, to=100, command=self._ao_mover_slider)
        self.slider.set(0)
        self.slider.pack(fill="x", padx=10, pady=4)

        # Tempo
        self.lbl_tempo = ctk.CTkLabel(self, text="00:00 / 00:00")
        self.lbl_tempo.pack()

        # Controles
        ctrl = ctk.CTkFrame(self)
        ctrl.pack(pady=6)

        self.btn_play = ctk.CTkButton(ctrl, text="▶ Play",  width=90, command=self.play)
        self.btn_play.grid(row=0, column=0, padx=6)

        ctk.CTkButton(ctrl, text="⏸ Pause", width=90, command=self.pause).grid(row=0, column=1, padx=6)
        ctk.CTkButton(ctrl, text="⏹ Stop",  width=90, command=self.stop).grid(row=0, column=2, padx=6)

        ctk.CTkButton(ctrl, text="📁 Carregar Vídeo", width=130,
                      command=self.carregar_video).grid(row=0, column=3, padx=6)
        ctk.CTkButton(ctrl, text="🎵 Carregar Áudio", width=130,
                      command=self.carregar_audio).grid(row=0, column=4, padx=6)

        ctk.CTkButton(ctrl, text="📍 Marcar aqui", width=120,
                      fg_color="#c0392b",
                      command=self._marcar_atual).grid(row=0, column=5, padx=6)

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
        self._fps          = self._cap.get(cv2.CAP_PROP_FPS) or 30
        self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.slider.configure(to=self._total_frames)
        self._atualizar_tempo(0)

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

    # --- CONTROLES ---
    def play(self):
        if not self._cap:
            messagebox.showwarning("Atenção", "Carregue um vídeo primeiro.")
            return
        if self._tocando:
            return
        self._tocando = True

        # Sincroniza áudio com o frame atual
        if AUDIO_OK and self._audio_path:
            segundo_atual = self._frame_atual / self._fps
            pygame.mixer.music.load(self._audio_path)
            pygame.mixer.music.play(start=segundo_atual)

        self._thread = threading.Thread(target=self._loop_video, daemon=True)
        self._thread.start()

    def pause(self):
        self._tocando = False
        if AUDIO_OK and pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()

    def stop(self):
        self._tocando = False
        self._frame_atual = 0
        if AUDIO_OK and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        if self._cap:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.slider.set(0)
        self._atualizar_tempo(0)

    # --- LOOP DE REPRODUÇÃO ---
    def _loop_video(self):
        while self._tocando and self._cap:
            ret, frame = self._cap.read()
            if not ret:
                self._tocando = False
                break

            self._frame_atual = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))

            # Converte frame para exibir no CTkLabel
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb).resize((640, 360))
            imgtk = ImageTk.PhotoImage(image=img)

            # Atualiza a UI na thread principal
            self.lbl_video.configure(image=imgtk, text="")
            self.lbl_video.image = imgtk
            self.slider.set(self._frame_atual)
            self._atualizar_tempo(self._frame_atual)

            time.sleep(1 / self._fps)

    # --- SLIDER ARRASTÁVEL ---
    def _ao_mover_slider(self, valor):
        if not self._cap:
            return
        frame = int(valor)
        self._frame_atual = frame
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame)

        # Sincroniza áudio ao pular posição
        if AUDIO_OK and self._audio_path and self._tocando:
            segundo = frame / self._fps
            pygame.mixer.music.play(start=segundo)

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
