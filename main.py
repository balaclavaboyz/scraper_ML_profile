import dataclasses
import re

from bs4 import BeautifulSoup
from datetime import datetime
import json
import pickle
import sqlite3
import requests
from dataclasses import dataclass, asdict


@dataclass
class Myprod:
    id: str
    price: float
    title: str
    stock: int
    isFull: bool
    qntSales: int
    createDate: str


@dataclass
class Profile:
    id: str
    name: str
    number_prods: int
    prods: dict


def user_prods(session: requests.Session, input_profile: str) -> dict:
    res = session.get(f'https://api.mercadolibre.com/sites/MLB/search?seller_id={input_profile}')
    info = dict(json.loads(json.dumps(res.json())))
    return info


def user_list_items(session: requests.Session, user: str) -> dict:
    res = session.get(f'https://api.mercadolibre.com/users/{user}/items/search')
    info = dict(json.loads(json.dumps(res.json())))
    return info


@dataclass
class Sql:
    def __init__(self):
        self.con = sqlite3.connect('db.sqlite3')
        self.cur = self.con.cursor()

    def create_db(self):
        self.cur.execute('''
        CREATE TABLE if not exists "profiles" (
            "id"	INTEGER NOT NULL UNIQUE,
            "fk_prods"	INTEGER,
            "name"	TEXT NOT NULL,
            "number_prods"	TEXT NOT NULL DEFAULT 0,
            FOREIGN KEY("id") REFERENCES "prods"("id"),
        ); 
       ''')
        self.cur.execute('''
        CREATE TABLE if not exists "prods" (
            "id"	INTEGER NOT NULL UNIQUE,
            "price"	REAL,
            "title"	TEXT,
            "stock"	INTEGER DEFAULT 0,
            "qntSales"	INTEGER DEFAULT 0,
            "createDate"	TEXT,
            "permalink"	TEXT,
            "thumb"	TEXT,
            "listing_type_id"	TEXT,
        ); 
       ''')

    def create_profile(self, profile_json):
        loc = ''
        for v in profile_json['available_filters']:
            if v['id'] == 'state':
                loc = v['values'][0]['name']
        data = (
            profile_json['seller']['id'],
            profile_json['seller']['nickname'],
            profile_json['paging']['total'],
            profile_json['seller']['seller_reputation']['transactions']['total'],
            loc,
            profile_json['seller']['registration_date'],
            profile_json['seller']['permalink'],
            profile_json['seller']['seller_reputation']['level_id']
        )
        self.cur.execute('''insert into profiles (id,name,number_prods,qnt_vendas,loc,date_registro,permalink,level_id)
         values(?,?,?,?,?,?,?,?)''', (
            data
        ))
        self.con.commit()

    def check_profile(self, profile_json: dict):
        print(json.dumps(profile_json, indent=2))
        self.cur.execute('''select * from profiles where id=?''', (profile_json['seller']['id'],))
        if self.cur.fetchone() is None:
            self.create_profile(profile_json)
        return

    def insert_basic_info_prods(self, profile_json: dict):
        # print(json.dumps(profile_value,indent=2))
        # exit()
        for prod in profile_json['results']:
            try:
                self.cur.execute('''insert into prods (
                id,price,title,stock,qntSales,createDate,permalink,thumb,listing_type_id,fk_profiles
                )
                values
                (?,?,?,?,?,?,?,?,?,?)''', (
                    prod['id'],
                    prod['price'],
                    prod['title'],
                    prod['available_quantity'],
                    prod['sold_quantity'],
                    datetime.now(),
                    prod['permalink'],
                    prod['thumbnail'],
                    prod['listing_type_id'],
                    profile_json['seller']['id']
                ))
            except Exception as e:
                print(e)
                print(f'{prod["title"]}')
        self.con.commit()

    def sync_info_prods(self, profile_info_input):
        profile_info_id = profile_info_input['seller']['id']
        # None or more than 1 day?
        # if more than 1 day, append task list
        self.cur.execute('''select * from prods where fk_profiles = ? and last_updated = ?''',
                         (profile_info_id, 'None',))
        for i in self.cur.fetchall():
            print(i)
            prod_id, price, name, stock, qntSales, createDate, permalink, thumb, listing_type_id, fk_profiles, last_updated = i
            print(permalink)
            self.update_info_prods(permalink)
            break

    def update_info_prods(self, permalink):
        if 'https://produto' in permalink:
            with requests.Session() as se:
                res=se.get(permalink)
                soup=BeautifulSoup(res.text,'html.parser')
                price=soup.find('meta',{'itemprop':'price'})
                print(price['content'])

                qnt_sales=soup.find('span',{'class':'ui-pdp-subtitle'}).text
                qnt_sales=qnt_sales.split(' ')[4]
                qnt_sales=re.sub(r'\+','',qnt_sales)
                qnt_sales=re.sub(r'mil','000',qnt_sales)
                print(qnt_sales)

                stock=soup.find('span','ui-pdp-buybox__quantity__available')
                stock=stock.text
                stock=stock.strip('()')
                stock=stock.split(' ')[0]
                print(stock)

                last_updated=datetime.now()
                print(last_updated)


                # price=soup.find('div',{'class':'ui-pdp-price__second-line'})
                # price_str=price.find('span',{'class':'andes-visually-hidden'}).text
                # split_price_str=price_str.split(' ')
                # print(price)
                # if len(split_price_str) <= 2:
                #     print(f'{split_price_str[0]}')
                # else:
                #     print(f'{split_price_str[0]}.{split_price_str[3]}')
        else:
            # normal page product, no catalogo
            pass
if __name__ == '__main__':
    mysql = Sql()

    profile = '43603886'
    with requests.Session() as s:
        profile_info = user_prods(s, profile)
        # print(user_list_items(s,profile))
    # mysql.check_profile(profile_info)
    # mysql.insert_basic_info_prods(profile_info)
    mysql.sync_info_prods(profile_info)
