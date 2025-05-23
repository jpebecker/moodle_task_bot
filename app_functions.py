import re,time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ExpC

def parse_date_text(text: str) -> datetime | None:
    """
    Recebe um texto poluido com a palavra-chave 'Vencimento'
    e retorna um datetime
    """
    data_obj = None

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

def get_subjects(active_browser):
    subjects = []
    try: #get all subjects in the latest semester 'semestres_box[0]'
        WebDriverWait(active_browser, 15).until(ExpC.presence_of_all_elements_located((By.CSS_SELECTOR, ".box.py-3.generalbox")))
        semestres_box = active_browser.find_elements(By.CSS_SELECTOR, ".box.py-3.generalbox")
        ul_semestre_atual = semestres_box[0].find_element(By.CSS_SELECTOR, 'ul')
        disciplinas_semestre_atual = ul_semestre_atual.find_elements(By.CSS_SELECTOR, 'li')
    except Exception as exc:
        print(f'-> Erro ao carregar disciplinas: {exc}')
        return None

    for subject in disciplinas_semestre_atual: #get the url and the text from the subjects list of Li
        try:
            link_elem = subject.find_element(By.TAG_NAME, 'a')
            nome = link_elem.text
            url = link_elem.get_attribute('href')
            subjects.append((nome, url))
        except Exception as exc:
            #print(exc)
            continue
    return subjects

def get_activities(active_browser,subject_url:str,all_time=False):
    atividades = None
    actual_subject_activities = []
    actual_subject_activities_url = []
    try:
        active_browser.get(subject_url)
        WebDriverWait(active_browser, 10).until(ExpC.element_to_be_clickable((By.ID, "collapsesections")))
        #######################################GET ALL SECTIONS OF ACTIVITIES OPEN AT THE SUBJECT PAGE
        botao = active_browser.find_element(By.ID, "collapsesections") #sections state btn
        aria_expanded = botao.get_attribute("aria-expanded")

        if aria_expanded == "true": #if the btn is in "Close All" state
            botao.click()  #close all
            time.sleep(0.4) #delay
            botao = active_browser.find_element(By.ID, "collapsesections") #recapture the btn
            botao.click()  #open all
        else: #if the btn is on "Expand All' state
            for _ in range(3): #to guarantee sucess it will loop through
                botao = active_browser.find_element(By.ID, "collapsesections")
                botao.click() #expand-close-expand to work fine
                time.sleep(0.4)
        ########################################get activities
        time.sleep(0.5)
        WebDriverWait(active_browser, 10).until(ExpC.presence_of_all_elements_located((By.CLASS_NAME, "activity-item")))
        atividades = active_browser.find_elements(By.CLASS_NAME, "activity-item")
    except Exception as e:
        print(f"Erro ao carregar atividades: {e}")

    for atividade in atividades:
        try:
            activity_name = atividade.get_attribute("data-activityname")
            descricao_div = atividade.find_element(By.CLASS_NAME, "description")
            descricao_texto = descricao_div.find_element(By.CLASS_NAME, "description-inner").text

            if activity_name and 'Vencimento:' in descricao_texto:
                activity_due_date = parse_date_text(descricao_texto)

                if all_time or activity_due_date > datetime.now():
                    #activity link
                    url_element = atividade.find_element(By.CSS_SELECTOR, 'a.aalink.stretched-link')
                    activity_url = url_element.get_attribute('href')
                    actual_subject_activities.append((activity_name,activity_url,activity_due_date))

        except Exception as exc:
            #print(exc)
            continue

    return actual_subject_activities

def get_activities_status(active_browser,activity_url:str):
    # get into activity page
    try:
        active_browser.execute_script("window.open(arguments[0]);", activity_url)
        active_browser.switch_to.window(active_browser.window_handles[-1])

        WebDriverWait(active_browser, 10).until(
            ExpC.visibility_of_element_located((By.CSS_SELECTOR, 'div.submissionstatustable'))
        )
        table = active_browser.find_element(By.CSS_SELECTOR, 'div.submissionstatustable table')
        first_td = table.find_element(By.CSS_SELECTOR, 'tbody > tr:first-child td')
        status = first_td.text.strip()
    except Exception as e:
        status = "Erro ao obter status"
        print(f"Erro ao obter status: {e}")
    finally:
        active_browser.close()
        active_browser.switch_to.window(active_browser.window_handles[0])

    return status

def login_moodle(active_browser,user:str,secret:str):
    """
        This function occurs after the user click in Login at the interface and have exception routes for error in credentials
        and if the user have multiple curriculum numbers
        """

    active_browser.get("https://presencial.moodle.ufsc.br/login")
    WebDriverWait(active_browser, 10).until(ExpC.element_to_be_clickable((By.ID, 'username')))
    active_browser.find_element(By.ID, "username").send_keys(user)
    active_browser.find_element(By.ID, "password").send_keys(secret)
    active_browser.find_element(By.NAME, "submit").click()
    WebDriverWait(active_browser, 5).until(lambda b: True)
    curriculum_numbers = []

    if "my" in active_browser.current_url:
        print('Login bem-sucedido.')
        return {"status": "success", "data": get_subjects(active_browser)}
    else:
        try:
            table = active_browser.find_element(By.CSS_SELECTOR, "div.table-responsive table")
            id_links = table.find_elements(By.CSS_SELECTOR, "td.cell.c1 a")
            links = [link.get_attribute('href') for link in id_links]
            user_ids = [link.text for link in id_links]
            for i in range(len(user_ids)):
                curriculum_numbers.append((user_ids[i], links[i]))
            print("Múltiplos IDs de usuário:", user_ids)
            return {"status": "multiple_ids", "data": curriculum_numbers}
        except:
            print('Login falhou ou estrutura da tabela não encontrada.')
            return {"status": "error", "data": None}

def select_curriculum_number(active_browser,user_id_page):
    """
        In a multi-curriculum number scenario, this function selects the curriculum number that the user wants to access moodle.
        OBS: this is the LAST step in the multi-curriculum number case
        """
    try:
        WebDriverWait(active_browser, 10).until(
            ExpC.presence_of_element_located((By.CSS_SELECTOR, "td.cell.c1 a")))

        table_links = active_browser.find_elements(By.CSS_SELECTOR, "td.cell.c1 a")

        # get corresponding url
        for link in table_links:
            if link.get_attribute('href') == user_id_page:
                link.click()
                WebDriverWait(active_browser, 10).until(lambda b: "my" in b.current_url)
                return  # exit and continues the process

        raise ValueError(f"Link com href '{user_id_page}' não encontrado.")

    except Exception as Exc:
        raise RuntimeError(f"Erro ao selecionar identidade: {Exc}")