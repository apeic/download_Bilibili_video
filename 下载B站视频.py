import tkinter as tk
import requests
import re   
from lxml import etree
import time
import os
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36'
}

picture = None
start_var = None
end_var = None


def get_download_url(base_url):
    ps = check_p(base_url)
    n = len(ps)
    down_list = []
    if 'no' in ps:
        down_list.append(parse_page(base_url))
    else:
        bv = re.search(r'BV\w+', base_url).group()
        for i in ps:
            url = base_url + '?p=%d' % i
            # print(url)
            print('\r正在加载P%d链接....' % i, end='')
            down_list.append(parse_page(url, p=True, bv=bv, i=int(i)))
        print()
    return down_list


def parse_page(url, p=False, bv=-1, i=-1):
    num = 1
    mp4_list = ['80', '64', '32', '16']
    mp3_list = ['30280', '30232', '30216']
    res = requests.get(url, headers=headers)
    text = res.text
    html = etree.HTML(text)
    title = html.xpath("//span[@class='tit' or @class='tit tr-fix']/text()")
    if not len(title):
        title = '未命名%d' % num
        num += 1
    else:
        title = title[0]
    if p:
        api_url = 'https://api.bilibili.com/x/player/pagelist?bvid=' + bv + '&jsonp=jsonp'
        res = requests.get(api_url, headers=headers)
        text_json = json.loads(res.text)
        ptitle = text_json['data'][i - 1]['part']
        title = title + '(P%d ' % i + ptitle + ')'
    title = re.sub(r'[\s\\/:\*\?"<>|]', '', title)
    mp4_list = list(map(lambda x: '{"id":' + x + ',"baseUrl":"(.*?)",', mp4_list))
    mp3_list = list(map(lambda x: '{"id":' + x + ',"baseUrl":"(.*?)",', mp3_list))
    mp3 = match_url(mp3_list, text)
    if mp3 == -1:
        videos = get_old_video_url(url)
        if videos is not None:
            return [title, 1, videos]
        else:
            return [-1, -1, -1]
    mp4 = match_url(mp4_list, text)
    return [title, mp3, mp4]


def get_url(rid, day, type, arc_type):  # 获取排行榜视频链接
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36',
        'Referer': 'https://www.bilibili.com/ranking/all/1/0/1'
    }
    if arc_type == '1' and day == '30':
        print('近期投稿没有月排行，请重新选择')
        return []
    url = 'https://api.bilibili.com/x/web-interface/ranking?rid=%s&day=%s&type=%s&arc_type=%s&jsonp=jsonp&callback=' \
          % (rid, day, type, arc_type)
    res = requests.get(url, headers=headers)
    text_json = json.loads(res.text)
    url_list = text_json['data']['list']
    base_url = 'https://www.bilibili.com/video/'
    bvs = list(url_list[i]['bvid'] for i in range(100))
    hrefs = list(map(lambda x: base_url + x, bvs))
    return hrefs


def get_old_video_url(url):
    res = requests.get(url, headers=headers)
    urls_ = re.findall(r'"url":"(.*?)","backup_url', res.text)
    return urls_


def match_url(conditions, text):
    for condition in conditions:
        result = re.search(condition, text)
        if result:
            return result.group(1)
    else:
        return -1


def downloader(title, mp3, mp4):
    is_exists = os.path.exists('小破站/temp')
    if not is_exists:
        os.mkdir('小破站/temp')
    # if os.path.exists('小破站/' + title + '.mp4'):
    #     print(title + '已存在')
    #     return
    start = time.time()
    if mp3 != 1:
        down(mp3, title + '_temp', 'mp3')
        down(mp4, title + '_temp', 'mp4')
        mainmux(title)
    else:
        for index, video in enumerate(mp4):
            temp_title = title + 'temp_' + str(index)
            with open('小破站/temp/' + title + '.txt', 'a') as fp:
                data = 'file ' + "'" + temp_title + ".flv'\n"
                fp.write(data)
            down(video, temp_title, 'flv')
        merge_video(title)
    end = time.time()
    print('\n下载完成！用时%.2f秒' % (end - start))


