import pickle
import psycopg2
import requests
from dataclasses import dataclass
from bs4 import BeautifulSoup
import re


def get_profile_id(url_input):
    with requests.Session() as s_get_profile_id:
        res = s_get_profile_id.get(url_input)
        if 'Ver todas' not in res.text:
            print('erro no get perfil')
            return
        soup = BeautifulSoup(res.text, 'html.parser')
        js = soup.find_all('script')
        bomdia = re.findall(r'\"user_id\":\d+', res.text)
        if bomdia is None:
            return
        id_profile: str = bomdia[0].split(':')[1]
        return id_profile


@dataclass
class ML:
    id_prod: list


def parser_page(link, session, temp_prods_list):
    prod_profile = session.get(link)
    soup_profile = BeautifulSoup(prod_profile.text, 'html.parser')
    soup_section = soup_profile.find('section', {
        'class': 'ui-search-results ui-search-results--without-disclaimer shops__search-results'})
    soup_links = soup_section.find_all('a', {
        'class': 'ui-search-item__group__element shops__items-group-details ui-search-link'})
    for i in soup_links:
        temp_prods_list.append(i['href'])
    if 'Seguinte</span>' in prod_profile.text:
        try:
            next_anchor = soup_profile.find('a', {'title': 'Seguinte'})
            next_link = next_anchor['href']
            parser_page(next_link, session, temp_prods_list)
        except Exception as e:
            print(e)
            print('last page')


if __name__ == '__main__':
    url = 'https://www.mercadolivre.com.br/perfil/PAULISTAPAPELARIA'
    with requests.Session() as s:
        profile_id = get_profile_id(url)
        url_profile = f'https://lista.mercadolivre.com.br/_CustId_{profile_id}'
        all_prods_links = []
        parser_page(url_profile, s, all_prods_links)
        with open('prods_links_list.pickle', 'wb') as f:
            pickle.dump(all_prods_links, f)
