#-*- coeing:utf-8 -*-
import requests
import ddddocr
from bs4 import BeautifulSoup
import pandas as pd
import dataframe_image as dfi
import matplotlib as mpl
import configparser
import urllib3
urllib3.disable_warnings()
config = configparser.ConfigParser()

config.read("config.ini")
mpl.rcParams['font.family']='MOESongUN'

ocr = ddddocr.DdddOcr(beta=True)

token = config["Line"]["token"]
headers = {
    "Authorization": "Bearer " + token
}

_url = "https://mbr.water.gov.taipei"
_waterno = config['water']['waterno']
_retry_num = 5

_Line_enable = True

proxies = {
#    'http': 'http:/127.0.0.1:8080',
#    'https': 'http://127.0.0.1:8080',
    }

def _ocr_try(session,waternum,token,retry):
    _get_validatecode = session.get(f"{_url}/Home/GetValidateCode" ,verify=False )
    _get_png = _get_validatecode.content
    res_ocr = ocr.classification(_get_png)
    print(res_ocr.upper())

    post_data = {
        "WaterNo":waternum,
        "pCode":res_ocr,
        "__RequestVerificationToken":token
    }
    _index_post = session.post(f"{_url}/WTSVCL023F/Index",data = post_data,allow_redirects=False,verify=False)
    if _index_post.status_code == 200 :
        return(_index_post.text)
    else:
        print("[Info]驗證碼 or 水號錯誤")
        print(_index_post.status_code)
        print(_index_post.text)
        print(retry)
        retry = retry - 1
        if  retry > 0:
            return(_ocr_try(session,waternum,token,retry))
        else:
            print("-None-")
            return None




def main(_number):
    s = requests.session()
    s.proxies = proxies
    s.headers.update({'User-Agent':'Mozilla/5.0 (compatible; Konqueror/4.3; Linux 2.6.31-16-generic; X11) KHTML/4.3.2 (like Gecko)'})
    _index = s.get(f"{_url}/WTSVCL023F/Index",verify=False)
    _index_soup = BeautifulSoup(_index.text,"lxml")
    _get_token = _index_soup.find("input",{"name":"__RequestVerificationToken"})["value"]
    _get_ok = _ocr_try(s,_number,_get_token,_retry_num)
    if (_get_ok):
        _get_ok_soup = BeautifulSoup(_get_ok,"lxml")
        _tmp_div = _get_ok_soup.find("div",class_="r-body")
        _title = _tmp_div.find("div",class_="accordion-bill-title")
        table = _tmp_div.find("table",{"class":"table table-bordered"})
        fields = table.select("thead > tr > th")
        _columns = []
        for _th in fields:
            _columns.append(_th.get_text())
        values = table.select("tbody > tr")
        _mylist = []
        for _tr in values:
            _td_columns = _tr.find_all("td")
            if len(_td_columns) == 4:
                _item = _td_columns[0].get_text()
                _content = _td_columns[1].get_text()
                _details = _td_columns[2].get_text()
                _money = _td_columns[3].get_text()
                _mylist.append([_item,_content,_details,_money])
            else:
                print()
        df = pd.DataFrame(_mylist,columns=_columns)
        df = df.style.apply(highlight_cell,axis=None)
        dfi.export(df,"_tmp.png",table_conversion="matplotlib")

        # Line Notify
        data = {'message':"[台北自來水]：" + _title.get_text()}
        image = open("_tmp.png","rb")
        files = {"imageFile":image}
        requests.post("https://notify-api.line.me/api/notify", headers = headers, data = data, files = files)
    else:
        print("[Warning]請確認水號是否正確..")

def highlight_cell(data, color='yellow'):
    attr = f'background-color: {color}'
    data = data.copy()
    data.iloc[:, :] = ''
    data.iloc[9, 3] = attr
    return data


if __name__ == "__main__":
    water_num  = _waterno
    main(water_num)