def down(url, title, type):
    host = re.search(r'http://(.*?)/', url).group(1)
    download_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 SE 2.X MetaSr 1.0',
        'Referer': 'https://www.bilibili.com/video/av6499012',
        'host': host
        # 'Origin': 'https://www.bilibili.com',
        # 'Accept': '*/*',
        # 'Accept-Encoding': 'gzip, deflate, sdch, br',
        # 'Accept-Language': 'zh-CN,zh;q=0.8'
    }
    res = requests.get(url, headers=download_headers, stream=True)
    chunk_size = 1024
    content_size = int(res.headers['content-length'])
    size = 0
    if res.status_code == 200:
        # if type == 'mp4':
        #     print()
        print(title + '.' + type + '文件大小 ：%0.2f MB' % (content_size / chunk_size / 1024))
        if type == 'flv':
            fp = open('小破站/temp/' + title + '.' + type, 'wb')
        else:
            fp = open('小破站/temp/' + title + '.' + type, 'wb')
        for data in res.iter_content(chunk_size=chunk_size):
            fp.write(data)
            size += len(data)
            print('\r' + '[下载进度]:%s%.2f%%' % ('>' * int(size * 50 / content_size), float(size / content_size * 100)),  end='')
        print()
        fp.close()


def check_p(url):
    text = requests.get(url, headers=headers).text
    lis = etree.HTML(text).xpath("//ul[@class='list-box']/li")
    n = len(lis)
    if n > 0:
        print('='*30 + '\n该视频总共有%dP，请选择：\n1、全部下载     2、自定义P数' % n)
        try:
            flag = eval(input())
        except:
            print('输入有误，请重试！')
            return []
        if flag == 2:
            print('请输入你要下载的P（以空格分隔）')
            ps = input().strip().split(' ')
            ps = [int(p) for p in ps if 0 < int(p) <= n]
            print('=' * 30)
            return ps
        print('='*30)
        return [i for i in range(1, n + 1)]
    return ['no']


def mainmux(title):
    vedioinput = title + '_temp.mp4'
    audioinput = title + '_temp.mp3'
    output = title + '.mp4'
    command = r'ffmpeg -loglevel quiet -i '+'"'+vedioinput+'"'+' -i '+'"'+audioinput+'"'+' -c:v copy -map 0:v:0 -c:a copy -map 1:a:0 -y '+'"../'+output+'"'
    # print(command)
    delete = 'del "' + vedioinput + '" "' + audioinput + '"'
    print('正在混流中。。。')
    os.system('cd 小破站/temp && ' + command)
    #  + ' && ' + delete
    time.sleep(1)
    os.system('cd 小破站/temp && ' + delete)
    print('混流完成！！！', end='')


def merge_video(title):
    output = title + '.flv'
    command = r'ffmpeg -f concat -safe 0 -loglevel quiet -i ' + title + '.txt ' + '-c copy ' + '../' + output
    delete = 'del *.flv ' + title + '.txt"'
    print('正在合并视频中。。。')
    os.system('cd 小破站/temp && ' + command)
    os.system('cd 小破站/temp && ' + delete)
    print('合并完成！！！', end='')


def downlowd_picture(bv):
    url = 'https://api.bilibili.com/x/web-interface/view?bvid=' + bv
    text = requests.get(url, headers=headers).text
    text_json = json.loads(text)
    title = text_json['data']['title']
    title = re.sub(r'[\\/:\*\?"<>|]', '', title)
    pic_url = text_json['data']['pic']
    ext = os.path.splitext(pic_url)
    title += ext[1]
    path = '小破站/' + title
    # if os.path.exists(path):
    #     print(path + '已存在')
    #     return
    with open(path, 'wb') as fp:
        fp.write(requests.get(pic_url, headers=headers).content)
    print(path + '下载完成！')


def method_bv(bv):
    base_url = 'https://www.bilibili.com/video/'
    url = base_url + bv
    if picture.get() == 1:
        downlowd_picture(bv)
    elif picture.get() == 2:
        downlowd_picture(bv)
        return
    down_list = get_download_url(url)
    for dl in down_list:
        title, mp3, mp4 = dl
        if mp3 != -1 and mp4 != -1:
            downloader(title, mp3, mp4)
            time.sleep(1)
        else:
            print('此视频可能无法下载，抱歉。')


def method_rank(a, b, c, d):
    # area = ['all/', 'origin/']
    time_ = ['0', '1']
    duration = ['1', '3', '7', '30']
    zone = ['0', '1', '168', '3', '129', '4', '36', '188', '160', '119', '155', '5', '181']
    # base_url = 'https://www.bilibili.com/ranking/'
    # full_url = base_url + area[a] + zone[b] + time[c] + duration[d]
    urls = get_url(zone[b], duration[d], str(a), time_[c])
    num = 0
    fail = []
    for url in urls:
        bv = re.search(r'BV\w+', url).group()
        if picture.get() == 1:
            downlowd_picture(bv)
        elif picture.get() == 2:
            downlowd_picture(bv)
            continue
        num += 1
        down_list = get_download_url(url)
        for dl in down_list:
            title, mp3, mp4 = dl
            if mp3 != -1 and mp4 != -1:
                downloader(title, mp3, mp4)
            else:
                fail.append(num)
        time.sleep(1)
    if len(fail):
        print('全部下载完成！第' + str(fail) + '个下载失败！\n')
    else:
        print('全部下载完成！')


