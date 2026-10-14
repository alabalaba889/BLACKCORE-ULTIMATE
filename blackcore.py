import ctypes, os, platform, shutil, subprocess, time, tkinter as tk
from tkinter import messagebox

from blackcore_core.monitor import sparkline, format_bytes
from blackcore_core.performance import NetworkRateSampler

BG, PANEL, GREEN, MUTED = "#080d0b", "#101a15", "#39ff88", "#8eb9a0"

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
      ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
      ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
      ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
      ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]

def ftv(x): return (x.dwHighDateTime << 32) + x.dwLowDateTime
def cpu_sample():
    i,k,u=FILETIME(),FILETIME(),FILETIME()
    if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(i),ctypes.byref(k),ctypes.byref(u)): return None
    return ftv(i),ftv(k),ftv(u)
def cpu_percent(a,b):
    if not a or not b: return None
    idle=b[0]-a[0]; total=b[1]-a[1]+b[2]-a[2]
    return max(0,min(100,round(100*(total-idle)/total))) if total else 0
def ram_stats():
    s=MEMORYSTATUSEX(); s.dwLength=ctypes.sizeof(s)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s)): return None
    total=s.ullTotalPhys/(1024**3)
    return s.dwMemoryLoad,total*s.dwMemoryLoad/100,total

class App:
    def __init__(self, root):
        self.root=root; root.title("BLACKCORE // LOCAL CONTROL"); root.geometry("900x680")
        root.minsize(760,580); root.configure(bg=BG); self.prev=cpu_sample(); self.effect=None
        self.cpu_history=[]; self.ram_history=[]; self.disk_history=[]; self.network_sampler=NetworkRateSampler(); self.workbench=None
        self.build(); self.log("BLACKCORE iniciado em modo local.")
        self.log("Sem conexão remota; nenhuma ação ocorre sem clique.")
        self.refresh(); root.protocol("WM_DELETE_WINDOW",self.close)
    def build(self):
        top=tk.Frame(self.root,bg=BG); top.pack(fill="x",padx=20,pady=(18,8))
        tk.Label(top,text="BLACKCORE",font=("Consolas",27,"bold"),fg=GREEN,bg=BG).pack(side="left")
        tk.Label(top,text="// WINDOWS LOCAL CONTROL • v0.1",font=("Consolas",10),fg=MUTED,bg=BG).pack(side="left",padx=12,pady=(10,0))
        tk.Label(top,text="● LOCAL / READY",font=("Consolas",10,"bold"),fg=GREEN,bg=BG).pack(side="right",pady=(10,0))
        stats=tk.Frame(self.root,bg=BG); stats.pack(fill="x",padx=20,pady=6)
        self.cpu=tk.StringVar(value="CPU: lendo..."); self.ram=tk.StringVar(value="RAM: lendo...")
        self.disk=tk.StringVar(value="DISCO: lendo..."); self.net=tk.StringVar(value="REDE: opcional")
        self.os=tk.StringVar(value=f"SISTEMA: {platform.system()} {platform.release()} • {platform.machine()}")
        self.history=tk.StringVar(value="HISTÓRICO 60s | CPU: — | RAM: — | DISCO: —")
        for v in (self.cpu,self.ram,self.disk,self.net,self.os):
            f=tk.Frame(stats,bg=PANEL,highlightbackground="#1d5034",highlightthickness=1); f.pack(fill="x",pady=3)
            tk.Label(f,textvariable=v,font=("Consolas",11),fg=GREEN,bg=PANEL,anchor="w",padx=12,pady=9).pack(fill="x")
        hf=tk.Frame(stats,bg=PANEL,highlightbackground="#1d5034",highlightthickness=1); hf.pack(fill="x",pady=3)
        tk.Label(hf,textvariable=self.history,font=("Consolas",9),fg=MUTED,bg=PANEL,anchor="w",padx=12,pady=7).pack(fill="x")
        body=tk.Frame(self.root,bg=BG); body.pack(fill="both",expand=True,padx=20,pady=8)
        left=tk.Frame(body,bg=PANEL,highlightbackground="#1d5034",highlightthickness=1); left.pack(side="left",fill="both",expand=True,padx=(0,7))
        right=tk.Frame(body,bg=PANEL,highlightbackground="#1d5034",highlightthickness=1); right.pack(side="right",fill="both",expand=True,padx=(7,0))
        tk.Label(left,text="CONTROLE LOCAL",font=("Consolas",13,"bold"),fg=GREEN,bg=PANEL).pack(anchor="w",padx=14,pady=(14,5))
        tk.Label(left,text="Ações locais, acionadas manualmente.",font=("Consolas",9),fg=MUTED,bg=PANEL).pack(anchor="w",padx=14,pady=(0,9))
        self.btn(left,"ABRIR BLOCO DE NOTAS",self.notepad); self.btn(left,"ABRIR CALCULADORA",self.calc)\n        self.btn(left,"ABRIR AI / ROBLOX WORKBENCH",self.open_workbench)
        tk.Label(left,text="Controle do mouse (coordenadas da tela):",font=("Consolas",9),fg=MUTED,bg=PANEL).pack(anchor="w",padx=14,pady=(14,4))
        coords=tk.Frame(left,bg=PANEL); coords.pack(fill="x",padx=14,pady=3)
        self.mouse_x=tk.Entry(coords,width=8,font=("Consolas",10),bg="#07100b",fg=GREEN,insertbackground=GREEN,relief="flat")
        self.mouse_x.insert(0,"500"); self.mouse_x.pack(side="left",fill="x",expand=True,padx=(0,4))
        self.mouse_y=tk.Entry(coords,width=8,font=("Consolas",10),bg="#07100b",fg=GREEN,insertbackground=GREEN,relief="flat")
        self.mouse_y.insert(0,"400"); self.mouse_y.pack(side="left",fill="x",expand=True,padx=(4,0))
        self.btn(left,"MOVER MOUSE (CONFIRMAR)",self.move_mouse)
        self.btn(left,"CLICAR NA POSIÇÃO (CONFIRMAR)",self.click_mouse,True)
        tk.Label(left,text="Texto para digitar no aplicativo ativo:",font=("Consolas",9),fg=MUTED,bg=PANEL).pack(anchor="w",padx=14,pady=(14,4))
        self.entry=tk.Entry(left,font=("Consolas",11),bg="#07100b",fg=GREEN,insertbackground=GREEN,relief="flat"); self.entry.pack(fill="x",padx=14,pady=4)
        self.btn(left,"DIGITAR TEXTO (CONFIRMAR)",self.type_text)
        tk.Label(right,text="TROLL LAB // REVERSÍVEL",font=("Consolas",13,"bold"),fg=GREEN,bg=PANEL).pack(anchor="w",padx=14,pady=(14,5))
        tk.Label(right,text="Simulações visuais. Não altera arquivos nem configurações.",font=("Consolas",9),fg=MUTED,bg=PANEL,wraplength=340,justify="left").pack(anchor="w",padx=14,pady=(0,9))
        self.btn(right,"ABRIR TERMINAL FALSO",self.fake_terminal); self.btn(right,"ALERTA DE PEGADINHA",self.fake_alert,True); self.btn(right,"PARAR / FECHAR EFEITOS",self.stop)
        tk.Label(right,text="TECLADO LOCAL • ATALHOS PERMITIDOS",font=("Consolas",9),fg=MUTED,bg=PANEL).pack(anchor="w",padx=14,pady=(12,3))
        self.key_choice=tk.StringVar(value="ENTER")
        tk.OptionMenu(right,self.key_choice,"ENTER","ESC","TAB","SPACE","CTRL+C","CTRL+V","CTRL+Z","CTRL+S","ALT+TAB").pack(fill="x",padx=14,pady=3)
        self.btn(right,"ENVIAR TECLA / ATALHO (CONFIRMAR)",self.press_key)
        lf=tk.Frame(self.root,bg=PANEL,highlightbackground="#1d5034",highlightthickness=1); lf.pack(fill="both",padx=20,pady=(4,16))
        tk.Label(lf,text="EVENT LOG",font=("Consolas",10,"bold"),fg=GREEN,bg=PANEL).pack(anchor="w",padx=12,pady=(8,2))
        self.logs=tk.Text(lf,height=5,bg="#050806",fg=MUTED,font=("Consolas",9),relief="flat",state="disabled"); self.logs.pack(fill="both",expand=True,padx=10,pady=(0,10))
    def btn(self,p,t,cmd,red=False):
        tk.Button(p,text=t,command=cmd,bg="#3a1b20" if red else "#153c28",fg="#ff9aa5" if red else GREEN,
          activebackground="#60232c" if red else "#205b3b",activeforeground="white",font=("Consolas",10,"bold"),
          relief="flat",padx=10,pady=9).pack(fill="x",padx=14,pady=4)
    def log(self,msg):
        if not hasattr(self,"logs"): return
        self.logs.configure(state="normal"); self.logs.insert("end",time.strftime("[%H:%M:%S] ")+msg+"\n")
        self.logs.see("end"); self.logs.configure(state="disabled")
    def refresh(self):
        try:
            cur=cpu_sample(); n=cpu_percent(self.prev,cur); self.prev=cur
            self.cpu.set("CPU: "+(f"{n}%" if n is not None else "indisponível"))
            r=ram_stats(); self.ram.set("RAM: "+(f"{r[0]}% usada • {r[1]:.1f}/{r[2]:.1f} GB" if r else "indisponível"))
            d=shutil.disk_usage(os.path.abspath(os.sep)); dp=round(d.used*100/d.total,1) if d.total else 0
            self.disk.set(f"DISCO: {dp}% usado • {d.used/(1024**3):.1f}/{d.total/(1024**3):.1f} GB")
            self.cpu_history.append(n); self.cpu_history=self.cpu_history[-40:]
            self.ram_history.append(r[0] if r else None); self.ram_history=self.ram_history[-40:]
            self.disk_history.append(dp); self.disk_history=self.disk_history[-40:]
            self.history.set("HISTÓRICO ~60s | CPU "+sparkline(self.cpu_history)+" | RAM "+sparkline(self.ram_history)+" | DISCO "+sparkline(self.disk_history))
            nr=self.network_sampler.sample()
            if nr["available"] and nr["sent_bytes_per_sec"] is not None:
                self.net.set("REDE: ↑ "+format_bytes(nr["sent_bytes_per_sec"])+"/s • ↓ "+format_bytes(nr["received_bytes_per_sec"])+"/s")
            elif nr["available"]:
                self.net.set("REDE: medindo velocidade…")
            else:
                self.net.set("REDE: instale psutil para medir velocidade (opcional)")
        except Exception as e: self.log("Métrica indisponível: "+str(e))
        self.root.after(1500,self.refresh)
    def notepad(self):
        try: subprocess.Popen(["notepad.exe"]); self.log("Bloco de Notas aberto.")
        except Exception as e: messagebox.showerror("BLACKCORE",str(e))
    def calc(self):
        try: subprocess.Popen(["calc.exe"]); self.log("Calculadora aberta.")
        except Exception as e: messagebox.showerror("BLACKCORE",str(e))
    def mouse_position(self):
        try:
            x, y = int(self.mouse_x.get()), int(self.mouse_y.get())
        except ValueError:
            messagebox.showerror("BLACKCORE", "Informe coordenadas X e Y como números inteiros.")
            return None
        try:
            width, height = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            if not (0 <= x < width and 0 <= y < height):
                messagebox.showerror("BLACKCORE", f"Coordenadas fora da tela atual ({width} × {height}).")
                return None
        except Exception:
            return None
        return x, y
    def move_mouse(self):
        point = self.mouse_position()
        if point is None: return
        x, y = point
        if not messagebox.askyesno("Confirmar movimento", f"Mover o cursor para X={x}, Y={y}?"):
            self.log("Movimento do mouse cancelado."); return
        try:
            if not ctypes.windll.user32.SetCursorPos(x, y):
                raise OSError("Windows não confirmou o movimento do cursor.")
            self.log(f"Cursor movido para X={x}, Y={y}.")
        except Exception as e:
            messagebox.showerror("BLACKCORE", "Não foi possível mover o cursor: " + str(e))
    def click_mouse(self):
        point = self.mouse_position()
        if point is None: return
        x, y = point
        if not messagebox.askyesno("Confirmar clique", f"AVISO: clicar com o botão esquerdo em X={x}, Y={y}. Confirma?"):
            self.log("Clique do mouse cancelado."); return
        try:
            user32 = ctypes.windll.user32
            if not user32.SetCursorPos(x, y):
                raise OSError("Não foi possível posicionar o cursor.")
            time.sleep(0.15)
            user32.mouse_event(0x0002, 0, 0, 0, 0)
            user32.mouse_event(0x0004, 0, 0, 0, 0)
            self.log(f"Clique esquerdo executado em X={x}, Y={y}.")
        except Exception as e:
            messagebox.showerror("BLACKCORE", "Não foi possível clicar: " + str(e))
    def press_key(self):
        key = self.key_choice.get()
        allowed = {
            "ENTER": [0x0D], "ESC": [0x1B], "TAB": [0x09], "SPACE": [0x20],
            "CTRL+C": [0x11, 0x43], "CTRL+V": [0x11, 0x56],
            "CTRL+Z": [0x11, 0x5A], "CTRL+S": [0x11, 0x53],
            "ALT+TAB": [0x12, 0x09],
        }
        codes = allowed.get(key)
        if not codes:
            messagebox.showerror("BLACKCORE", "Tecla não permitida.")
            return
        if not messagebox.askyesno("Confirmar teclado", f"Enviar {key} para a janela atualmente ativa?\\nConfirme que o destino está correto."):
            self.log(f"Atalho {key} cancelado.")
            return
        try:
            u = ctypes.windll.user32
            modifier = codes[0] if len(codes) == 2 else None
            target = codes[-1]
            if modifier is not None: u.keybd_event(modifier, 0, 0, 0)
            u.keybd_event(target, 0, 0, 0)
            u.keybd_event(target, 0, 0x0002, 0)
            if modifier is not None: u.keybd_event(modifier, 0, 0x0002, 0)
            self.log(f"Tecla/atalho {key} enviado com confirmação.")
        except Exception as e:
            messagebox.showerror("BLACKCORE", "Não foi possível enviar a tecla: " + str(e))

    def type_text(self):
        s=self.entry.get()
        if not s: messagebox.showinfo("BLACKCORE","Escreve o texto primeiro."); return
        if not messagebox.askyesno("Confirmar","Após confirmar, terás 3 segundos para selecionar o campo de destino. Digitar apenas o texto deste campo. Continuar?"): return
        self.log("Digitação autorizada; tens 3 segundos para selecionar o campo.")
        self.root.iconify(); self.root.after(3000,lambda:self.send_text(s))
    def send_text(self,s):
        try:
            u=ctypes.windll.user32; up,uni=0x0002,0x0004
            for ch in s:
                u.keybd_event(0,ord(ch),uni,0); u.keybd_event(0,ord(ch),uni|up,0); time.sleep(.008)
            self.root.deiconify(); self.root.lift(); self.log("Texto enviado; nenhuma tecla foi gravada.")
        except Exception as e:
            self.root.deiconify(); messagebox.showerror("BLACKCORE","Falha ao digitar: "+str(e))
    def fake_terminal(self):
        if self.effect and self.effect.winfo_exists(): self.effect.lift(); return
        w=tk.Toplevel(self.root); self.effect=w; w.title("SYSTEM DIAGNOSTICS // DEMO"); w.geometry("620x340"); w.configure(bg="#020604")
        w.protocol("WM_DELETE_WINDOW",self.stop)
        tk.Label(w,text="BLACKCORE // SIMULAÇÃO VISUAL",font=("Consolas",13,"bold"),fg=GREEN,bg="#020604").pack(anchor="w",padx=14,pady=12)
        t=tk.Text(w,bg="#020604",fg=GREEN,font=("Consolas",10),relief="flat"); t.pack(fill="both",expand=True,padx=12,pady=(0,12))
        for line in ["[DEMO] Inicializando interface visual...","[DEMO] Verificando módulos locais...","[DEMO] Nenhum arquivo está sendo alterado.","[DEMO] Nenhum acesso remoto está ativo.","[DEMO] Isto é apenas uma brincadeira."]: t.insert("end",line+"\n")
        t.configure(state="disabled"); self.log("Terminal falso aberto.")
    def fake_alert(self):
        messagebox.showinfo("Pegadinha do BLACKCORE","PEGADINHA! Só uma brincadeira.\nNenhuma falha foi detectada e nada foi alterado.")
        self.log("Alerta de brincadeira exibido.")
    def stop(self):
        try:
            if self.effect and self.effect.winfo_exists(): self.effect.destroy()
        except Exception: pass
        self.effect=None; self.log("Efeitos visuais encerrados.")
    def close(self): self.stop(); self.root.destroy()

if __name__=="__main__":
    if os.name!="nt": raise SystemExit("BLACKCORE foi feito para Windows.")
    root=tk.Tk(); App(root); root.mainloop()
