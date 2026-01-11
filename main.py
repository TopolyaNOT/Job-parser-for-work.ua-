from parser import config
from parser import workua

def main():

    parsing_pages = workua.get_pages(config.PAGE_URL)
    if not parsing_pages:
        print('Невдалося отримати сторінки для парсингу')
        return

    vacations_on_pages = workua.get_vacations(parsing_pages)
    if not vacations_on_pages:
        print('Невдалося отримати ваканції для парсингу')
        return

    about_vacation = workua.get_detalied_info(vacations_on_pages, 'data/test_v3.csv')
    if not about_vacation:
        print('Невдалося отримати ваканцію') 



if __name__ == "__main__":
    main()