def method_up(up):
    res = requests.get('https://search.bilibili.com/all?keyword=' + up)
    html = etree.HTML(res.text)
    li = html.xpath("//li[@class='user-item']")
    start = start_var.get().strip()
    end = end_var.get().strip()
    if len(li) == 0:
        print('未找到该up，请核对之后重试！')
        return
    else:
        li = li[0]
        up_name = li.xpath(".//div[@class='headline']//a/@title")[0]
        url = 'https:' + li.xpath(".//a[@class='video-more']/@href")[0]
        print('=' * 30)
        flag = input('你是否要下载 【%s】 %s 到 %s 的视频？(y/n)\n' % (up_name, start, end))
        flag = flag.lower()
        if flag == 'y' or flag == 'yes':
            mid = re.search(r'\d+', url).group()
            bvs = get_video_urls(mid, start, end)
            for bv in bvs:
                method_bv(bv)
        else:
            print('取消下载！')


def get_video_urls(mid, start, end):
    s = time.strptime(start, "%Y-%m-%d")
    e = time.strptime(end, "%Y-%m-%d")
    s = int(time.mktime(s))
    e = int(time.mktime(e))
    if s > e:
        s, e = e, s
    i = 1
    stop = False
    bvs = []
    while True:
        url = 'https://api.bilibili.com/x/space/arc/search?mid=%s&ps=30&tid=0&pn=%d&keyword=&order=pubdate&jsonp=jsonp' % (mid, i)
        res = requests.get(url, headers=headers)
        info = res.text
        info_json = json.loads(info)
        vlist = info_json['data']['list']['vlist']
        count = info_json['data']['page']['count']
        for v in vlist:
            created = v['created']
            title = v['title']
            if s <= created <= e:
                print('\r正在加载 %s 视频下载地址' % title, end='')
                bvid = v['bvid']
                bvs.append(bvid)
            elif created < s or created < 1519833600:   # 2018/3/1 时间戳 1519833600.0
                stop = True
                break
            else:
                continue
        if stop:
            break
        if i == count // 30 + 1:
            break
        i += 1
    print("\n全部加载完成！开始下载！\n " + '='*30)
    return bvs


