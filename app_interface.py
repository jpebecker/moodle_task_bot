import app_functions as functions  # crawler functions
import threading
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from datetime import datetime
from tkinter import messagebox
from selenium import webdriver
from cryptography.fernet import Fernet
from selenium.webdriver.chrome.options import Options
########################################################Credentials Section
#credentials path
CREDENTIALS_DIR = Path.home() / "Documents" / "Moodle_Credentials"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.txt"
KEY_FILE = CREDENTIALS_DIR / "key.key"

#check if directory path exist
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

#read or write credential
if KEY_FILE.exists():
    with open(KEY_FILE, 'rb') as f:
        key = f.read()
else:
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as f:
        f.write(key)

fernet = Fernet(key)
########################################################App interface Class
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Moodle Activity Bot")
        self.geometry("300x250")
        self.resizable(False, False)
        self.user_entry = None
        self.pass_entry = None
        self.Main_Title = None
        self.Description = None
        self.save_credentials_var = None
        self.all_time_var = None
        self.show_browser_var = None
        self.main_browser = None
        self.table = None
        self.all_activities = []
        self.clear_btn = None  #botao de limpar credenciais (se for usado)
        self.create_ui()

    def create_ui(self):
        """
        Show all the initial ui elements to the Login Process
        """
        for widget in self.winfo_children():
            widget.destroy()

        tk.Label(self, text="Usuário:", anchor="e", width=12).grid(row=0, column=0, padx=10, pady=10)
        self.user_entry = tk.Entry(self, width=25)
        self.user_entry.grid(row=0, column=1, padx=10, pady=10)

        tk.Label(self, text="Senha:", anchor="e", width=12).grid(row=1, column=0, padx=10, pady=10)
        self.pass_entry = tk.Entry(self, width=25, show="*")
        self.pass_entry.grid(row=1, column=1, padx=10, pady=10)

        self.save_credentials_var = tk.BooleanVar()
        save_checkbox = tk.Checkbutton(self, text="Salvar credenciais", variable=self.save_credentials_var)
        save_checkbox.grid(row=2, column=0, columnspan=2)

        self.all_time_var = tk.BooleanVar()
        all_time_checkbox = tk.Checkbutton(self, text="Todas as Tarefas com prazo", variable=self.all_time_var)
        all_time_checkbox.grid(row=3, column=0, columnspan=2)

        login_btn = tk.Button(self, text="Login", width=20, command=self.check_login)
        login_btn.grid(row=4, column=0, columnspan=2, pady=10)

        self.show_browser_var = tk.BooleanVar()
        show_browser_checkbox = tk.Checkbutton(self, text="Mostrar execução?", variable=self.show_browser_var)
        show_browser_checkbox.grid(row=6, column=0, columnspan=2)

        self.clear_btn = None  # Inicializa sem o botão
        self.load_credentials()

    def check_login(self):
        """
        Get exceptions related to the login after the LOGIN btn is pressed
        """
        user = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()

        if not user or not password:
            messagebox.showwarning("Aviso", "Por favor, preencha usuário e senha.")
            return

        self.user_entry.config(state='disabled')
        self.pass_entry.config(state='disabled')

        if self.save_credentials_var.get():
            try:
                encrypted_password = fernet.encrypt(password.encode())
                cred_was_saved = not CREDENTIALS_FILE.exists()  #se o arquivo já existia

                with open(CREDENTIALS_FILE, 'w') as f:
                    f.write(user + '\n')
                    f.write(encrypted_password.decode())

                if cred_was_saved:
                    messagebox.showinfo("Credenciais salvas", f"Credenciais salvas com sucesso em:\n{CREDENTIALS_FILE}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar credenciais: {e}")

        threading.Thread(target=self.run_login, args=(user, password)).start()

    def run_login(self, user, password):
        """
        Switch the UI and start the web scrapping Login Function and waits for the status result, if successful it will
        get back the dataframe of results and call the show results function
        """
        self.after(0, self.show_logged_screen)
        self.main_browser = create_browser(self.show_browser_var.get())
        result = functions.login_moodle(active_browser=self.main_browser,user=user,secret=password)

        if result["status"] == "success":
            subjects_list = result["data"]
            print(f'DISCIPLINAS COLETADAS:\n{subjects_list}')
            threading.Thread(target=self.loop_subject, args=(subjects_list,), daemon=True).start()
        elif result["status"] == "multiple_ids":
            users_ids = []
            links_ids = []
            for user in result["data"]:
                users_ids.append(user[0])
                links_ids.append(user[1])

            self.after(0, lambda: self.show_curriculum_opt(users_ids, links_ids))

        else:  #if status == error
            self.after(0, lambda: messagebox.showerror("Erro", f"Falha nas credenciais\n"))
            self.after(0, self.create_ui)

    def load_credentials(self):
        """
        Insert saved credentials at their entries
        """
        try:
            if CREDENTIALS_FILE.exists():
                with open(CREDENTIALS_FILE, 'r') as f:
                    user = f.readline().strip()
                    encrypted_password = f.readline().strip().encode()
                    password = fernet.decrypt(encrypted_password).decode()

                    self.user_entry.insert(0, user)
                    self.pass_entry.insert(0, password)
                    self.save_credentials_var.set(True)

                #botao de limpar credenciais
                self.clear_btn = tk.Button(self, text="Limpar credenciais salvas", command=self.clear_credentials)
                self.clear_btn.grid(row=5, column=0, columnspan=2)
            else:
                print('Não tem credenciais salvas')
        except Exception as exc:
            pass

    def clear_credentials(self):
        """
        Erase the credential from the local repository and erase the inserted ones at their entries
        """
        try:
            if CREDENTIALS_FILE.exists():
                CREDENTIALS_FILE.unlink()
            if KEY_FILE.exists():
                KEY_FILE.unlink()
            messagebox.showinfo(
                "Credenciais removidas",
                f"Credenciais apagadas com sucesso de:\n{CREDENTIALS_FILE}"
            )
            self.user_entry.delete(0, tk.END)
            self.pass_entry.delete(0, tk.END)
            self.save_credentials_var.set(False)

            if self.clear_btn:
                self.clear_btn.destroy()
                self.clear_btn = None
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível apagar as credenciais: {e}")

    def show_logged_screen(self):
        """
        Change the screen of the app to an In Progress one
        """
        for widget in self.winfo_children():
            widget.destroy()

        self.title("Conectado ao Moodle")
        self.Main_Title = tk.Label(self, text="Login realizado com sucesso!", font=("Arial", 14))
        self.Main_Title.pack(pady=20)

        self.Description =tk.Label(
            self,
            text="Aguarde o fim da varredura para que esta página atualize automaticamente",
            font=("Arial", 10),
            wraplength=250,
            justify="center"
        )
        self.Description.pack(pady=20)
        self.table = ttk.Treeview(self, columns=("Disciplina", "Tarefa", "Prazo", "Status"), show="headings")
        for col in ("Disciplina", "Tarefa", "Prazo", "Status"):
            self.table.heading(col, text=col)
            self.table.column(col, anchor="center")
        self.table.pack(fill=tk.BOTH, expand=True)
        self.table.tag_configure("pendente", background="#FFF5CC")
        self.table.tag_configure("enviado", background="#CCFFCC")
        self.table.tag_configure("atrasado", background="#FFCCCC")
        self.geometry("900x500")

    def show_curriculum_opt(self, user_ids: list, links: list):
        """
        Show a new window if the different curriculum numbers showed as buttons and wait for the user click
        """
        window = tk.Toplevel(self)
        window.title("Selecione a matrícula")

        tk.Label(window, text="Escolha o número de matrícula para continuar:").pack(pady=10)

        for uid, link in zip(user_ids, links):
            tk.Button(
                window,
                text=uid,
                command=lambda l=link: self.select_identity(l, window)
            ).pack(pady=5)

    def select_identity(self, user_link, window):
        """
        Delete the curriculum option window and calls another function to properly set the address of the user selected
        """
        window.destroy()
        threading.Thread(target=self._run_select_identity, args=(user_link,), daemon=True).start()

    def _run_select_identity(self, user_page):
        """
        Send to the Function script the user_url and awaits for the result to be shown like the run_login method
        """
        try:
            functions.select_curriculum_number(active_browser=self.main_browser,user_id_page=user_page)
            subjects = functions.get_subjects(self.main_browser)
            threading.Thread(target=self.loop_subject, args=(subjects,), daemon=True).start()
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erro", f"Erro ao selecionar identidade: {e}"))
            self.after(0, self.create_ui)

    def show_result(self,activity:dict):
        print('===========================ATIVIDADE NOVA REGISTRADA=====================================')
        print(activity)
        self.title("Atividades Retornadas")
        self.all_activities.append(activity)
        self.atualizar_tabela()

    def atualizar_tabela(self):
        if self.table.get_children():
            for item in self.table.get_children():
                self.table.delete(item)
        # Ordena por data de 'Prazo' (do mais próximo ao mais distante)
        atividades_ordenadas = sorted(
            self.all_activities,
            key=lambda x: datetime.strptime(x['Prazo'], "%d/%m/%Y")
        )

        for atividade in atividades_ordenadas:
            status = atividade["Status"].lower()
            prazo = datetime.strptime(atividade["Prazo"], "%d/%m/%Y")

            if 'nenhum envio' in status or 'não enviado' in status:
                if prazo < datetime.today():
                    tag = 'atrasado'
                else:
                    tag = 'pendente'

            elif 'enviado com atraso' in status:
                tag = 'atrasado'

            elif 'enviado' in status:
                tag = 'enviado'
            else:
                tag = 'atrasado'

            self.table.insert("", "end", values=(
                atividade["Disciplina"], atividade["Tarefa"], atividade["Prazo"], atividade["Status"]
            ), tags=(tag,))

    def loop_subject(self,subjects_list):
        for subject in subjects_list:
            subject_name = subject[0]
            subject_url = subject[1]
            print(f'>>> Percorrendo: {subject_name}')
            subject_activities = functions.get_activities(active_browser=self.main_browser, subject_url=subject_url,
                                                          all_time=self.all_time_var.get())
            for activity in subject_activities:
                activity_name = activity[0]
                activity_url = activity[1]
                activity_due_date = activity[2]
                activity_status = functions.get_activities_status(active_browser=self.main_browser,
                                                                  activity_url=activity_url)
                task = {
                    'Disciplina': subject_name,
                    'Tarefa': activity_name,
                    'Prazo': activity_due_date.strftime("%d/%m/%Y"),
                    'Status': activity_status,
                }
                self.after(0, lambda t=task: self.show_result(t))

        self.after(0, lambda : self.ended_ui())

    def ended_ui(self):
        self.title("Resultados Exibidos")
        print('end')
def create_browser(show_browser=False):
    # browser options
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")
    if not show_browser:
        options.add_argument("--headless")

    browser = webdriver.Chrome(options=options)
    return browser
##########################--------------------------------------Main loop
if __name__ == '__main__':
    app = App()
    app.mainloop()