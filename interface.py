import threading
import functions #crawler functions
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Moodle Bot")
        self.geometry("300x200")
        self.resizable(False, False)
        self.create_login_ui()

    def create_login_ui(self):
        # Limpa qualquer layout anterior
        for widget in self.winfo_children():
            widget.destroy()

        # Campos de login
        tk.Label(self, text="Usuário:", anchor="e", width=12).grid(row=0, column=0, padx=10, pady=10)
        self.user_entry = tk.Entry(self, width=25)
        self.user_entry.grid(row=0, column=1, padx=10, pady=10)

        tk.Label(self, text="Senha:", anchor="e", width=12).grid(row=1, column=0, padx=10, pady=10)
        self.pass_entry = tk.Entry(self, width=25, show="*")
        self.pass_entry.grid(row=1, column=1, padx=10, pady=10)

        login_btn = tk.Button(self, text="Login", width=20, command=self.handle_login)
        login_btn.grid(row=2, column=0, columnspan=2, pady=15)

    def handle_login(self):
        user = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()

        if not user or not password:
            messagebox.showwarning("Aviso", "Por favor, preencha usuário e senha.")
            return

        # Desabilita campos durante a autenticação
        self.user_entry.config(state='disabled')
        self.pass_entry.config(state='disabled')

        # Inicia login em thread separada
        threading.Thread(target=self.run_login, args=(user, password), daemon=True).start()

    def run_login(self, user, password):
        self.after(0, self.show_logged_screen)  # altera layout principal
        df = functions.login_moodle(user, password)  # tenta pegar o dataframe
        if df is not None:
            self.after(0, lambda: self.show_results_screen(df))  # exibe na interface
        elif df is None:
            self.after(0, lambda: messagebox.showerror("Erro", f"Falha nas credenciais:\n"))
            self.after(0, self.create_login_ui) #reinicia interface

    def show_logged_screen(self):
        #Limpa
        for widget in self.winfo_children():
            widget.destroy()

        self.title("Conectado ao Moodle")

        tk.Label(self, text="Login realizado com sucesso!", font=("Arial", 14)).pack(pady=20)

        tk.Label(
            self,
            text="Aguarde o fim da varredura para que esta página atualize automaticamente",
            font=("Arial", 10),
            wraplength=250,  # quebra de linha automática
            justify="center"  # centraliza o texto
        ).pack(pady=20)

    def show_results_screen(self, df):
        for widget in self.winfo_children():
            widget.destroy()

        self.title("Tarefas Pendentes")

        altura_px = min(700, max(300, len(df) * 25))
        largura_px = 1000
        self.geometry(f"{largura_px}x{altura_px}")

        frame = tk.Frame(self)
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        #orientation
        vsb = tk.Scrollbar(frame, orient="vertical")
        hsb = tk.Scrollbar(frame, orient="horizontal")

        tree = ttk.Treeview(
            frame,
            columns=list(df.columns), #headers are the columns of the df
            show='headings',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        vsb.config(command=tree.yview)
        vsb.pack(side='right', fill='y')
        hsb.config(command=tree.xview)
        hsb.pack(side='bottom', fill='x')
        tree.pack(fill='both', expand=True)

        #headers size
        for col in df.columns:
            tree.heading(col, text=col)
            max_width = max(df[col].astype(str).apply(len).max(), len(col)) * 7
            tree.column(col, width=min(max_width, 400), anchor='w')

        #styling tags to the table lines
        tree.tag_configure('atrasado', background='#f8d7da')  #red
        tree.tag_configure('pendente', background='#fff3cd')  #yellow
        tree.tag_configure('enviado', background='#d4edda')  #green

        #insert lines
        for _, row in df.iterrows():
            status = str(row['Status']).lower()

            if 'nenhum envio' in status or 'não enviado' in status:
                tag = 'pendente'
            elif 'enviado' in status:
                tag = 'enviado'
            else: #if It would get before activities (all time published ones)
                tag = 'atrasado'

            tree.insert('', 'end', values=list(row), tags=(tag,))

if __name__ == '__main__':
    app = App()
    app.mainloop()