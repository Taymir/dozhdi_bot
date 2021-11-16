import random
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import cv2
import numpy as np
from selenium.webdriver.firefox.options import Options
import os
import time
import asyncio


def make_url(lat: float, lon: float):
    url = f"https://yandex.ru/pogoda/maps/nowcast?le_Lightning=1&ll={lon}_{lat}&z=10"
    return url


async def request_mp4(lat: float, lon: float):
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Firefox(options=options)
    driver.set_window_rect(0, 0, 1000, 1000)
    url = make_url(lat, lon)

    driver.get(url)

    elem = WebDriverWait(driver, 50).until(
        EC.presence_of_element_located((By.CLASS_NAME, "tiled-nowcast-loader"))
    )
    driver.execute_script('document.getElementsByClassName("adv_pos_popup")[0].hidden = true') #hide advertisement
    driver.execute_script('document.getElementsByClassName("sc-bdnylx")[0].hidden = true') #hide cookies popup
    driver.execute_script(
        'document.getElementsByClassName("weather-maps__layer-buttons")[0].style = {"display": "none"}') #hide buttons
    driver.execute_script('document.getElementsByClassName("ymaps-2-1-78-copyrights-pane")[0].hidden = true')
    await asyncio.sleep(6)
    elem = driver.find_element_by_tag_name("body")

    x = 380  # 400
    y = 160  # 160
    w = 540  # 520
    h = 730  # 650

    random_name = str(random.randint(10000, 99999)) + ".mp4"
    filename = os.path.join('var', random_name)
    videodims = (w, h)

    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    video = cv2.VideoWriter(filename, fourcc, 2, videodims)

    for i in range(10):
        await asyncio.sleep(0.5)
        shot_bytes = driver.get_screenshot_as_png()
        nparr = np.frombuffer(shot_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        img = img[y:y + h, x:x + w]
        img = np.array(img)
        video.write(img)
        elem.send_keys(Keys.ARROW_RIGHT)
    video.release()

    driver.close()
    return filename


async def remove_file(filename):
    os.remove(filename)


