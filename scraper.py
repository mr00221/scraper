import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request
from datetime import datetime
from telegram import Bot

scrapeTime = datetime.now()
import requests

app = Flask(__name__)

sending = True

session = None

server_addr = 'http://django-service'

def replace_sumike(bsd):
    crke = {"Č": "C",
            "č": "c",
            "Ž": "Z",
            "ž": "z",
            "Š": "S",
            "š": "s"}

    for crka in crke.keys():
        bsd = bsd.replace(crka, crke[crka])
    return bsd


def can_send_to_user(userID, avto_naslov, avto_cena, avto_letnik):
    avto_naslov = avto_naslov.lower()
    r = session.get(url=server_addr + ':8000/app1/filters/?userID=' + str(userID))
    filtri = r.json()
    for f in filtri:
        if f['znamka'] is None or f['znamka'].lower() in avto_naslov:
            if f['model'] is None or f['model'].lower() in avto_naslov:
                if f['cena_od'] is None or int(avto_cena) >= int(f['cena_od']):
                    if f['cena_do'] is None or int(avto_cena) <= int(f['cena_do']):
                        if f['letnik_od'] is None or int(avto_letnik) >= int(f['letnik_od']):
                            if f['letnik_do'] is None or int(avto_letnik) <= int(f['letnik_do']):
                                return True
    return False


# brez sprehajanja po podstraneh, vse podakte dobi iz banerja
def fast100():
    global session
    session = requests.Session()
    scrapeTime = datetime.now()

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko'}
    result = requests.get("https://www.avto.net/Ads/results_100.asp?oglasrubrika=1&prodajalec=0", headers=headers)
    print(headers)
    src = result.content

    soup = BeautifulSoup(src, "html.parser")
    cars = soup.find_all("div", {"class": "GO-Results-Row"})

    # Dobi vse uporabnike za posiljanje
    r = session.get(url=server_addr + ':8000/app1/users/')
    users = r.json()

    # print(soup)
    # TODO posreduje listo avtomobilov, dobi seznam avtomobilov, ki niso v bazi
    for car in cars:
        car_id = car.find("a", {"class": "stretched-link"}).attrs["href"].split("id=")[1].split("&")[0]
        # Preveri ali se avto nahaja v bazi
        r = session.get(url=server_addr + ':8000/app1/avti/' + str(car_id))
        if r.status_code != 404:
            continue
        naslov = car.find("div", {"class": "GO-Results-Naziv"}).find("span").text
        try:
            car_link = "https://www.avto.net/Ads/details.asp?id=" + str(car_id)
            fizicna = 1

            data = car.find("div", {"class": "GO-Results-Data-Top"}).find("table").find_all("tr")
            letnik = str(datetime.now().year)
            kilometri = "0"
            for tr in data:
                try:
                    ime_polja = tr.find_all("td")[0].text
                    vrednost = tr.find_all("td")[1].text
                    if "Prevo" in ime_polja:
                        kilometri = vrednost.split(" ")[0]
                    if "registrac" in ime_polja:
                        letnik = vrednost
                    if "Starost" in ime_polja:
                        letnik = str(datetime.now().year)
                except:
                    pass

            if car.find("div", {"class": "GO-Results-Price-TXT-Regular"}):
                cena = car.find("div", {"class": "GO-Results-Price-TXT-Regular"}).text
            else:
                cena = car.find("div", {"class": "GO-Results-Top-Price-TXT-AkcijaCena"}).text

            cena = cena.split(" ")[0].replace(".", "")

            try:
                int(cena)
            except:
                cena = "0"

            # TODO po nepotrebnem za vsak avto klice uporabnike, optimiziraj
            for user in users:
                userID = int(user['userID'])
                if sending and can_send_to_user(userID, naslov, cena, letnik):
                    b = Bot(token="1024063569:AAFV_fy723VkLlQs8qIacdIggM5CCkTasOo")
                    slika = car.find("div", {"class": "GO-Results-Photo"}).find("img").attrs["src"].replace("_160", "")
                    sporocilo = naslov + '\nLetnik: ' + letnik + '\nCena: ' + cena + '€\n<a href="' + car_link + '">Ogled oglasa</a>'

                    b.send_photo(chat_id=userID, photo=slika, caption=sporocilo, parse_mode='HTML')

            # TODO vstavi avto v podatkovno bazo
            jsondata = {"carID": car_id, "ime": replace_sumike(naslov), "cena": cena, "registracija": letnik + "-01-01", "km": kilometri,
                        "fizicna_os": fizicna, "poskodovano": 0, "scrapeTime": scrapeTime.strftime("%Y-%m-%dT%H:%M:%S")}

            session.post(url=server_addr + ':8000/app1/avti/', json=jsondata)
            print("Uspesno shranil avto: " + naslov)
        except Exception as e:
            print(e)


@app.route("/startscrape/")
def scrape():
    fast100()
    return "Scrape completed"

@app.route("/")
def probe():
    print("Probe called")
    response = app.response_class(
        response="Call probe",
        status=200
    )
    return response


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)


