import os
import time
import json
import shutil
import requests
import urllib.parse
import logging.handlers

from tqdm import tqdm
from openpyxl import Workbook
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import UnexpectedAlertPresentException


# 전역변수
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'}
driver_loc = './chromedriver.exe'
input_data = list()
driver = webdriver.Chrome(driver_loc)


def load_setting():
    path_dir = './setting'
    file_list = os.listdir(path_dir)
    file_list.sort()

    for iter in file_list:
        file_name = '{0}/{1}'.format(path_dir, iter)
        with open(file_name, 'r') as f:
            temp_dict = {'keywords': list(), 'blacklist': list()}

            lines = f.readlines()
            now = 'url'
            for line in lines:
                if line[0] == '#':
                    if 'url' in line.strip():
                        now = 'url'
                    elif 'id / pw' in line.strip():
                        now = 'account'
                    elif 'keyword' in line.strip():
                        now = 'keyword'
                    elif 'blacklist' in line.strip():
                        now = 'blacklist'
                    elif 'excel' in line.strip():
                        now = 'excel'
                else:
                    if now == 'url':
                        temp_dict['url'] = line.strip()
                    elif now == 'account':
                        temp_dict['id'] = line.split(' ')[0].strip()
                        temp_dict['pw'] = line.split(' ')[1].strip()
                    elif now == 'keyword':
                        temp_dict['keywords'].append(line.strip())
                    elif now == 'blacklist':
                        temp_dict['blacklist'].append(line.strip())
                    elif now == 'excel':
                        temp_dict['excel_name'] = line.strip()
            input_data.append(temp_dict)






def _get_now_time():
    now = time.localtime()
    s = "{0}.{1:0>2}.{2:0>2}. {3:0>2}:{4:0>2}:{5:0>2}".format(now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec)
    return s


def make_excel(data, file_name):
    FILENAME = './result/' + file_name + ".xlsx"
    wb = Workbook()
    ws = wb.worksheets[0]
    header = ['작성자', '댓글', '카테고리명', '제목명', '내용', '게시글 URL', '작성 시각', '수집 시각']
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 50
    ws.column_dimensions['E'].width = 70
    ws.column_dimensions['F'].width = 55
    ws.column_dimensions['G'].width = 20
    ws.column_dimensions['H'].width = 20
    ws.append(header)

    for iter in data:
        if iter['ok'] == 'error':
            continue
        author = '{0}({1})'.format(iter['nickname'], iter['author_id'])
        if len(iter['comments']) == 0:
            has_comment = '0개'
        else:
            has_comment = '{}개'.format(iter['comment_counts'])
        temp_list = [author, has_comment, iter['category'], iter['title'], iter['content'], iter['url'], iter['time'], iter['timestamp']]
        ws.append(temp_list)

    wb.save(FILENAME)
    logger.info('[COMPLETE] {} 엑셀 파일 생성 완료.'.format(file_name))


def login(id, pw):
    for i in range(1, 16):
        logger.info("[ATTEMPT] 로그인 시도 중... ({}/15)".format(i))
        driver.get('https://nid.naver.com/nidlogin.login')
        driver.implicitly_wait(3)
        driver.find_element_by_xpath('//*[@id="id"]').send_keys(id.strip())
        driver.implicitly_wait(3)
        driver.find_element_by_xpath('//*[@id="pw"]').send_keys(pw.strip())
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


def get_club_id(cafe_url):
    html = requests.get(cafe_url, headers=headers).text
    bs = BeautifulSoup(html, 'lxml')
    return str(bs.find('input', {'name': 'clubid'})['value'])


def get_page_len(club_id, keyword, count=1):
    page_len = count

    # 검색
    encoded_keyword = str(str(keyword).encode('euc-kr'))[1:].replace('\\x', '%')
    url = 'https://cafe.naver.com/ArticleSearchList.nhn?search.clubid={0}&search.searchdate=all&search.searchBy=1&search.query={1}&search.sortBy=date&userDisplay=50&search.media=0&search.option=0&search.page={2}'.format(
        club_id, encoded_keyword, str(page_len))
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
                page_len = get_page_len(club_id, keyword, page_len + 1)
        else:
            page_len += 1

    return page_len


def get_post_ids(club_id, keyword, pages, history_ids=list()):
    post_ids = list()

    for page in range(1, pages + 1):
        # 검색
        encoded_keyword = str(str(keyword).encode('euc-kr'))[1:].replace('\\x', '%')
        url = 'https://cafe.naver.com/ArticleSearchList.nhn?search.clubid={0}&search.searchdate=all&search.searchBy=1&search.query={1}&search.sortBy=date&userDisplay=50&search.media=0&search.option=0&search.page={2}'.format(club_id, encoded_keyword, str(page))
        driver.get(url)
        driver.implicitly_wait(3)
        driver.switch_to.frame(driver.find_element_by_id('cafe_main'))
        html = driver.page_source
        bs = BeautifulSoup(html, 'lxml')

        trs = bs.find('form', {'name': 'ArticleList'}).find('table').find_all('tr', {'align': 'center'})
        for tr in trs:
            post_id = tr.find('span', class_='list-count').get_text()
            if post_id in history_ids:
                continue
            else:
                post_ids.append(post_id)

    return post_ids


