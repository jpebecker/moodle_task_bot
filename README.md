# Moodle Task Bot

Automação de coleta de tarefas publicadas com Python e Selenium.
Este projeto foi criado para facilitar o acompanhamento de atividades e prazos de entrega em múltiplas disciplinas, tornando essa rotina mais ágil e eficiente.

---

## Funcionalidades

- Login no Moodle.
- Listagem das disciplinas do semestre atual.
- Extração de atividades com prazos de entrega.
- Filtragem de atividades por data (futuras ou todas).
- Detecção de múltiplas matrículas.
- Verificação do status de envio de atividades.
- Armazenamento local de anotações e credenciais.
  
---

## Bibliotecas Utilizadas

 - re (padrão Python) — regex de strings compostas para coleta de data.
 - selenium — para automação de navegador.
 - tkinter — interface gráfica (GUI).
 - cryptography.fernet — para criptografia das credenciais.

---

## Estrutura do Projeto

 - app_interface.py: arquivo responsável por criar a janela que o usuário vê e interage. Utiliza principalmente o Tkinter para construir a UI (interface do usuário).
 - app_functions.py: arquivo responsável por funções relacionadas ao webscraping feito na plataforma da faculdade. Utiliza principalmente o Selenium WebDriver para a automação.

---

## Objetivo do Projeto

 - Auxiliar no dia a dia, melhorando a velocidade com que se verifica as pendências de atividades da faculdade.
 - Praticar e desafiar conhecimentos em automação, resolução de problemas e web sraping. Tudo em um projeto.
 - Explorar novas bibliotecas e metodologias.
---
