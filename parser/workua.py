from urllib.parse import urlparse
from bs4 import BeautifulSoup
from parser import ai_score
from parser import config
from pathlib import Path
import requests
import random
import time
import csv
import re
import os




def _get_response(
        url:str =config.PAGE_URL,
        headers:dict =config.USER_AGENT,
        timeout:int=5
) -> BeautifulSoup | None:
    try:
        session = requests.Session()
        session.headers.update(headers)
        responce = session.get(url=url,timeout=timeout)
        responce.raise_for_status()
        responce.encoding = 'utf-8'
        return BeautifulSoup(responce.text, 'lxml')
    except requests.exceptions.RequestException as e:
        print(f"Помилка при запиті до {url}: {e}")
        return None


def get_shema(url:str =config.PAGE_URL) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/"


def load_done_ids(path=config.PROCESSED_IDS_PATH) -> set:
    if not Path(path).exists():
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)


def append_done_id(vac_id: str, path=config.PROCESSED_IDS_PATH):
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{vac_id}\n")


def random_sleep(min_sec=1, max_sec=5.0):
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


def get_pages(PAGE_URL:str):
    last_page = [last.text for last in _get_response(PAGE_URL).find('ul', class_ = "pagination hidden-xs")][-4]
    last_page = int(last_page)
    pages_list = []
    if '?' in PAGE_URL:
        for i in range(1,last_page+1): 
            page_url = f'{PAGE_URL}&page={i}'
            pages_list.append(page_url)
        print(f'Створив список сторінок, загальною кількістю: {len(pages_list)}')
    else:
        for i in range(1,last_page+1): 
            page_url = f'{PAGE_URL}?page={i}'
            pages_list.append(page_url)
        print(f'Створив список сторінок, загальною кількістю: {len(pages_list)}')
    return pages_list


def get_vacations(page_list):
    vacations = []
    for page in page_list:
        try:
            hrefs = [{'url' : get_shema() + tag['href']} for tag in _get_response(page).find_all('a', href=True) if re.fullmatch(r"/jobs/\d+/", tag['href'])]     # Отримую посиланння на ваканцію
            vacations.extend(hrefs)
            print(f'Парсингую сторінку: {page}')
            random_sleep(0.3,0.6)
            if config.TEST_MODE and len(vacations) > config.TEST_PAGES:
                return vacations[:abs(config.TEST_PAGES)]
        except Exception as e:
            print(f'Помилка {e} при обробці сторкінки: {page}')
            continue
    print(f'Всього ваканцій отримано: {len(vacations)}')
    return vacations


def get_detalied_info(vacation_list, output_path:str):

    first_write = not os.path.exists(output_path)
    processed_ids = load_done_ids()

    job_list = []
    c = 1

    for job in vacation_list:
        try:
            job_id = job['url'].rstrip('/').split('/')[-1]
            if job_id in processed_ids:
                continue

            print(f'Прогрес перегляду ваканцій: {c}/{len(vacation_list)}')
            job_html = _get_response(job['url'])
            about = {}


            try:                                # блок обробки 1
                about['url'] = job['url']
                about['position'] = job_html.find('h1', id='h1-name').text if job_html.find('h1', id='h1-name') else None
                about['company'] = job_html.find('a', class_='inline').find('span', class_='strong-500').text if job_html.find('a', class_='inline').find('span', class_='strong-500') else None
                about['requirements'] = ' '.join(job_html.find('span', title='Умови й вимоги').find_parent('li').text.split()) if job_html.find('span', title='Умови й вимоги').find_parent('li') else None
                job_description = job_html.find('div', id='job-description').text if job_html.find('div', id='job-description') else None
                # about['description'] = job_description
                about['verify'] = 'verified' if job_html.find('span',class_="glyphicon glyphicon-tick glyphicon-fs-16 glyphicon-top") else None 
            except Exception as e:
                print('Помилка у блоці обробки 1: ', e)
                continue
            

            try:                                 # обробка оцінки ві ШІ  
                if config.IA_PROCCES:    
                    about['ai score'] = ai_score.get_score(job_description)
                else:
                    about['ai score'] = None
            except Exception as e:
                print('Помилка обробки оціеки від ШІ: ',e)
                about['ai score'] = None
            
            
            try:                                # обробка вмінь
                job_skills = job_html.find_all('span', class_="ellipsis")
                skills_raw = []
                for span in job_skills:
                    skill = span.text
                    skills_raw.append(skill)
                about['skills']=', '.join(skills_raw)
            except Exception as e:
                print('Помилка у блоці обробки вмінь: ', e)
                about['skills'] = None


            try:                               # обробка зп
                job_salary = job_html.find_all('li', class_='text-indent no-style mt-sm mb-0')
                clean_salary=None
                for li in job_salary:
                    icon = li.find('span', title='Зарплата')
                    if icon:
                        salary_span = li.find('span', class_='strong-500')
                        if salary_span:
                            clean_salary = salary_span.text.split()
                            if '–' in clean_salary:
                                dash_index = clean_salary.index('–')   
                                min_salary = int(clean_salary[0]+clean_salary[1])
                                max_salary = int(clean_salary[dash_index + 1] + clean_salary[dash_index + 2])
                                about['min salary'] = min_salary
                                about['max salary'] = max_salary
                            else:
                                min_salary = max_salary = int(clean_salary[0]+clean_salary[1])
                            break     
            except Exception as e:
                print('Помилка у блоці обробки заробітньої плати: ', e)
                about['min salary'] = None
                about['max salary'] = None


            try:                               # обробка галузі
                job_company_class = job_html.find_all('li', class_="text-indent no-style mt-sm mb-0")
                for li in job_company_class:
                    detalile = li.find('span', title="Дані про компанію")
                    if detalile:
                        class_ = li.find('span', class_="text-default-7")
                        if class_:
                            raw_text = class_.text
                            about['class'] = re.sub(r'\s+', ' ', raw_text).strip()
            except Exception as e:
                print('Помилка у блоці обробки 4: ', e)
                about['class'] = None

            c+=1
            random_sleep(0.5,4)

            if about:
                save_single_vacancy_as_csv(output_path, about, write_header=first_write)
                first_write = False
                append_done_id(job_id)
                job_list.append(about)

        except Exception as e:
                print('Помилка у блоці обробки детальної інформацї: ', e)
                continue
        

    print(job_list) if config.TEST_MODE else None
    print('\n'*2, '='*24, '\n', 'Список ваканцій створено', '\n', '='*24, '\n'*2)
    return job_list


def save_single_vacancy_as_csv(filename, data, write_header=False):
    try:
        with open(filename, mode='a', newline='', encoding='utf-8-sig') as file:
            filednames = ['position', 'min salary', 'max salary', 'company', 'class', 'requirements','skills', 'verify', 'url', 'ai score']
            writer = csv.DictWriter(file, fieldnames=filednames, delimiter=';')
            if write_header:
                writer.writeheader()
            writer.writerow(data)
    except Exception as e:
        print('Невдалося зберегти результати парсенгу')
        return
    