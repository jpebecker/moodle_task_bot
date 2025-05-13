import tkinter as tk
from tkinter import messagebox
import threading
import functions #crawler functions

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
        try:
            self.after(0, self.show_logged_screen)  # altera layout principal
            df = functions.login_moodle(user, password)  # recebe o dataframe
            self.after(0, lambda: self.show_results_screen(df))  # exibe na interface
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erro", f"Falha no login:\n{e}"))
            self.after(0, self.create_login_ui)

    def show_logged_screen(self):
        #Limpa
        for widget in self.winfo_children():
            widget.destroy()

        self.title("Conectado")

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

        #dataframe to a string
        df_str = df.to_string(index=False)
        linhas = df_str.split('\n')
        num_linhas = len(linhas)
        largura_max = max(len(linha) for linha in linhas)

        #proporcional size
        largura_px = min(1000, max(300, largura_max * 8))
        altura_px = min(700, max(200, num_linhas * 20))
        self.geometry(f"{largura_px}x{altura_px}")

        frame = tk.Frame(self)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side='right', fill='y')

        text_widget = tk.Text(
            frame, wrap='none', yscrollcommand=scrollbar.set, font=("Courier", 9,'bold')
        )
        text_widget.pack(fill='both', expand=True)
        scrollbar.config(command=text_widget.yview)

        text_widget.insert(tk.END, df_str)
        text_widget.config(state='disabled')

if __name__ == '__main__':
    app = App()
    app.mainloop()