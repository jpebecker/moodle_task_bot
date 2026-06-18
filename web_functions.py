import re
import time
import logging
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ExpC

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def parse_date_text(text: str) -> datetime | None:
    """
    Extract the first valid due date from an activity description string.

    The function searches for occurrences of the Portuguese keyword
    ``"Vencimento:"`` followed by a date in the format used by Moodle UFSC,
    e.g. ``"Vencimento: sábado, 15 jun. 2024, 23:59"``.

    Args:
        text: Raw description text scraped from a Moodle activity block.

    Returns:
        A :class:`datetime` object for the first match, or ``None`` if no
        valid date pattern is found.
    """
    meses = {
        "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
        "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
    }

    matches = re.findall(
        r'Vencimento:\s*([a-zçãé\-]+),\s*(\d{1,2})\s*([a-zç]+)\.\s*(\d{4}),\s*(\d{2}:\d{2})',
        text,
        re.IGNORECASE,
    )

    for _, dia, mes_abrev, ano, hora in matches:
        mes_num = meses.get(mes_abrev.lower()[:3])
        if mes_num:
            data_str = f"{dia.zfill(2)}/{mes_num:02}/{ano} {hora}"
            return datetime.strptime(data_str, "%d/%m/%Y %H:%M")  # Return on first valid match

    return None


def toggle_page_extended(active_browser):
    """
    Ensure all course sections on the current page are fully expanded.

    If the toggle button reports the sections are already expanded, the
    function collapses them first and then re-expands to force a complete
    DOM refresh before activity elements are queried.

    Args:
        active_browser: Active :class:`selenium.webdriver.Chrome` instance.
    """
    expand_btn = active_browser.find_element(By.ID, "collapsesections")
    is_expanded = expand_btn.get_attribute("aria-expanded") == "true"

    if is_expanded:
        expand_btn.click()      # Collapse all sections
        time.sleep(0.5)
        expand_btn.click()      # Re-expand all sections
    else:
        expand_btn.click()      # Expand all sections


# ─────────────────────────────────────────────────────────────────────────────
# Core scraping functions
# ─────────────────────────────────────────────────────────────────────────────

def get_subjects(active_browser) -> list | None:
    """
    Collect all enrolled subjects from the Moodle dashboard for the most
    recent semester.

    The function targets the first ``.box.py-3.generalbox`` element on the
    page, which corresponds to the current semester block.

    Args:
        active_browser: Active :class:`selenium.webdriver.Chrome` instance,
                        already authenticated and on the dashboard page.

    Returns:
        A list of ``(name, url)`` tuples, one per subject, or ``None`` if
        the expected DOM structure could not be located.
    """
    subjects = []
    try:
        WebDriverWait(active_browser, 15).until(
            ExpC.presence_of_all_elements_located((By.CSS_SELECTOR, ".box.py-3.generalbox"))
        )
        semestres_box = active_browser.find_elements(By.CSS_SELECTOR, ".box.py-3.generalbox")
        ul_current = semestres_box[0].find_element(By.CSS_SELECTOR, "ul")
        items = ul_current.find_elements(By.CSS_SELECTOR, "li")
    except Exception as exc:
        logger.error("Failed to load subjects: %s", exc)
        return None

    for item in items:
        try:
            link_elem = item.find_element(By.TAG_NAME, "a")
            subjects.append((link_elem.text, link_elem.get_attribute("href")))
        except Exception:
            continue  # Skip list items that do not contain a direct link

    return subjects


def get_activities(active_browser, subject_url: str) -> list | None:
    """
    Navigate to a subject page and return all ``activity-item`` elements.

    The function expands all course sections before querying for activities
    and allows a short render delay for lazy-loaded descriptions.

    Args:
        active_browser: Active :class:`selenium.webdriver.Chrome` instance.
        subject_url:    Full URL of the Moodle subject/course page.

    Returns:
        A list of Selenium WebElements with class ``activity-item``, or
        ``None`` if navigation or element discovery fails.
    """
    active_browser.get(subject_url)
    try:
        WebDriverWait(active_browser, 10).until(
            ExpC.element_to_be_clickable((By.ID, "collapsesections"))
        )
        toggle_page_extended(active_browser)
        WebDriverWait(active_browser, 10).until(
            ExpC.visibility_of_all_elements_located((By.CLASS_NAME, "activity-item"))
        )
        time.sleep(1)  # Allow lazy-loaded activity descriptions to finish rendering
        activities = active_browser.find_elements(By.CLASS_NAME, "activity-item")
        logger.info("Activity blocks found: %d", len(activities))
        return activities
    except Exception as exc:
        logger.error("Failed to retrieve activities from '%s': %s", subject_url, exc)
        return None


def get_activities_status(active_browser, activity_url: str) -> str:
    """
    Navigate to an individual activity page and read the submission status.

    Uses direct ``get()`` / restore navigation instead of opening a new
    browser tab, which avoids window-handle switching errors.

    Args:
        active_browser: Active :class:`selenium.webdriver.Chrome` instance.
        activity_url:   Full URL of the Moodle assignment page.

    Returns:
        The submission status string extracted from the status table, or
        ``"Erro ao obter status"`` if the page structure is not as expected.
    """
    previous_url = active_browser.current_url
    try:
        active_browser.get(activity_url)
        WebDriverWait(active_browser, 15).until(
            ExpC.visibility_of_element_located((By.CSS_SELECTOR, "div.submissionstatustable"))
        )
        table = active_browser.find_element(By.CSS_SELECTOR, "div.submissionstatustable table")
        first_td = table.find_element(By.CSS_SELECTOR, "tbody > tr:first-child td")
        status = first_td.text.strip()
    except Exception as exc:
        logger.warning("Could not retrieve status for '%s': %s", activity_url, exc)
        status = "Erro ao obter status"
    finally:
        active_browser.get(previous_url)  # Restore the subject page

    return status


