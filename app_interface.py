import web_functions as functions  # crawler functions
import sys,os
import threading
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from datetime import datetime
from tkinter import messagebox
from selenium import webdriver
from cryptography.fernet import Fernet
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
########################################################Credentials Section
CREDENTIALS_DIR = Path.home() / "Documents" / "Moodle_Credentials" #credentials path
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
        self.resizable(False, False)
        self.user_entry = None #entry for username value
        self.username = None #username variable
        self.pass_entry = None #entry for password value
        self.Main_Title = None #title text
        self.Description = None #below title text
        self.save_credentials_var = None #save login credentials boolean variable
        self.all_time_var = None #show all activities boolean variable
        self.show_browser_var = None #show execution boolean variable
        self.main_browser = None #virtual browser
        self.table = None #results table
        self.all_activities = [] #activities list
        self.clear_btn = None  #clear credentials btn
        self.notes_text = None
        icon_path = get_icon_path("assets/icone.ico") #find the icon to use as tkinter interface icon
        self.iconbitmap(icon_path) #set the attribute icon
        self.create_main_ui()

    def create_main_ui(self):
        """
        Show all the necessary UI elements in Main Page
        """
        for widget in self.winfo_children():
            widget.destroy()

        #window and grid config
        self.title("Moodle Activity Bot")
        self.geometry("300x275")
        self.grid_rowconfigure(8, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

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
        all_time_checkbox = tk.Checkbutton(self, text="Mostrar Tarefas Vencidas", variable=self.all_time_var)
        all_time_checkbox.grid(row=3, column=0, columnspan=2)

        login_btn = tk.Button(self, text="Login", width=20, command=self.check_login)
        login_btn.grid(row=4, column=0, columnspan=2, pady=10)

        self.show_browser_var = tk.BooleanVar()
        show_browser_checkbox = tk.Checkbutton(self, text="Mostrar execução", variable=self.show_browser_var)
        show_browser_checkbox.grid(row=6, column=0, columnspan=2)

        faq_btn = tk.Button(self, text="?", width=5, command=self.show_faq_screen)
        faq_btn.grid(row=8, column=1, sticky="se")

        footer = tk.Label(self, text=f"©{datetime.today().year} JpeBecker. Todos os direitos reservados.",
                          font=("Arial", 9,"bold"), bd=1, relief=tk.SUNKEN, anchor="center")
        footer.grid(row=9, column=0, columnspan=2, sticky="we", pady=(10, 0))

        self.clear_btn = None
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
        self.username = user
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
        start to search for results and call the show results function
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

        else:
            print(result["status"])#if status == error
            self.after(0, lambda: messagebox.showerror("Erro", f"Falha nas credenciais\n"))
            self.after(0, self.create_main_ui)
            self.after(self.main_browser.close())

    def get_notes_file_path(self):
        """
        Get the local path where the user notes were saved
        """
        NOTES_DIR = Path.home() / "Documents" / "Moodle_notes"
        NOTES_DIR.mkdir(exist_ok=True)
        return NOTES_DIR / f"{self.username}_notes.txt"

    def save_notes(self):
        """
        Save the notes written in local repository
        """
        try:
            with open(self.get_notes_file_path(), "w", encoding="utf-8") as f:
                f.write(self.notes_text.get("1.0", tk.END).strip())
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar anotações: {e}")

    def load_notes(self):
        """
        Get the user notes saved at local repository
        """
        try:
            notes_file = self.get_notes_file_path()
            if notes_file.exists():
                with open(notes_file, "r", encoding="utf-8") as f:
                    self.notes_text.insert("1.0", f.read())
        except Exception as e:
            print(f"Erro ao carregar anotações: {e}")

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
        except Exception:
            print('no credentials')
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
        Change the Main screen of the app to a 'Search In Progress' one and initialize the results table
        """

        for widget in self.winfo_children():
            widget.destroy()#clear all UI elements before

        self.title("Conectado ao Moodle")
        self.geometry("900x500")

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)

        #Activities section
        activities_frame = tk.Frame(notebook)
        self.Main_Title = tk.Label(activities_frame, text="Login realizado com sucesso!", font=("Arial", 14))
        self.Main_Title.pack(pady=10)

        self.Description = tk.Label(
            activities_frame,
            text="Aguarde o fim da varredura para que esta página atualize automaticamente",
            font=("Arial", 10),
            wraplength=250,
            justify="center"
        )
        self.Description.pack(pady=10)

        self.table = ttk.Treeview(activities_frame, columns=("Disciplina", "Tarefa", "Prazo", "Status"),
                                  show="headings")
        for col in ("Disciplina", "Tarefa", "Prazo", "Status"):
            self.table.heading(col, text=col)
            self.table.column(col, anchor="center")
        self.table.pack(fill=tk.BOTH, expand=True)

        self.table.tag_configure("pendente", background="#FFF5CC")
        self.table.tag_configure("enviado", background="#CCFFCC")
        self.table.tag_configure("atrasado", background="#FFCCCC")

        footer = tk.Label(self, text=f"©{datetime.today().year} JpeBecker. Todos os direitos reservados.",
                          font=("Arial", 9, "bold"), bd=1, relief=tk.SUNKEN, anchor="center")
        footer.pack(side=tk.BOTTOM, fill=tk.X)

        ######NOTES section
        notes_frame = tk.Frame(notebook)
        tk.Label(notes_frame, text="Anotações Pessoais", font=("Arial", 12)).pack(pady=5)

        self.notes_text = tk.Text(notes_frame, wrap="word", height=20)
        self.notes_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        #load notes to the label
        self.load_notes()

        save_btn = tk.Button(notes_frame, text="Salvar Anotações", command=self.save_notes)
        save_btn.pack(pady=5)

        #add both sections/frames to the Notebook
        notebook.add(activities_frame, text="Atividades")
        notebook.add(notes_frame, text="Anotações")

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
            self.after(0, self.create_main_ui)

    def update_results(self, activity:dict):
        print('\n===========================ATIVIDADE NOVA REGISTRADA=====================================')
        print(activity)
        self.title("Atividades Retornadas")
        self.all_activities.append(activity)
        self.update_table()

    def update_table(self):
        """
        Update activities table with new results
        """
        if self.table.get_children():
            for item in self.table.get_children():
                self.table.delete(item)
        #order by date
        atividades_ordenadas = sorted(
            self.all_activities,
            key=lambda x: datetime.strptime(x['Prazo'], "%d/%m/%Y"))

        for atividade in atividades_ordenadas:
            status = atividade["Status"].lower()
            prazo = datetime.strptime(atividade["Prazo"], "%d/%m/%Y")

            if 'nenhum envio' in status or 'não enviado' in status: #changing the row color by their status
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
        """
        Loop through the subject page getting their activities and calling the update table function
        after returning the result dict
        """

        for subject in subjects_list:
            subject_name = subject[0]
            subject_url = subject[1]
            print(f'>>> Percorrendo: {subject_name}')
            subject_activities = functions.get_activities(active_browser=self.main_browser, subject_url=subject_url)
            if subject_activities is not None:
                print(f'{subject_name} has content blocks')
                selected_activities = functions.loop_activities(activities_list=subject_activities,all_time=self.all_time_var.get())
                for activity in selected_activities:
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
                    self.after(0, lambda t=task: self.update_results(t)) #mutable value to keep posting new activities

            else:
                print(f'{subject_name} has NONE content blocks')
                continue
        self.after(0, lambda : self.has_ended_ui())

    def has_ended_ui(self):
        """
        Update current page to match the end of execution
        """
        self.title("Todos os Resultados Exibidos")
        self.main_browser.quit()
        if self.Main_Title:
            self.Main_Title.config(text="Varredura finalizada!")
            self.Main_Title.config(fg="green", font=("Arial", 14, "bold"))
        if self.Description:
            self.Description.config(
                text="Todos os resultados foram exibidos.\n"
                     "Você pode revisar a tabela abaixo."
            )
        print('end')

    def show_faq_screen(self):
        """
        show a faq screen in the UI
        """
        #limpa a tela
        for widget in self.winfo_children():
            widget.destroy()

        self.title("Sobre a Interface - (FAQ)")
        self.geometry("400x400")

        #Grid configs
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(5, weight=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        faq_title = tk.Label(self, text="Perguntas Frequentes", font=("Arial", 14))
        faq_title.grid(row=0, column=0, columnspan=3, pady=10)

        faq_text = (
            "1. Onde são salvas as credenciais?\n"
            "   - Ao marcar a caixa 'Salvar credenciais' antes de fazer login, as suas credenciais do moodle serão salvas na pasta Documentos de seu computador.\n\n"
            "2. O que significa 'Mostrar Tarefas Vencidas'?\n"
            "   - Inclui na varredura também as atividades com prazos de vencimento antes da data atual.\n\n"
            "3. O que 'Mostrar execução' faz?\n"
            "   - Exibe o navegador durante o processo de coleta de dados.\n\n"
            "4. Como apago minhas credenciais salvas?\n"
            "   - Use o botão 'Limpar credenciais salvas' na tela de login.\n\n"
            "OBS: A coleta deste aplicativo está sujeita a erros e não substitui o uso de seu moodle pessoal"
        )
        faq_label = tk.Label(self, text=faq_text, justify="left", wraplength=350, anchor="w")
        faq_label.grid(row=1, column=0, columnspan=3, padx=20, sticky="nw")

        spacer = tk.Label(self, text="")
        spacer.grid(row=2, column=0)

        back_btn = tk.Button(self, text="Voltar", command=self.create_main_ui)
        back_btn.grid(row=3, column=2, pady=10, padx=10, sticky="e")

        process_btn = tk.Button(self, text="Sobre o BOT", command=self.show_bot_info)
        process_btn.grid(row=3, column=0, pady=10, padx=10, sticky="w")

        footer = tk.Label(
            self,
            text=f"©{datetime.today().year} JpeBecker. Todos os direitos reservados.",
            font=("Arial", 9, "bold"),
            bd=1,
            relief=tk.SUNKEN,
            anchor="center"
        )
        footer.grid(row=5, column=0, columnspan=3, sticky="we", pady=(10, 0))

    def show_bot_info(self):
        """
        show BOT info screen
        """
        for widget in self.winfo_children():
            widget.destroy()

        self.title("Sobre o BOT - (FAQ)")
        self.geometry("600x500")
        #grid configs
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(5, weight=1)  # linha inferior para manter rodapé no fundo
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        #title
        page_title = tk.Label(self, text="Sobre o Processo de Varredura ", font=("Arial", 14))
        page_title.grid(row=0, column=0, columnspan=3, pady=10)

        #answer to questions
        page_text = (
            "1. Inicialmente o bot faz login em sua conta do moodle.\n\n"
            "2. Após entrar na interface da plataforma, ele captura as URLs das disciplinas do semestre mais recente.\n\n"
            "3. Após coletar as disciplinas, percorre cada uma capturando os elementos de atividade (blocos de atividade)\n\n"
            "4. Então, faz a verificação conforme a data da descrição da atividade (palavra chave: 'Vencimento')\n\n"
            "5. Se a verificação der positiva, acessa a URL da atividade para capturar o status de entrega.\n\n"
            "6. Retorna todas as informações (Disciplina-Título da Tarefa-Prazo-Status de envio) para a tabela e passa para a próxima tarefa.\n\n"
            "7. Ao finalizar todas as tarefas da disciplina, passa para a próxima disciplina e repete o processo.\n\n"
            "8. Ao percorrer todas as disciplinas, fecha o navegador e atualiza a interface.\n\n"
            "OBS: A varredura feita por este aplicativo esta sujeita a erros e não substitui o uso de seu moodle pessoal"
        )

        page_label = tk.Label(self, text=page_text, justify="left", wraplength=500, anchor="w")
        page_label.grid(row=1, column=0, columnspan=3, padx=20, sticky="nw")

        #back to faq ui
        back_btn = tk.Button(self, text="Voltar", command=self.show_faq_screen)
        back_btn.grid(row=3, column=2, pady=10, padx=10, sticky="e")

        footer = tk.Label(self, text=f"©{datetime.today().year} JpeBecker. Todos os direitos reservados.",
                          font=("Arial", 9,"bold"), bd=1, relief=tk.SUNKEN, anchor="center")
        footer.grid(row=5, column=0, columnspan=3, sticky="we", pady=(10, 0))

##########################External functions
def create_browser(show_browser=False):
    """
    Instantiate custom virtual browser to be used in all the execution
    (only one virtual browser is used to keep the authentication)
    """
    # browser options
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")
    if not show_browser:
        options.add_argument("--headless")

    # Use webdriver-manager to install and manage the ChromeDriver
    service = Service(ChromeDriverManager().install())
    browser = webdriver.Chrome(service=service, options=options)

    return browser

def get_icon_path(relative_path):
    """find the icon after build"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)