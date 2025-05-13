import re
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as ExpC

#browser options
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-dev-shm-usage")

browser = webdriver.Chrome(options=options)
disciplinas = []
tarefas_pendentes = []

def parse_text(text: str) -> list:
    """
    Recebe um texto poluido com a palavra-chave 'Vencimento'
    e retorna um datetime
    """

    #get all ocurrances after 'Vencimento:' by a regex
    matches = re.findall(r'Vencimento:\s*([a-zçãé\-]+),\s*(\d{1,2})\s*([a-zç]+)\.\s*(\d{4}),\s*(\d{2}:\d{2})', text,
                         re.IGNORECASE)

    meses = {
        "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
        "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12
    }

    for _, dia, mes_abrev, ano, hora in matches:
        mes_num = meses.get(mes_abrev.lower()[:3])
        if mes_num:
            data_str = f"{dia.zfill(2)}/{mes_num:02}/{ano} {hora}"
            data_obj = datetime.strptime(data_str, "%d/%m/%Y %H:%M")

    return data_obj

def pending_tasks():
    # GET SUBJECTS URLs
    WebDriverWait(browser, 10).until(ExpC.presence_of_all_elements_located((By.CSS_SELECTOR, ".box.py-3.generalbox")))
    semestres_box = browser.find_elements(By.CSS_SELECTOR, ".box.py-3.generalbox")
    ul_semestre_atual = semestres_box[0].find_element(By.CSS_SELECTOR, 'ul')  # get latest semester
    disciplinas_semestre_atual = ul_semestre_atual.find_elements(By.CSS_SELECTOR, 'li')

    for subject in disciplinas_semestre_atual:
        link_elem = subject.find_element(By.TAG_NAME, 'a')
        nome = link_elem.text
        url = link_elem.get_attribute('href')
        # print(nome, url)
        disciplinas.append((nome, url))

    for d in disciplinas:
        browser.get(d[1])  # get into the subject page
        WebDriverWait(browser, 10).until(ExpC.presence_of_all_elements_located((By.CLASS_NAME, "activity-item")))
        atividades = browser.find_elements(By.CLASS_NAME, "activity-item")  # get all activities DIVs
        for atividade in atividades:
            try:
                # getting the title (usando o atributo data-activityname)
                activity_name = atividade.get_attribute("data-activityname")
                # print("Nome da Atividade:", activity_name)

                # searching description
                descricao_div = atividade.find_element(By.CLASS_NAME, "description")
                descricao_interna = descricao_div.find_element(By.CLASS_NAME, "description-inner")
                descricao_texto = descricao_interna.text
                # print("Descrição da Atividade:", descricao_texto)

                if activity_name and descricao_texto:
                    if 'Vencimento:' in descricao_texto:
                        date_formatted = parse_text(descricao_texto)
                        if date_formatted > datetime.now():
                            task = {
                                'Disciplina': d[0],  # name,
                                'Tarefa': activity_name,
                                'Prazo': date_formatted.strftime("%d/%m/%Y")
                            }
                            tarefas_pendentes.append(task)
                            # print(f"Nome da Atividade: {activity_name}\n Vencimento da Atividade: {date_formatted}")
            except Exception as Exc:
                pass  # ignored values

        browser.back()  # go back to main page of subjects

    tarefas_ordenadas = sorted(tarefas_pendentes,
                               key=lambda tarefa: datetime.strptime(tarefa["Prazo"], "%d/%m/%Y"))

    df = pd.DataFrame(tarefas_ordenadas)
    pd.set_option('display.max_columns', None)  # all columns showed guaranteeed
    pd.set_option('display.width', 0)  # limited width
    pd.set_option('display.max_colwidth', None)  # all contents are showed
    print(df)
    return df

def login_moodle(user:str,password:str):
    #LOGIN INTO MOODLE
    browser.get("https://presencial.moodle.ufsc.br/login")
    WebDriverWait(browser, 10).until(ExpC.element_to_be_clickable((By.ID, 'username')))
    browser.find_element(By.ID, "username").send_keys(user)
    browser.find_element(By.ID, "password").send_keys(password)
    browser.find_element(By.NAME, "submit").click()
    return pending_tasks()
