from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from PIL import Image
from io import BytesIO
from selenium.webdriver.firefox.options import Options


import time


async def request_gif(lat: float, lon: float):
    url = f"https://yandex.ru/pogoda/maps/nowcast?le_Lightning=1&ll={lon}_{lat}&z=10"
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Firefox(options=options)
    driver.set_window_rect(0, 0, 1000, 1000)
    driver.get(url)

    elem = WebDriverWait(driver, 50).until(
        EC.presence_of_element_located((By.CLASS_NAME, "tiled-nowcast-loader"))
    )
    driver.execute_script('document.getElementsByClassName("adv_pos_popup")[0].hidden = true')
    driver.execute_script(
        'document.getElementsByClassName("weather-maps__layer-buttons")[0].style = {"display": "none"}')
    driver.execute_script('document.getElementsByClassName("ymaps-2-1-78-copyrights-pane")[0].hidden = true')
    time.sleep(6)
    elem = driver.find_element_by_tag_name("body")
    imgs = []
    drts = []
    for i in range(10):
        time.sleep(0.3)
        shot = driver.get_screenshot_as_png()
        img = Image.open(BytesIO(shot))

        rect = {
            'x': 380,  # 400
            'y': 160,  # 160
            'w': 540,  # 520
            'h': 760   # 650
        }
        roi = (rect['x'], rect['y'], rect['x']+rect['w'], rect['y']+rect['h'])
        img = img.crop(roi)
        imgs.append(img)
        drts.append(500)
        elem.send_keys(Keys.ARROW_RIGHT)
    drts[0] = 1000
    output = BytesIO()
    imgs[0].save(output, format='gif', save_all=True, append_images=imgs[1:], duration=drts, loop=0)
    driver.close()

    output.seek(0)
    return output
