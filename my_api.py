import time


def get_count_json_url(total, cnt_per_page):
    count = total / cnt_per_page
    if total % cnt_per_page != 0:
        count += 1
    return int(count)


def get_now_time():
    now = time.localtime()
    s = "{0}.{1:0>2}.{2:0>2}. {3:0>2}:{4:0>2}:{5:0>2}".format(now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec)
    return s