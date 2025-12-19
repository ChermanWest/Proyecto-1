# interfaz.py

import tkinter as tk
import customtkinter as ctk
from queue import Queue, Empty
from Conexion import BLEWorker

class LegoGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Control LEGO Spike Prime - SP 7")
        self.geometry("500x650")
        self.resizable(False, False)

        self.log_queue = Queue()
        self.worker = BLEWorker(self.log_queue)
        self.emergency = False
        
        # --- RASTREADOR DE ESTADO PARA EVITAR DELAY ---
        # Esto guarda si una tecla ya está siendo presionada
        self.pressed_keys = {"w": False, "a": False, "s": False, "d": False}
        
        # Colores
        self.color_green = "#2EA043"
        self.color_red = "#DA3633"
        self.color_blue = "#1F6FEB"
        self.color_gray = "#30363D"
        self.color_yellow = "#D29922"

        self._build_ui()

        # Habilitar control por teclado (W A S D)
        self.bind_all("<KeyPress>", self._on_key_press)
        self.bind_all("<KeyRelease>", self._on_key_release)
        self.focus_set()

        self._poll_logs()

    def _build_ui(self):
        # Header
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(20, 10))

        title_lbl = ctk.CTkLabel(self.header_frame, text="Spike Prime Control", 
                                 font=ctk.CTkFont(size=20, weight="bold"))
        title_lbl.pack(side="left")

        right_header = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        right_header.pack(side="right")

        self.status_indicator = ctk.CTkButton(right_header, text="", width=14, height=14,
                                              corner_radius=7, fg_color=self.color_red,
                                              hover=False, state="disabled")
        self.status_indicator.pack(side="left", padx=(0, 10))

        self.lbl_status = ctk.CTkLabel(right_header, text="Sin conexión", 
                                      text_color="gray", font=ctk.CTkFont(size=12))
        self.lbl_status.pack(side="left", padx=(0, 10))

        self.btn_connect = ctk.CTkButton(right_header, text="Conectar", width=90,
                                         fg_color=self.color_gray,
                                         command=self.toggle_connection)
        self.btn_connect.pack(side="left")

        # PANEL D-PAD
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=10)
        
        dpad_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        dpad_container.place(relx=0.5, rely=0.5, anchor="center")

        btn_style = {
            "font": ("Arial", 11, "bold"),
            "relief": "flat",
            "borderwidth": 0,
            "fg": "white",
            "activeforeground": "white"
        }

        # ADELANTE
        self.btn_up = tk.Button(dpad_container, text="▲\nAdelante", bg=self.color_green, 
                                activebackground="#268c3b", width=14, height=4, **btn_style)
        self.btn_up.grid(row=0, column=1, pady=10)
        self.btn_up.bind("<ButtonPress-1>", lambda e: self.cmd_move("F"))
        self.btn_up.bind("<ButtonRelease-1>", lambda e: self.cmd_stop_traction())

        # IZQUIERDA
        self.btn_left = tk.Button(dpad_container, text="◀", bg=self.color_blue,
                                  activebackground="#1a5cbf", width=8, height=4, **btn_style)
        self.btn_left.grid(row=1, column=0, padx=10)
        self.btn_left.bind("<ButtonPress-1>", lambda e: self.cmd_steer("L"))
        self.btn_left.bind("<ButtonRelease-1>", lambda e: self.cmd_steer("Z"))

        # STOP
        self.btn_stop = tk.Button(dpad_container, text="STOP", bg=self.color_red,
                                  activebackground="#b02a28", width=10, height=4, **btn_style)
        self.btn_stop.grid(row=1, column=1, padx=5)
        self.btn_stop.config(command=self.cmd_emergency_stop)

        # DERECHA
        self.btn_right = tk.Button(dpad_container, text="▶", bg=self.color_blue,
                                   activebackground="#1a5cbf", width=8, height=4, **btn_style)
        self.btn_right.grid(row=1, column=2, padx=10)
        self.btn_right.bind("<ButtonPress-1>", lambda e: self.cmd_steer("R"))
        self.btn_right.bind("<ButtonRelease-1>", lambda e: self.cmd_steer("Z"))

        # ATRAS
        self.btn_down = tk.Button(dpad_container, text="▼\nAtrás", bg=self.color_yellow,
                                  activebackground="#71751f", width=14, height=4, **btn_style)
        self.btn_down.grid(row=2, column=1, pady=10)
        self.btn_down.bind("<ButtonPress-1>", lambda e: self.cmd_move("B"))
        self.btn_down.bind("<ButtonRelease-1>", lambda e: self.cmd_stop_traction())
        
        self._orig_btn_colors = {
            'up': self.btn_up.cget('bg'),
            'left': self.btn_left.cget('bg'),
            'right': self.btn_right.cget('bg'),
            'down': self.btn_down.cget('bg')
        }

        # Footer
        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(self.bottom_frame, text="Velocidad Tracción").pack(pady=(10, 0))

        self.slider = ctk.CTkSlider(self.bottom_frame, from_=0, to=100, number_of_steps=100, width=300)
        self.slider.set(50) 
        self.slider.pack(pady=5)
        
        labels_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        labels_frame.pack(fill="x", padx=40)
        self.lbl_speed_val = ctk.CTkLabel(labels_frame, text="50%", text_color="white", font=("Arial", 12, "bold"))
        self.lbl_speed_val.pack(side="top") 
        self.slider.configure(command=lambda v: self.lbl_speed_val.configure(text=f"{int(v)}%"))

        self.btn_emergencia = ctk.CTkButton(self.bottom_frame, text="PARADA DE EMERGENCIA",
                                            fg_color="transparent", border_color=self.color_red, border_width=2,
                                            text_color=self.color_red, hover_color=self.color_red,
                                            height=45, font=ctk.CTkFont(weight="bold"),
                                            command=self.cmd_emergency_stop)
        self.btn_emergencia.pack(fill="x", padx=20, pady=15)

        self.status_bar = ctk.CTkLabel(self, text="", anchor="w", padx=10, 
                                     font=ctk.CTkFont(size=11), text_color="gray")
        self.status_bar.pack(side="bottom", fill="x")

    def _set_controls_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        try:
            # Tk buttons
            for btn in (self.btn_up, self.btn_down, self.btn_left, self.btn_right, self.btn_stop):
                btn.configure(state=state)
            # CTk widgets
            try:
                self.slider.configure(state=state)
            except:
                pass
        except:
            pass

    def cmd_steer(self, action):
        if self.worker.running.is_set() and not self.emergency:
            self.worker.send_packet(action)

    def cmd_move(self, direction):
        pct = self.slider.get()
        speed = int(pct * 10)
        cmd = f"{direction}{speed}"
        if self.worker.running.is_set():
            self.worker.send_packet(cmd)

    def cmd_stop_traction(self, event=None):
        if self.worker.running.is_set():
            self.worker.send_packet("S")

    # TECLADO OPTIMIZADO PARA EVITAR LAG
    def _on_key_press(self, event):
        try:
            if self.emergency:
                return
            key = getattr(event, "keysym", "").lower()
            
            # BLOQUEO: Si la tecla ya está marcada como presionada, ignoramos el evento repetido
            if key in self.pressed_keys and self.pressed_keys[key]:
                return
            
            # Registrar que la tecla se acaba de presionar
            if key in self.pressed_keys:
                self.pressed_keys[key] = True

            if key == "w":
                self.cmd_move("F")
                self.btn_up.configure(bg=self.btn_up.cget('activebackground'), relief='sunken')
            elif key == "s":
                self.cmd_move("B")
                self.btn_down.configure(bg=self.btn_down.cget('activebackground'), relief='sunken')
            elif key == "a":
                self.cmd_steer("L")
                self.btn_left.configure(bg=self.btn_left.cget('activebackground'), relief='sunken')
            elif key == "d":
                self.cmd_steer("R")
                self.btn_right.configure(bg=self.btn_right.cget('activebackground'), relief='sunken')
        except Exception:
            pass

    def _on_key_release(self, event):
        try:
            if self.emergency:
                for k in self.pressed_keys: self.pressed_keys[k] = False
                return
            key = getattr(event, "keysym", "").lower()
            
            # LIBERAR BLOQUEO: Permitir que se vuelva a detectar la pulsación más adelante
            if key in self.pressed_keys:
                self.pressed_keys[key] = False

            if key in ("w", "s"):
                self.cmd_stop_traction()
                if key == 'w':
                    self.btn_up.configure(bg=self._orig_btn_colors['up'], relief='flat')
                else:
                    self.btn_down.configure(bg=self._orig_btn_colors['down'], relief='flat')
            elif key in ("a", "d"):
                self.cmd_steer("Z")
                if key == 'a':
                    self.btn_left.configure(bg=self._orig_btn_colors['left'], relief='flat')
                else:
                    self.btn_right.configure(bg=self._orig_btn_colors['right'], relief='flat')
        except Exception:
            pass

    def cmd_emergency_stop(self):
        # Activate emergency stop state
        self.emergency = True
        # Send immediate stop commands if connected
        try:
            if self.worker.running.is_set():
                self.worker.send_packet("S")
                self.worker.send_packet("Z")
                # stop BLE worker to prevent further commands
                self.worker.stop()
        except:
            pass
        # Disable controls
        try:
            self._set_controls_enabled(False)
        except:
            pass
        # Clear pressed keys to avoid stuck inputs
        for k in self.pressed_keys:
            self.pressed_keys[k] = False
        # Update UI to reflect emergency state
        try:
            self.lbl_status.configure(text="PARADA DE EMERGENCIA", text_color=self.color_red)
            self.status_indicator.configure(fg_color=self.color_red)
            self.status_bar.configure(text="¡PARADA DE EMERGENCIA activada!")
            # Ensure connect button shows 'Conectar' and is enabled so user can reconnect when ready
            self.btn_connect.configure(text="Conectar", fg_color=self.color_gray, state="normal")
        except:
            pass

    def toggle_connection(self):
        if self.btn_connect.cget("text") == "Conectar":
            self.on_connect()
        else:
            self.on_disconnect()

    def on_connect(self):
        self.lbl_status.configure(text="Conectando...", text_color="yellow")
        self.status_indicator.configure(fg_color=self.color_yellow)
        self.btn_connect.configure(state="disabled")
        self.worker.start()

        def wait_ready():
            if self.worker.running.is_set():
                self.lbl_status.configure(text="Conectado", text_color=self.color_green)
                self.status_indicator.configure(fg_color=self.color_green)
                self.btn_connect.configure(text="Desconectar", state="normal", fg_color=self.color_red)
                # Clear emergency state and re-enable controls
                self.emergency = False
                try:
                    self._set_controls_enabled(True)
                except:
                    pass
                self._log("¡Sistema Listo!")
            else:
                self.after(200, wait_ready)
        wait_ready()

    def on_disconnect(self):
        self.worker.stop()
        self.lbl_status.configure(text="Desconectado", text_color="gray")
        self.status_indicator.configure(fg_color=self.color_red)
        self.btn_connect.configure(text="Conectar", fg_color=self.color_gray)
        self._log("Desconectado.")

    def _log(self, msg: str):
        try:
            self.status_bar.configure(text=msg)
            print(f"[LOG] {msg}")
        except: pass

    def _poll_logs(self):
        try:
            while True:
                try:
                    msg = self.log_queue.get_nowait()
                    self._log(msg)
                except Empty: break
        except: pass
        self.after(150, self._poll_logs)