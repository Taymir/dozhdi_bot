from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from PIL import Image
from io import BytesIO

import time





def main():
    #url = "https://yandex.ru/pogoda/moscow/maps/nowcast?le_Lightning=1"
    #url = "https://yandex.ru/pogoda/moscow/maps/nowcast?ll=37.617011_55.745857&z=10&le_Lightning=1"
    url = "https://yandex.ru/pogoda/maps/nowcast?le_Lightning=1&lat=55.91320191400199&lon=37.809271578125006&ll=30.392958_59.911052&z=10"
    driver = webdriver.Firefox()
    driver.set_window_rect(0, 0, 1000, 1000)
    driver.get(url)

    # document.getElementsByClassName('tiled-nowcast-loader')[0].getElementsByTagName('canvas')[0].toDataURL()
    elem = WebDriverWait(driver, 50).until(
        EC.presence_of_element_located((By.CLASS_NAME, "tiled-nowcast-loader"))
    )

    time.sleep(5)
    elem = driver.find_element_by_tag_name("body")
    imgs = []
    drts = []
    for i in range(10):
        time.sleep(0.2)
        shot = driver.get_screenshot_as_png()
        img = Image.open(BytesIO(shot))
        roi = (400, 160, 400+520, 160+600)
        img = img.crop(roi)
        #img.save(f"var/{i}.png")
        imgs.append(img)
        drts.append(500)
        elem.send_keys(Keys.ARROW_RIGHT)
    drts[0] = 1000
    imgs[0].save("var/anim.gif", save_all=True, append_images=imgs[1:], duration=drts, loop=0)

    driver.close()


if __name__ == '__main__':
    main()

