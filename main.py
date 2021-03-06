from random import randrange
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from datetime import datetime, date
import psycopg2
import configparser
config = configparser.ConfigParser()
config_file_name = "config"
config.read(config_file_name)
group_token = config['tokens']['group_token']
service_token = config['tokens']['service_token']

users = []
vk = vk_api.VkApi(token=group_token)
vk_service = vk_api.VkApi(token=service_token)
longpoll = VkLongPoll(vk)
con = psycopg2.connect(database="bot_users", user="postgres", password=config['database']['pass'],
                       host="127.0.0.1", port="5432")
cur = con.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS BOT_USERS (ID INT PRIMARY KEY, AGE INT, CITY INT, SEX INT);''')
con.commit()
supported_cities = {"Москва": 1, "Волгоград": 10, "Самара": 123}


class VkUser:

    def __init__(self, id, age=0, city=0, sex=0):
        self.id = id
        self.age = age
        self.city = city
        self.sex = sex

    def insert_into_table(self):
        try:
            cur.execute(f'INSERT INTO BOT_USERS (ID, AGE, CITY, SEX) VALUES ({str(self.id)},'
                        f'{str(self.age)},{self.city},{str(self.sex)})')
        except psycopg2.errors.UniqueViolation:
            pass
        return con.commit()

    def update_data(self):
        u_data = vk.method('users.get', {'user_id': self.id, 'fields': "sex,city,bdate"})[0]
        print(u_data)
        for data in u_data:
            if data == 'sex':
                cur.execute(f'''UPDATE BOT_USERS SET sex={u_data[data]} WHERE id={self.id}''')
                self.sex = u_data[data]
            if data == 'bdate':
                age = calculate_age(u_data[data])
                cur.execute(f'''UPDATE BOT_USERS SET age={age} WHERE id={self.id}''')
                self.age = age
            if data == 'city':
                cur.execute(f'''UPDATE BOT_USERS SET city={u_data[data]['id']} WHERE id={self.id}''')
                self.city = u_data[data]['id']
        return con.commit()

    def get_data(self):
        cur.execute(f"SELECT ID, SEX, AGE, CITY FROM BOT_USERS WHERE ID={self.id}")
        return cur.fetchall()

    def ask_the_data(self):
        for data in self.__dict__.items():
            if data[1] == 0 and data[0] == 'age':
                self.write_msg(f"Сколько тебе лет?")
                age = wait_reply()
                while int(age) <= 0:
                    self.write_msg(f"Некорректный возраст. Повтори ещё раз, пожалуйста.")
                cur.execute(f'''UPDATE BOT_USERS SET age={age} WHERE id={self.id}''')
            if data[1] not in supported_cities and data[0] == 'city':
                self.write_msg(f"Из какого ты города?\nПоддерживаемые города: " + ", ".join(supported_cities.keys()))
                city = wait_reply()
                while not city:
                    if city not in supported_cities:
                        self.write_msg(f"К сожалению, данный город не поддерживается.")
                    city = False
                self.write_msg(f'Хорошо, твой город ' + city)
                cur.execute(f'''UPDATE BOT_USERS SET city={supported_cities[city]} WHERE id={self.id}''')
            if data[1] == 0 and data[0] == 'sex':
                self.write_msg(f"Какого ты пола?")
                sex = wait_reply()
                while int(sex) <= 0:
                    self.write_msg(f"Некорректный возраст. Повтори ещё раз, пожалуйста.")
                cur.execute(f'''UPDATE BOT_USERS SET sex={sex} WHERE id={self.id}''')

    def get_user_name(self):
        return vk.method('users.get', {'user_id': self.id})[0]['first_name']

    def remove_user(self):
        cur.execute(f'''DELETE FROM BOT_USERS WHERE ID={self.id}''')
        return con.commit()

    def write_msg(self, message):
        vk.method('messages.send', {'user_id': self.id, 'message': message, 'random_id': randrange(10 ** 7), })


def wait_reply():
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            if event.to_me:
                return event.text


def get_russian_cities():
    cities = vk_service.method("database.getCities", {'country_id': 1})
    print(cities)


def calculate_age(born):
    born = datetime.strptime(born, '%d.%m.%Y')
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def main():
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:

            if event.to_me:
                request = event.text
                uid = event.user_id
                vku = VkUser(uid)
                vku.insert_into_table()
                if request.lower() == "1":
                    vku.write_msg(f"Хай, {vku.get_user_name()}")
                    vku = VkUser(uid)
                    vku.update_data()
                    vku.ask_the_data()
                elif request == "пока":
                    vku.write_msg("Пока((")
                else:
                    vku.write_msg("Не поняла вашего ответа...")


if __name__ == '__main__':
    # get_russian_cities()
    # VkUser(65268211).remove_user()
    # VkUser(65268211).get_user_name()
    main()