def login_moodle(active_browser, user: str, secret: str) -> dict:
    """
    Authenticate on the Moodle UFSC platform and return a structured result.

    After submitting the login form the function inspects the resulting URL
    to determine the outcome and handles the multi-curriculum-number edge
    case.

    Args:
        active_browser: Active :class:`selenium.webdriver.Chrome` instance.
        user:           Plain-text Moodle username.
        secret:         Plain-text Moodle password.

    Returns:
        A dict with one of the following shapes:

        * ``{"status": "success",      "data": [(name, url), ...]}``
          — Login succeeded; ``data`` is the subject list.
        * ``{"status": "multiple_ids", "data": [(id, url), ...]}``
          — Account has multiple curriculum numbers; user must choose one.
        * ``{"status": "error",        "data": None}``
          — Login failed (wrong credentials or unexpected page structure).
    """
    active_browser.get("https://presencial.moodle.ufsc.br/login")
    WebDriverWait(active_browser, 10).until(ExpC.element_to_be_clickable((By.ID, "username")))
    active_browser.find_element(By.ID, "username").send_keys(user)
    active_browser.find_element(By.ID, "password").send_keys(secret)
    active_browser.find_element(By.NAME, "submit").click()
    WebDriverWait(active_browser, 5).until(lambda b: True)

    if "my" in active_browser.current_url:
        logger.info("Login successful.")
        return {"status": "success", "data": get_subjects(active_browser)}

    # Check whether the page presents a curriculum number selection table
    try:
        table = active_browser.find_element(By.CSS_SELECTOR, "div.table-responsive table")
        id_links = table.find_elements(By.CSS_SELECTOR, "td.cell.c1 a")
        curriculum_numbers = [
            (link.text, link.get_attribute("href")) for link in id_links
        ]
        logger.info("Multiple curriculum IDs detected: %s", [c[0] for c in curriculum_numbers])
        return {"status": "multiple_ids", "data": curriculum_numbers}
    except Exception:
        logger.warning("Login failed or unexpected page structure.")
        return {"status": "error", "data": None}


def select_curriculum_number(active_browser, user_id_page: str):
    """
    Click the curriculum number link that matches *user_id_page* and wait
    for the Moodle dashboard to load.

    This function handles the final step of the multi-curriculum login flow.

    Args:
        active_browser: Active :class:`selenium.webdriver.Chrome` instance,
                        currently on the curriculum selection page.
        user_id_page:   The ``href`` of the curriculum link to activate.

    Raises:
        RuntimeError: If the target link is not found or navigation fails.
    """
    try:
        WebDriverWait(active_browser, 10).until(
            ExpC.presence_of_element_located((By.CSS_SELECTOR, "td.cell.c1 a"))
        )
        for link in active_browser.find_elements(By.CSS_SELECTOR, "td.cell.c1 a"):
            if link.get_attribute("href") == user_id_page:
                link.click()
                WebDriverWait(active_browser, 10).until(lambda b: "my" in b.current_url)
                return
        raise ValueError(f"Link with href '{user_id_page}' not found.")
    except Exception as exc:
        raise RuntimeError(f"Failed to select curriculum identity: {exc}")


def loop_activities(activities_list: list, all_time: bool = False) -> list:
    """
    Filter a list of activity WebElements by due date and return those that
    match the selection criteria.

    Args:
        activities_list: List of Selenium WebElements with class
                         ``activity-item``, as returned by
                         :func:`get_activities`.
        all_time:        When ``False`` (default), only activities whose due
                         date is in the future are included.  When ``True``,
                         all activities with a parseable due date are
                         returned, regardless of whether they have passed.

    Returns:
        A list of ``(name, url, due_date)`` tuples for the activities that
        satisfy the filter criteria.
    """
    result = []
    for atividade in activities_list:
        try:
            activity_name = atividade.get_attribute("data-activityname")
            if not activity_name:
                continue

            descricao_div   = atividade.find_element(By.CLASS_NAME, "description")
            descricao_texto = descricao_div.find_element(By.CLASS_NAME, "description-inner").text

            if "Vencimento:" not in descricao_texto:
                continue

            activity_due_date = parse_date_text(descricao_texto)
            if not activity_due_date:
                logger.debug("No parseable due date for '%s', skipping.", activity_name)
                continue

            if not all_time and activity_due_date <= datetime.today():
                continue  # Skip past activities when all_time is disabled

            url_element  = atividade.find_element(By.CSS_SELECTOR, "a.aalink.stretched-link")
            activity_url = url_element.get_attribute("href")

            if activity_url:
                result.append((activity_name, activity_url, activity_due_date))
            else:
                logger.warning("Missing URL for activity '%s', skipping.", activity_name)

        except Exception:
            continue  # Silently skip malformed or incomplete activity blocks

    return result