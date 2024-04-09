'''Отслеживание наличия и изменения стоимости настольных игр
путём парсинга сайтов.'''
COMPARE_PRICE = '__{}__ на {} ₽ | {}%'
PARSING_DELAY = 5  # 86400 секунд в сутках
PRICE_INFO = '**{}**\nНовая цена: **{}** ₽\n{}'
REPORT_TITLE = '❗️ Новые данные от **HOBBYGAMES** ❗️'
STATUS_INFO = '**{}**\nтеперь __{}__'

last_parsing = {  # тестовые данные с изменением цены и статуса игр
    86318: {'Название': 'Столкновение цивилизаций: Монументальное издание', 'Цена': 9990, 'Статус': 'ОТСУТСТВУЕТ'},
    102256: {'Название': 'Набор игр "Ядер-кола одобряет"', 'Цена': 9581, 'Статус': 'ОТСУТСТВУЕТ'},
    94647: {'Название': 'Кольт Экспресс. Большое приключение', 'Цена': 3890, 'Статус': 'В НАЛИЧИИ'},
    63945: {'Название': 'Повелитель Токио', 'Цена': 4000, 'Статус': 'В НАЛИЧИИ'}
}  # для проверки корректной работы при активации скрипта


def get_content(html):
    '''Запускает сбор информации с переданной страницы.'''
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'html.parser')
    print(soup.find('title').text)  # название сканируемой страницы
    favorites = soup.find_all('li', {'class': 'favorites-table__product'})
    games_data = dict()
    for game in favorites:
        _id = int(game.attrs['data-product-id'])
        title = game.find('a', {'class': 'favorites-table__product-name favorites-table__product-name--link'}).text
        dirty_price = game.find('span', {'aria-label': 'Цена'}).text
        price = int(dirty_price[:dirty_price.index('₽')].replace(' ', ''))
        available = (
            'ОТСУТСТВУЕТ' if 'disabled' in game.find('button').attrs
            else 'В НАЛИЧИИ'
        )
        games_data[_id] = {
            'Название': title, 'Цена': price, 'Статус': available
        }
    return games_data


def compare_prices(price_now, price_last):
    '''Вычисляет и возвращает информацию об изменении цены.'''
    price_change = 'ПОДОРОЖАЛА' if price_now > price_last else 'СТАЛА ДЕШЕВЛЕ'
    difference = max(price_now, price_last) - min(price_now, price_last)
    percent = round(difference / price_last * 100, 2)
    return COMPARE_PRICE.format(price_change, difference, percent)


def send_message(messages):
    '''Отправляет уведомление в Телеграмм.'''
    import os
    from dotenv import load_dotenv
    from pyrogram import Client

    load_dotenv()
    API_ID = os.getenv('API_ID')
    API_HASH = os.getenv('API_HASH')
    REPORT_TO = os.getenv('CHAT')
    app = Client(name='board_games', api_id=API_ID, api_hash=API_HASH)
    app.start()
    app.send_message(chat_id=REPORT_TO, text=REPORT_TITLE)
    for message in messages:
        app.send_message(chat_id=REPORT_TO, text=message)
    app.stop()
    return


def check_changes(html):
    '''Проверяет изменение данных по результатам парсинга.'''
    global last_parsing
    new_data = get_content(html)
    if last_parsing != new_data:
        messages = []
        for _id, details in new_data.items():
            if _id not in last_parsing:
                continue
            status_now = details['Статус']
            status_last = last_parsing[_id]['Статус']
            if status_now != status_last:
                messages.append(
                    STATUS_INFO.format(details['Название'], status_now)
                )
            price_now = details['Цена']
            price_last = last_parsing[_id]['Цена']
            if price_now != price_last:
                compare = compare_prices(price_now, price_last)
                messages.append(
                    PRICE_INFO.format(details['Название'], price_now, compare)
                )
        if messages:
            send_message(messages)
        last_parsing = new_data
    return


def hobbygames(show, screenshot):
    '''Получение html кода сайта «hobbygames.ru» (наличие защиты от ботов).'''
    import os
    from dotenv import load_dotenv
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    from undetected_chromedriver import By
    import undetected_chromedriver as uc

    load_dotenv()
    FAVORITES = 'https://hobbygames.ru/account/favorites'
    LOGIN = os.getenv('LOGIN')
    MAIN_PAGE = 'https://hobbygames.ru'
    PASSWORD = os.getenv('PASSWORD')
    # указать путь к exe файлу браузера Chrome (при необходимости):
    # browser_executable_path='...'
    # открывать браузер в фоновом режиме: headless=True
    driver = uc.Chrome(headless=not show)
    try:
        driver.get(MAIN_PAGE)  # открыть главную страницу
        # найти и нажать элемент «Войти» (авторизация)
        driver.find_element(By.CLASS_NAME, 'user-profile').click()
        # подождать подгрузку формы авторизации
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="login-form"]/div/input')
            )
        )
        # найти поле ввода логина и ввести его
        driver.find_element(
            By.XPATH, '//*[@id="login-form"]/label[1]/input'
        ).send_keys(LOGIN)
        # найти поле ввода пароля и ввести его
        driver.find_element(
            By.XPATH, '//*[@id="login-form"]/label[2]/input'
        ).send_keys(PASSWORD)
        # найти и нажать кнопку «Вход»
        driver.find_element(
            By.XPATH, '//*[@id="login-form"]/div/input'
        ).click()
        # ожидать появления элемента «Профиль» (завершение авторизации)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="js-showDropdownLKMenu"]/span')
            )
        )
        driver.get(FAVORITES)  # перейти на страницу «Избранное»
        # ожидать полной загрузки элементов в «Избранном»
        WebDriverWait(driver, 2).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="favorites-list"]/div/ul')
            )
        )
        if screenshot:
            driver.save_screenshot('page_screenshot.png')  # сделать скриншот
        check_changes(driver.page_source)  # запустить парсинг html кода
    except Exception as exception:
        print(f'Ошибка: {exception}')
    finally:
        driver.close()
        driver.quit()


def main():
    '''Запуск последовательного парсинга требуемых сайтов.'''
    from time import sleep

    while True:
        hobbygames(show=False, screenshot=False)
        sleep(PARSING_DELAY)


if __name__ == '__main__':
    main()