def get_comments(url, club_id, post_id):
    all_comment = []
    url_dict = dict()
    url_dict['url'] = url

    # Make Json URL
    try:
        article_attr = 'search.clubid={0}&search.menuid=26&search.articleid={1}&search.lastpageview=true&lcs=Y'.format(club_id, post_id)
        json_chk_url = 'https://cafe.naver.com/CommentView.nhn?' + article_attr

        temp_data = requests.get(json_chk_url).text

        try:
            comment_data = json.loads(temp_data)
            url_chk = 0
        except:
            driver.get(json_chk_url)
            bs4 = BeautifulSoup(driver.page_source, 'lxml')
            comment_data = json.loads(bs4.get_text())
            url_chk = 1

        # Count comment pages
        total = comment_data['result']['totalCount']
        cnt_per_page = comment_data['result']['countPerPage']
        page_count = total / cnt_per_page
        if total % cnt_per_page != 0:
            page_count += 1
        page_count = int(page_count)

        json_url_list = []
        for num in range(1, page_count + 1):
            json_url_list.append(
                'https://cafe.naver.com/CommentView.nhn?search.page={}&'.format(num) + article_attr)

    except UnexpectedAlertPresentException:
        alert = driver.switch_to.alert()
        logger.info("[PASS] ({}) {}".format(url.strip(), alert.text))
        alert.accept()
        driver.implicitly_wait(3)
        return list()

    # Get comment
    comment_list = []
    for json_url in json_url_list:
        comment_data = {}
        if url_chk == 0:
            temp_data = requests.get(json_url).text
            comment_data = json.loads(temp_data)
        elif url_chk == 1:
            driver.get(json_url)
            bs4 = BeautifulSoup(driver.page_source, 'lxml')
            comment_data = json.loads(bs4.get_text())

        for comment in comment_data['result']['list']:
            temp_comment = {}
            if comment['deleted']:
                continue
            if comment['articleWriter']:
                continue
            temp_comment['author_id'] = comment['writerid']
            temp_comment['time'] = comment['writedt']
            temp_comment['comment'] = comment['content']
            comment_list.append(temp_comment)

    url_dict['comments'] = comment_list
    all_comment.append(url_dict)
    return all_comment


def get_post_info(cafe_url, club_id, post_id, blacklist=None):
    result = dict()
    url = 'https://cafe.naver.com/ArticleRead.nhn?clubid={0}&page=10&userDisplay=50&inCafeSearch=true&searchBy=1&query=vs&includeAll=&exclude=&include=&exact=&searchdate=all&media=0&sortBy=date&articleid={1}&referrerAllArticles=true'.format(
        club_id, str(post_id))
    try:
        html = requests.get(url, headers=headers).text
        bs = BeautifulSoup(html, 'lxml')
        temp = bs.find('td', class_='p-nick').find('a').get('onclick')
    except Exception:
        driver.get(url)
        driver.implicitly_wait(3)
        driver.switch_to.frame(driver.find_element_by_id('cafe_main'))
        bs = BeautifulSoup(driver.page_source, 'lxml')
        temp = bs.find('td', class_='p-nick').find('a').get('onclick')

    # 작성자 정보
    result['author_id'] = temp.split(',')[1].replace("'", '').strip()
    result['nickname'] = temp.split(',')[3].replace("'", '').strip()

    # 블랙리스트 포함 여부 확인
    if result['author_id'] in blacklist:
        result['ok'] = 'error'
        return result

    # 글 정보 (제목 & 카테고리, 작성시간)
    temp2 = bs.find('div', class_='tit-box').find_all('table')
    result['title'] = temp2[0].find('span', class_='b m-tcol-c').get_text().strip()
    result['category'] = temp2[0].find('a', class_='m-tcol-c').get_text().strip()
    result['time'] = temp2[1].find('td', class_='date').get_text().strip()

    # 글 내용
    result['url'] = cafe_url + '/' + str(post_id)
    result['content'] = bs.find('div', class_='tbody m-tcol-c').get_text().replace('\xa0', '').strip()

    # 댓글 수집
    result['comments'] = get_comments(result['url'], club_id, post_id)
    result['comment_counts'] = len(result['comments'])

    # 기타 수집용 정보
    result['timestamp'] = str(_get_now_time())
    result['ok'] = 'success'

    return result


def _get_history(club_id):
    file_name = './history/{0}.json'.format(club_id)
    try:
        with open(file_name, 'r') as f:
            return json.loads(f.read())
    except:
        return list()


def _make_history(club_id, post_ids):
    file_name = './history/{0}.json'.format(club_id)
    with open(file_name, 'w') as f:
        json.dump(post_ids, f)


if __name__ == '__main__':
    if not os.path.exists('./setting'):
        os.mkdir('./setting')
    if not os.path.exists('./result'):
        os.mkdir('./result')
    if not os.path.exists('./history'):
        os.mkdir('./history')

    # LOGGER
    logger = logging.getLogger('notice')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('[SYSTEM] %(asctime)s :: %(message)s')
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)

    load_setting()

    # Main loop
    for data in input_data:
        result_data = list()
        post_ids_list = list()

        login(data['id'], data['pw'])
        club_id = get_club_id(data['url'])
        logger.info('[SYSTEM] 현재 cafe : {}'.format(data['url']))
        history = _get_history(club_id)
        logger.info('[SYSTEM] History 로딩 완료.')

        for keyword in data['keywords']:
            logger.info('[SYSTEM] 게시글 목록 수집 시작.')
            page_len = get_page_len(club_id, keyword)
            post_ids = get_post_ids(club_id, keyword, page_len, history)
            post_ids_list.extend(post_ids)

            logger.info('[SYSTEM] 게시글 상세 데이터 수집 시작.')
            for post_id in tqdm(post_ids):
                try:
                    result_data.append(get_post_info(data['url'], club_id, post_id, blacklist=data['blacklist']))
                except:
                    continue

        make_excel(result_data, data['excel_name'])
        _make_history(club_id, post_ids_list.extend(history))

    driver.quit()