def gui():
    global picture, start_var, end_var

    window = tk.Tk()
    window.title('下载B站视频')
    window.geometry('750x480')

    a = tk.IntVar()
    a.set(1)
    b = tk.IntVar()
    b.set(0)
    c = tk.IntVar()
    c.set(0)
    d = tk.IntVar()
    d.set(0)
    tk.Label(window, fg='red', text='下载过程中，此页面会未响应，下载完就好啦！', font=('微软雅黑', 15)).place(x=230, y=10)
    tk.Label(window, text='下载排行榜所有视频', font=('微软雅黑', 15)).place(x=5, y=10)
    frame1 = tk.Frame(bd=1, width=100, height=80, relief=tk.GROOVE).place(x=5, y=50)
    tk.Radiobutton(frame1, text='全站榜', variable=a, value=1, font=('微软雅黑', 15)).place(x=8, y=55)
    tk.Radiobutton(frame1, text='原创榜', variable=a, value=2, font=('微软雅黑', 15)).place(x=8, y=90)
    frame2 = tk.Frame(bd=1, width=120, height=80, relief=tk.GROOVE).place(x=150, y=50)
    tk.Radiobutton(frame2, text='全部投稿', variable=c, value=0, font=('微软雅黑', 15)).place(x=153, y=55)
    tk.Radiobutton(frame2, text='近期投稿', variable=c, value=1, font=('微软雅黑', 15)).place(x=153, y=90)
    frame3 = tk.Frame(bd=1, width=260, height=80, relief=tk.GROOVE).place(x=320, y=50)
    tk.Radiobutton(frame3, text='日排行', variable=d, value=0, font=('微软雅黑', 15)).place(x=323, y=55)
    tk.Radiobutton(frame3, text='三日排行', variable=d, value=1, font=('微软雅黑', 15)).place(x=323, y=90)
    tk.Radiobutton(frame3, text='周排行', variable=d, value=2, font=('微软雅黑', 15)).place(x=460, y=55)
    tk.Radiobutton(frame3, text='月排行', variable=d, value=3, font=('微软雅黑', 15)).place(x=460, y=90)
    frame4 = tk.Frame(bd=1, width=670, height=80, relief=tk.GROOVE).place(x=5, y=140)
    tk.Radiobutton(frame4, text='全站', variable=b, value=0, font=('微软雅黑', 15)).place(x=8, y=145)
    tk.Radiobutton(frame4, text='动画', variable=b, value=1, font=('微软雅黑', 15)).place(x=100, y=145)
    tk.Radiobutton(frame4, text='国创相关', variable=b, value=2, font=('微软雅黑', 15)).place(x=192, y=145)
    tk.Radiobutton(frame4, text='音乐', variable=b, value=3, font=('微软雅黑', 15)).place(x=320, y=145)
    tk.Radiobutton(frame4, text='舞蹈', variable=b, value=4, font=('微软雅黑', 15)).place(x=412, y=145)
    tk.Radiobutton(frame4, text='游戏', variable=b, value=5, font=('微软雅黑', 15)).place(x=504, y=145)
    tk.Radiobutton(frame4, text='科技', variable=b, value=6, font=('微软雅黑', 15)).place(x=8, y=180)
    tk.Radiobutton(frame4, text='数码', variable=b, value=7, font=('微软雅黑', 15)).place(x=100, y=180)
    tk.Radiobutton(frame4, text='生活', variable=b, value=8, font=('微软雅黑', 15)).place(x=192, y=180)
    tk.Radiobutton(frame4, text='鬼畜', variable=b, value=9, font=('微软雅黑', 15)).place(x=320, y=180)
    tk.Radiobutton(frame4, text='时尚', variable=b, value=10, font=('微软雅黑', 15)).place(x=412, y=180)
    tk.Radiobutton(frame4, text='娱乐', variable=b, value=11, font=('微软雅黑', 15)).place(x=504, y=180)
    tk.Radiobutton(frame4, text='影视', variable=b, value=12, font=('微软雅黑', 15)).place(x=596, y=180)
    picture = tk.IntVar()
    picture.set(0)

    def rank():
        method_rank(a.get(), b.get(), c.get(), d.get())

    tk.Button(window, text='下载！', font=('微软雅黑', 15), command=rank).place(x=625, y=65)

    def bv():
        bv = var.get().strip()
        method_bv(bv)
        # downlowd_picture(av)

    var = tk.StringVar()
    frame5 = tk.Frame(bd=1, width=330, height=110, relief=tk.GROOVE).place(x=5, y=230)
    tk.Label(frame5, text='下载指定bv号视频(前面带上BV~)', font=('微软雅黑', 15)).place(x=10, y=240)
    tk.Entry(frame5, textvariable=var, show=None, font=('微软雅黑', 15), width=12).place(x=15, y=285)
    tk.Button(frame5, text='下载！', font=('微软雅黑', 15), command=bv).place(x=177, y=278)

    def up():
        up_ = up_var.get().strip()
        # print(up_)
        method_up(up_)

    up_var = tk.StringVar()
    end_var = tk.StringVar()
    start_var = tk.StringVar()
    start_var.set('2018-03-01')
    end_var.set(time.strftime("%Y-%m-%d", time.localtime(time.time())))
    frame6 = tk.Frame(bd=1, width=670, height=110, relief=tk.GROOVE).place(x=5, y=350)
    tk.Label(frame6, text='下载指定up主视频', font=('微软雅黑', 15)).place(x=10, y=360)
    tk.Entry(frame6, textvariable=up_var, show=None, font=('微软雅黑', 15), width=12).place(x=15, y=405)
    tk.Button(frame6, text='下载！', font=('微软雅黑', 15), command=up).place(x=177, y=398)
    tk.Label(frame6, text='输入开始日期：', font=('微软雅黑', 15)).place(x=300, y=360)
    tk.Entry(frame6, textvariable=start_var, show=None, font=('微软雅黑', 15), width=12).place(x=440, y=360)
    tk.Label(frame6, text='输入结束日期：', font=('微软雅黑', 15)).place(x=300, y=410)
    tk.Entry(frame6, textvariable=end_var, show=None, font=('微软雅黑', 15), width=12).place(x=440, y=410)

    frame7 = tk.Frame(bd=1, width=315, height=110, relief=tk.GROOVE).place(x=360, y=230)
    tk.Radiobutton(frame7, text='下载封面图片和视频', variable=picture, value=1, font=('微软雅黑', 15)).place(x=400, y=235)
    tk.Radiobutton(frame7, text='仅下载封面图片', variable=picture, value=2, font=('微软雅黑', 15)).place(x=400, y=265)
    tk.Radiobutton(frame7, text='仅下载视频', variable=picture, value=0, font=('微软雅黑', 15)).place(x=400, y=295)
    window.mainloop()


def main():
    gui()


if __name__ == '__main__':
    main()
