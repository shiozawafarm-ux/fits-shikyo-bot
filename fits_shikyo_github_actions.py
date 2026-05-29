import io
import os
import json
import time
import datetime as dt
import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

# --- 設定（GitHubのSecretsから読み込み） ---
USER_ID = os.environ.get("FITS_ID")
USER_PW = os.environ.get("FITS_PW")
GAS_URL = os.environ.get("GAS_URL")

# --- 関数の定義 ---

def upload_to_sheets(df):
    """取得したデータをGAS経由でスプレッドシートへ送信"""
    if df.empty:
        print("No data to upload.")
        return
    
    # データをJSON形式に変換（日付などは文字列にする）
    # fillna("")で欠損値を空文字にし、すべての値をリスト形式に変換
    data = df.fillna("").astype(str).values.tolist()
    
    try:
        response = requests.post(GAS_URL, data=json.dumps(data), timeout=30)
        if response.text == "Success":
            print("Successfully uploaded to Google Sheets.")
        else:
            print(f"Upload failed: {response.text}")
    except Exception as e:
        print(f"Error during upload: {e}")

def select_ymd(driver, target_date):
    date_y_dd = driver.find_element(By.NAME, "cmb_selectYear")
    Select(date_y_dd).select_by_value(str(target_date.year))

    date_d_dd = driver.find_element(By.NAME, "cmb_selectDay")
    Select(date_d_dd).select_by_value(str(target_date.day).zfill(2))
    
    date_m_dd = driver.find_element(By.NAME, "cmb_selectMonth")
    Select(date_m_dd).select_by_value(str(target_date.month).zfill(2))

def click_go_search(driver):
    driver.find_element(By.NAME, "GoSearch").click()
    time.sleep(2)

def send_keyword(driver, search_keyword):
    search_bar = driver.find_element(By.NAME, "searchkey")
    search_bar.send_keys(search_keyword)

# --- メイン処理 ---

# ヘッドレスモードの設定（クラウド実行に必須）
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(options=chrome_options)

try:
    # Fitsアクセス
    driver.get('https://fits.faj.co.jp/fits5/index.cfm')

    # ログイン
    driver.find_element(By.NAME, "fitsuser_id").send_keys(USER_ID)
    driver.find_element(By.NAME, "fitspasswd").send_keys(USER_PW)
    driver.find_element(By.NAME, "Login").click()
    time.sleep(3)

    # 商品市況ページへ
    driver.find_element(By.LINK_TEXT, "商品市況").click()
    time.sleep(3)

    # 自動実行時の対象日付（今日）
    target_date = dt.date.today()
    keyword = ""

    # 検索条件入力
    select_ymd(driver, target_date)
    send_keyword(driver, keyword)
    
    # 2回クリック
    for _ in range(2):
        click_go_search(driver)

    # データ抽出
    try:
        table = driver.find_element(By.CSS_SELECTOR, "body > form > table > tbody > tr:nth-child(2) > td > table > tbody > tr > td > table > tbody > tr:nth-child(3) > td > table > tbody > tr > td:nth-child(3) > table")
        html = table.get_attribute('outerHTML')
        
        # StringIOを使ってFutureWarningを回避
        data = pd.read_html(io.StringIO(html))
        df = pd.DataFrame(data[0])
        
        # 不要なヘッダー行の削除
        df = df.drop(0)
        
        # 日付列を追加（9番目の列として日付を挿入）
        df[8] = target_date.strftime('%Y-%m-%d')
        
        # GASへ送信
        upload_to_sheets(df)
        print(f"Process completed for {target_date}")
        
    except Exception as e:
        # テーブルがない場合（休場日など）はエラーを出さずに終了
        print(f"No table found for {target_date}. It might be a holiday.")

finally:
    driver.quit()
