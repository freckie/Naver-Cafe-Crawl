import os
import time
import json
import shutil
import requests
import urllib.parse
import logging.handlers
from bs4 import BeautifulSoup
from selenium import webdriver


# 전역변수
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'}
accounts = {'id': 'rlaaudgu2', 'pw': 'kimh1785*'}
driver_loc = './chromedriver.exe'
driver = webdriver.Chrome(driver_loc)


def login(account):
    for i in range(1, 16):
        logger.info("[ATTEMPT] 로그인 시도 중... ({}/15)".format(i))
        driver.get('https://nid.naver.com/nidlogin.login')
        driver.implicitly_wait(3)
        driver.find_element_by_xpath('//*[@id="id"]').send_keys(accounts['id'].strip())
        driver.implicitly_wait(3)
        driver.find_element_by_xpath('//*[@id="pw"]').send_keys(accounts['pw'].strip())
        driver.implicitly_wait(3)
        driver.find_element_by_xpath('//*[@id="frmNIDLogin"]/fieldset/input').click()
        driver.implicitly_wait(3)

        if driver.current_url == 'https://www.naver.com/':
            break

    if driver.current_url == 'https://www.naver.com/':
        logger.info("[COMPLETE] 로그인 성공")
    else:
        logger.info("[DEBUG] 직접 로그인해주세요...")
        while True:
            login_chk = input('완료 시 입력하세요 (완료: 1) :: ')
            if login_chk == '1':
                break
            else:
                logger.info("[DEBUG] 다시 입력해주세요...")


def get_page_len(keyword, count=1):
    page_len = count

    # 검색
    encoded_keyword = str(str(keyword).encode('euc-kr'))[1:].replace('\\x', '%')
    url = 'https://cafe.naver.com/ArticleSearchList.nhn?search.clubid=28866679&search.searchdate=all&search.searchBy=1&search.query={0}&search.sortBy=date&userDisplay=50&search.media=0&search.option=0&search.page={1}'.format(
        encoded_keyword, str(page_len))
    driver.get(url)
    driver.implicitly_wait(3)
    driver.switch_to.frame(driver.find_element_by_id('cafe_main'))
    html = driver.page_source
    bs = BeautifulSoup(html, 'lxml')

    # 검색 페이지 수 수집
    page_tds = bs.find('div', class_='prev-next').find('table').find('tr').find_all('td')
    for td in page_tds:
        if td.has_attr('class'):
            if 'pgL' in td['class']:
                continue
            elif 'pgR' in td['class']:
                page_len = get_page_len(keyword, page_len + 1)
        else:
            page_len += 1

    return page_len


def get_post_ids(keyword, pages):
    post_ids = list()

    for page in range(1, pages + 1):
        # 검색
        encoded_keyword = str(str(keyword).encode('euc-kr'))[1:].replace('\\x', '%')
        url = 'https://cafe.naver.com/ArticleSearchList.nhn?search.clubid=28866679&search.searchdate=all&search.searchBy=1&search.query={0}&search.sortBy=date&userDisplay=50&search.media=0&search.option=0&search.page={1}'.format(encoded_keyword, str(page))
        driver.get(url)
        driver.implicitly_wait(3)
        driver.switch_to.frame(driver.find_element_by_id('cafe_main'))
        html = driver.page_source
        bs = BeautifulSoup(html, 'lxml')

        trs = bs.find('form', {'name': 'ArticleList'}).find('table').find_all('tr', {'align': 'center'})
        for tr in trs:
            post_ids.append(tr.find('span', class_='list-count').get_text())

    return post_ids


def get_post_info(post_code):
    result = dict()

    url = 'https://cafe.naver.com/ArticleRead.nhn?clubid=28866679&page=10&userDisplay=50&inCafeSearch=true&searchBy=1&query=vs&includeAll=&exclude=&include=&exact=&searchdate=all&media=0&sortBy=date&articleid={0}&referrerAllArticles=true'.format(str(post_code))
    html = requests.get(url, headers=headers).text
    bs = BeautifulSoup(html, 'lxml')

    # 작성자 정보
    temp = bs.find('td', class_='p-nick').find('a').get('onclick')
    result['author_id'] = temp.split(',')[1].replace("'", '').strip()
    result['nickname'] = temp.split(',')[3].replace("'", '').strip()

    # 글 정보 (제목 & 카테고리, 작성시간)
    temp2 = bs.find('div', class_='tit-box').find_all('table')
    result['title'] = temp2[0].find('span', class_='b m-tcol-c').get_text().strip()
    result['category'] = temp2[0].find('a', class_='m-tcol-c').get_text().strip()
    result['time'] = temp2[1].find('td', class_='date').get_text().strip()

    # 글 내용
    result['url'] = 'https://cafe.naver.com/playbattlegrounds/' + str(post_code)
    result['content'] = bs.find('div', class_='tbody m-tcol-c').get_text().replace('\xa0', '').strip()

    return result


if __name__ == '__main__':
    # LOGGER
    logger = logging.getLogger('notice')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('[SYSTEM] %(asctime)s :: %(message)s')
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)

    print(get_post_info('2880884'))

    # 메인 루프
    login(accounts)
    len = get_page_len('vss')
    logger.info('페이지 수 수집 완료.')
    print(get_post_ids('vss', len))
    logger.info('글 ID 수집 완료.')
