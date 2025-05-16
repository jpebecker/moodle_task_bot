import re
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
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

def pending_tasks(all_time=False):
    tarefas_pendentes.clear()
    disciplinas.clear()

    try:
        WebDriverWait(browser, 15).until(ExpC.presence_of_all_elements_located((By.CSS_SELECTOR, ".box.py-3.generalbox")))
        semestres_box = browser.find_elements(By.CSS_SELECTOR, ".box.py-3.generalbox")
        ul_semestre_atual = semestres_box[0].find_element(By.CSS_SELECTOR, 'ul')
        disciplinas_semestre_atual = ul_semestre_atual.find_elements(By.CSS_SELECTOR, 'li')
    except Exception as exc:
        print(f'-> Erro ao carregar disciplinas: {exc}')
        return None

    for subject in disciplinas_semestre_atual:
        try:
            link_elem = subject.find_element(By.TAG_NAME, 'a')
            nome = link_elem.text
            url = link_elem.get_attribute('href')
            disciplinas.append((nome, url))
        except Exception:
            continue

    for nome_disciplina, url_disciplina in disciplinas:
        try:
            browser.get(url_disciplina)
            WebDriverWait(browser, 10).until(ExpC.presence_of_all_elements_located((By.CLASS_NAME, "activity-item")))
            atividades = browser.find_elements(By.CLASS_NAME, "activity-item")
        except Exception as e:
            print(f"Erro ao carregar atividades de {nome_disciplina}: {e}")
            continue

        for atividade in atividades:
            try:
                activity_name = atividade.get_attribute("data-activityname")
                descricao_div = atividade.find_element(By.CLASS_NAME, "description")
                descricao_texto = descricao_div.find_element(By.CLASS_NAME, "description-inner").text

                if activity_name and 'Vencimento:' in descricao_texto:
                    data_vencimento = parse_text(descricao_texto)

                    if all_time or data_vencimento > datetime.now():
                        #activity link
                        url_element = atividade.find_element(By.CSS_SELECTOR, 'a.aalink.stretched-link')
                        activity_url = url_element.get_attribute('href')

                        #get into activity page
                        try:
                            browser.execute_script("window.open(arguments[0]);", activity_url)
                            browser.switch_to.window(browser.window_handles[-1])

                            WebDriverWait(browser, 10).until(
                                ExpC.presence_of_element_located((By.CSS_SELECTOR, 'div.submissionstatustable'))
                            )
                            table = browser.find_element(By.CSS_SELECTOR, 'div.submissionstatustable table')
                            first_td = table.find_element(By.CSS_SELECTOR, 'tbody > tr:first-child td')
                            status = first_td.text.strip()
                        except Exception as e:
                            status = "Erro ao obter status"
                            print(f"Erro ao obter status: {e}")
                        finally:
                            browser.close()
                            browser.switch_to.window(browser.window_handles[0])

                        task = {
                            'Disciplina': nome_disciplina,
                            'Tarefa': activity_name,
                            'Prazo': data_vencimento.strftime("%d/%m/%Y"),
                            'Status': status,
                        }
                        tarefas_pendentes.append(task)

            except Exception as exc:
                #print(exc)
                continue

    tarefas_ordenadas = sorted(tarefas_pendentes, key=lambda t: datetime.strptime(t["Prazo"], "%d/%m/%Y"))

    df = pd.DataFrame(tarefas_ordenadas)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 0)
    pd.set_option('display.max_colwidth', None)
    print(df)
    return df


def login_moodle(user: str, password: str, all_time: bool = False):
    # LOGIN INTO MOODLE
    browser.get("https://presencial.moodle.ufsc.br/login")
    WebDriverWait(browser, 10).until(ExpC.element_to_be_clickable((By.ID, 'username')))
    browser.find_element(By.ID, "username").send_keys(user)
    browser.find_element(By.ID, "password").send_keys(password)
    browser.find_element(By.NAME, "submit").click()
    WebDriverWait(browser,5)

    if "my" in browser.current_url:
        print('Login bem-sucedido.')
        return pending_tasks(all_time)
    else:
        print('Login falhou ou credenciais inválidas')
        return None