# --- KONFIGURASI UTAMA ---
import json
import re
import time
import pandas as pd
import base64
import random
import logging
import os
import requests
import sys
import shutil
import glob
from datetime import datetime
from dotenv import load_dotenv
import pyotp

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- LOAD ENVIRONMENT VARIABLES ---
load_dotenv()

USERNAME = os.getenv("BPS_USERNAME")
PASSWORD = os.getenv("BPS_PASSWORD")
OTP_SECRET = os.getenv("BPS_OTP_SECRET")
# Default True jika tidak ada setting
USE_SESSION_CACHE = os.getenv("USE_SESSION_CACHE", "true").lower() == "true"

if not USERNAME or not PASSWORD:
    print("ERROR: Kredensial (BPS_USERNAME, BPS_PASSWORD) tidak ditemukan di file .env")
    sys.exit(1)

# --- SETUP LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

CUSTOM_USER_AGENT = 'Mozilla/5.0 (Linux; Android 13; itel A666LN Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.192 Mobile Safari/537.36'

DIR_URL = "https://matchapro.web.bps.go.id/dirgc"
POST_URL = 'https://matchapro.web.bps.go.id/dirgc/konfirmasi-user'

SESSION_FILE = 'session.json'
DATA_FILE = 'data.xlsx'
INPUT_DIR = 'input'
BACKUP_DIR = 'backup'

def get_driver():
    """Menginisialisasi dan mengembalikan driver Selenium."""
    logging.info("Menginisialisasi Chrome Driver...")
    chrome_options = Options()
    chrome_options.add_argument(f'user-agent={CUSTOM_USER_AGENT}')
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    # Anti-detection
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def save_session_data(driver):
    """Menyimpan data sesi (cookies & csrf) dan mengembalikan gc_token dari driver yang aktif."""
    logging.info("Mengambil cookie dan token CSRF dari browser...")
    time.sleep(2)
    cookies = driver.get_cookies()
    page_source = driver.page_source
    
    # Mencari CSRF Token
    match = re.search(r'<meta name="csrf-token" content="([^"]+)">', page_source)
    csrf_token = match.group(1) if match else None
    
    if not csrf_token:
        logging.warning("Tidak dapat menemukan token CSRF di halaman.")

    # Mencari gcSubmitToken
    logging.info("Mencari gcSubmitToken di source code halaman...")
    gc_token_match = re.search(r"gcSubmitToken\s*=\s*['\"]([^'\"]+)['\"]", page_source)
    gc_token = None
    if gc_token_match:
        gc_token = gc_token_match.group(1)
        logging.info(f"Ditemukan gcSubmitToken: {gc_token}")
    else:
        logging.warning("gcSubmitToken tidak ditemukan di halaman.")

    session_data = None
    if csrf_token:
        session_data = {'cookies': cookies, 'csrf_token': csrf_token}
        
        if USE_SESSION_CACHE:
            with open(SESSION_FILE, 'w') as f:
                json.dump(session_data, f)
            logging.info(f"Sesi berhasil diperbarui dan disimpan di '{SESSION_FILE}'.")
        else:
            logging.info("Sesi diperbarui (Tidak disimpan ke file karena USE_SESSION_CACHE=false).")
    
    return session_data, gc_token

def login_selenium(driver):
    """Melakukan proses login."""
    logging.info("Membuka halaman login...")
    driver.get(DIR_URL)
    
    # Cek jika sudah login
    if driver.current_url == DIR_URL or "Sign in" not in driver.page_source:
         try:
             WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in with SSO BPS')]")))
         except:
             logging.info("Terdeteksi sudah dalam keadaan login.")
             return

    logging.info("Melakukan klik tombol Sign in with SSO BPS...")
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in with SSO BPS')]"))).click()
    
    logging.info("Memasukkan kredensial...")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.XPATH, "//input[@type='submit']").click()
    
    # --- OTP HANDLING ---
    logging.info("Mengecek kebutuhan OTP...")
    try:
        # Cek apakah masuk ke halaman OTP (tunggu max 2 detik saja)
        # Asumsi elemen input OTP memiliki id atau name yang mengandung 'token' atau 'otp'
        otp_field = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, "//input[contains(@name, 'token') or contains(@id, 'token') or contains(@name, 'otp') or contains(@id, 'otp')]"))
        )
        logging.info("Halaman OTP terdeteksi!")

        otp_code = None
        if OTP_SECRET:
            try:
                totp = pyotp.TOTP(OTP_SECRET)
                otp_code = totp.now()
                logging.info("OTP dihasilkan otomatis dari secret key.")
            except Exception as e:
                logging.error(f"Gagal generate OTP: {e}")
        
        if not otp_code:
            print("\n" + "!"*50)
            print("MASUKKAN KODE OTP SECARA MANUAL!")
            print("!"*50 + "\n")
            # Bunyikan beep sistem agar user sadar (opsional, hanya work di beberapa terminal)
            print('\a') 
            otp_code = input("Masukkan Kode OTP: ").strip()

        logging.info("Menginput kode OTP...")
        otp_field.send_keys(otp_code)
        
        # Cari tombol submit OTP (biasanya type submit atau button dengan text Sign in/Verifikasi)
        # Kita coba enter saja di field atau cari tombol
        try:
             otp_field.submit()
        except:
             try:
                 driver.find_element(By.XPATH, "//input[@type='submit'] or //button[@type='submit']").click()
             except:
                 logging.info("Klik tombol gagal, mencoba tekan ENTER...")
                 otp_field.send_keys(Keys.ENTER)
        
    except Exception as e:
        # Jika tidak ditemukan elemen OTP atau timeout, asumsikan tidak perlu OTP atau sudah login
        logging.info(f"Info OTP: {e}")

    logging.info("Menunggu redirect ke halaman utama...")
    try:
        WebDriverWait(driver, 60).until(EC.url_contains("dirgc"))
    except Exception as e:
        logging.error(f"Gagal login (Timeout). URL terakhir: {driver.current_url}")
        raise e
    logging.info("Login berhasil.")

def get_authenticated_session_selenium():
    """Fungsi wrapper untuk login penuh. Mengembalikan (session_data, gc_token)."""
    logging.info("--- MEMULAI OTENTIKASI BARU DENGAN SELENIUM ---")
    driver = get_driver()
    try:
        login_selenium(driver)
        return save_session_data(driver)
    finally:
        if driver:
            driver.quit()

def refresh_gc_token_selenium():
    """Mencoba refresh halaman untuk dapat token baru. Login ulang jika perlu. Mengembalikan (session_data, gc_token)."""
    logging.info("--- REFRESH TOKEN DENGAN SELENIUM ---")
    driver = get_driver()
    try:
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'r') as f:
                    old_session = json.load(f)
                
                driver.get(DIR_URL) 
                for cookie in old_session.get('cookies', []):
                    try:
                        driver.add_cookie(cookie)
                    except:
                        pass
            except Exception as e:
                logging.error(f"Gagal load cookie lama: {e}")

        logging.info(f"Membuka {DIR_URL} untuk cek token...")
        driver.get(DIR_URL)
        time.sleep(3) 

        page_source = driver.page_source
        if "gcSubmitToken" in page_source:
            logging.info("gcSubmitToken ditemukan tanpa perlu login ulang.")
            return save_session_data(driver)
        else:
            logging.warning("gcSubmitToken tidak ditemukan. Kemungkinan sesi habis. Melakukan login ulang...")
            login_selenium(driver)
            return save_session_data(driver)
            
    finally:
        if driver:
            driver.quit()

def load_session_from_file():
    """Mencoba memuat sesi dari file."""
    if not USE_SESSION_CACHE:
        logging.info("USE_SESSION_CACHE=false, melewati pemuatan sesi dari file.")
        return None

    if os.path.exists(SESSION_FILE):
        logging.info(f"Mencoba memuat sesi dari file '{SESSION_FILE}'...")
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    return None

def create_backup(file_path):
    """Membuat backup file Excel ke folder backup/."""
    try:
        # Buat folder backup jika belum ada
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            logging.info(f"Folder backup dibuat: {BACKUP_DIR}")

        # Nama file backup dengan timestamp
        filename = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{os.path.splitext(filename)[0]}_{timestamp}{os.path.splitext(filename)[1]}"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)

        shutil.copy2(file_path, backup_path)
        logging.info(f"Backup file dibuat: {backup_path}")
    except Exception as e:
        logging.error(f"Gagal membuat backup untuk {file_path}: {e}")

def print_validation_rules():
    """Menampilkan aturan validasi ke console/log."""
    rules = """
    =======================================================
    ATURAN VALIDASI DATA:
    1. perusahaan_id : Wajib terisi.
    2. hasilgc       : Harus salah satu dari ['1', '3', '4', '99'].
    3. edit_nama     : Harus '0' atau '1'.
    4. edit_alamat   : Harus '0' atau '1'.
    5. Konsistensi   :
       - Jika nama_usaha terisi, edit_nama harus '1'.
       - Jika nama_usaha kosong, edit_nama harus '0'.
       - Jika alamat_usaha terisi, edit_alamat harus '1'.
       - Jika alamat_usaha kosong, edit_alamat harus '0'.
    =======================================================
    """
    print(rules)
    input("Tekan Enter untuk melanjutkan...")
    logging.info("Aturan validasi ditampilkan dan disetujui user.")

def get_input_files():
    """Mencari semua file Excel di folder input."""
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
        logging.info(f"Folder '{INPUT_DIR}' dibuat. Silakan letakkan file Excel di dalamnya.")
        return []
    
    files = glob.glob(os.path.join(INPUT_DIR, "*.xlsx")) + glob.glob(os.path.join(INPUT_DIR, "*.xls"))
    return files

def is_retriable(status_msg):
    """Mengecek apakah status error layak untuk di-retry."""
    if not status_msg or not status_msg.startswith("gagal"):
        return False
    
    msg_lower = status_msg.lower()
    
    # Jangan di-retry jika sudah diground check oleh user lain atau sudah berhasil
    if "sudah diground check oleh user lain" in msg_lower:
        return False
        
    # Retry jika ada masalah jaringan, timeout, atau status code tertentu (429/409/449)
    retriable_terms = ['timeout', '429', '409', '449', 'connection', 'error']
    return any(term in msg_lower for term in retriable_terms)

def process_file(file_path, session, post_headers, gc_token, csrf_token):
    """Memproses satu file Excel."""
    logging.info(f"--- MEMPROSES FILE: {file_path} ---")
    
    # 1. Buat Backup
    create_backup(file_path)

    try:
        logging.info(f"Membaca file data: {file_path}")
        df = pd.read_excel(file_path, dtype=str)
        df = df.fillna('')
        df = df.replace('nan', '')
        
        if 'status_upload' not in df.columns:
            df['status_upload'] = ''
            
    except Exception as e:
        logging.error(f"Gagal membaca file Excel {file_path}: {e}", exc_info=True)
        return gc_token # Return token yang ada

    required_columns = [
        'perusahaan_id', 'latitude', 'longitude', 'hasilgc',
        'edit_nama', 'edit_alamat', 'nama_usaha', 'alamat_usaha'
    ]
    
    if not all(col in df.columns for col in required_columns):
        logging.error(f"Kolom di Excel {file_path} tidak lengkap. Harus ada: {', '.join(required_columns)}")
        return gc_token

    total_data = len(df)
    logging.info(f"Memulai proses untuk {total_data} baris data di {file_path}...")

    # Simpan indeks yang perlu di-retry
    retriable_indices = []

    def run_process_loop(indices, is_retry_pass=False):
        nonlocal gc_token, session, csrf_token
        
        loop_label = "RETRY" if is_retry_pass else "MAIN"
        current_idx_in_loop = 0
        total_in_loop = len(indices)

        for index in indices:
            row = df.loc[index]
            current_idx_in_loop += 1
            current_num = index + 1
            progress_pct = (current_idx_in_loop / total_in_loop) * 100
            
            if not is_retry_pass and str(row.get('status_upload', '')).lower() == 'berhasil':
                logging.info(f"[{loop_label} PROGRESS {progress_pct:.2f}%] Baris {current_num} sudah berstatus 'berhasil', dilewati.")
                continue

            logging.info(f"--- [{loop_label} PROGRESS {progress_pct:.2f}%] Memproses Baris {current_num} ---")
            
            # --- VALIDASI DATA --- (tetap sama)
            perusahaan_id_val = str(row['perusahaan_id']).strip()
            hasilgc_val = str(row['hasilgc']).replace('.0', '').strip()
            edit_nama_val = str(row['edit_nama']).replace('.0', '').strip()
            edit_alamat_val = str(row['edit_alamat']).replace('.0', '').strip()
            nama_usaha_val = str(row['nama_usaha']).strip()
            alamat_usaha_val = str(row['alamat_usaha']).strip()
            
            validation_errors = []
            if not perusahaan_id_val: validation_errors.append("perusahaan_id kosong")
            valid_hasilgc = ['1', '3', '4', '99']
            if hasilgc_val not in valid_hasilgc: validation_errors.append(f"hasilgc invalid ({hasilgc_val})")
            valid_flag = ['0', '1']
            if edit_nama_val not in valid_flag: validation_errors.append(f"edit_nama invalid ({edit_nama_val})")
            if edit_alamat_val not in valid_flag: validation_errors.append(f"edit_alamat invalid ({edit_alamat_val})")
            
            if validation_errors:
                error_msg = "Invalid: " + "; ".join(validation_errors)
                logging.warning(f"Validasi Gagal Baris {current_num}: {error_msg}")
                df.at[index, 'status_upload'] = error_msg
                df.to_excel(file_path, index=False)
                continue 
            # --- END VALIDASI ---

            if edit_nama_val == '1':
                nama_usaha_val = base64.b64encode(nama_usaha_val.encode('utf-8')).decode('utf-8')
            if edit_alamat_val == '1':
                alamat_usaha_val = base64.b64encode(alamat_usaha_val.encode('utf-8')).decode('utf-8')

            time_on_page_val = str(random.randint(30, 120))
            data = {
                'perusahaan_id': perusahaan_id_val,
                'latitude': str(row['latitude']),
                'longitude': str(row['longitude']),
                'hasilgc': hasilgc_val,
                'gc_token': gc_token,
                'edit_nama': edit_nama_val,
                'edit_alamat': edit_alamat_val,
                'nama_usaha': nama_usaha_val,
                'alamat_usaha': alamat_usaha_val,
                'time_on_page': time_on_page_val, 
                '_token': csrf_token,
            }

            retry_row_count = 0
            max_row_retries = 1
            status_akhir = "gagal"
            
            while retry_row_count <= max_row_retries:
                try:
                    response = session.post(POST_URL, headers=post_headers, data=data, timeout=30)
                    if response.status_code == 200:
                        response_json = response.json()
                        msg = response_json.get('message', 'No message')
                        if response_json.get('status') == 'success' and 'new_gc_token' in response_json:
                            gc_token = response_json['new_gc_token']
                            status_akhir = "berhasil"
                            break 
                        else:
                            status_akhir = f"gagal - {msg}"
                            break 
                    elif response.status_code == 400:
                        response_json = response.json()
                        msg = response_json.get('message', '')
                        if "Token invalid atau sudah terpakai" in msg:
                            session_data_new, new_gc_token = refresh_gc_token_selenium()
                            if session_data_new and new_gc_token:
                                csrf_token = session_data_new['csrf_token']
                                session = requests.Session()
                                for cookie in session_data_new['cookies']:
                                    session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
                                gc_token = new_gc_token
                                data['gc_token'] = gc_token
                                data['_token'] = csrf_token
                                retry_row_count += 1
                                continue 
                            else:
                                status_akhir = "gagal - Refresh token error"
                                break
                        else:
                            status_akhir = f"gagal - {msg}"
                            break
                    else:
                        status_akhir = f"gagal - HTTP {response.status_code}"
                        break
                except requests.exceptions.Timeout:
                    status_akhir = "gagal - Request timeout"
                    break
                except Exception as e:
                    status_akhir = f"gagal - {str(e)[:50]}"
                    break
            
            df.at[index, 'status_upload'] = status_akhir
            
            # Log hasil ke terminal
            if status_akhir == "berhasil":
                logging.info(f"[SUCCESS] Baris {current_num}: {status_akhir}")
            else:
                logging.warning(f"[FAILED] Baris {current_num}: {status_akhir}")
            
            # Cek jika perlu di-retry di pass kedua
            if not is_retry_pass and is_retriable(status_akhir):
                retriable_indices.append(index)

            # Simpan ke Excel
            for attempt in range(3):
                try:
                    df.to_excel(file_path, index=False)
                    break
                except:
                    time.sleep(2)
            
            time.sleep(random.uniform(1, 2))

    try:
        # Pass 1: Main Loop
        run_process_loop(list(df.index))
        
        # Pass 2: Retry Loop (Hanya jika ada yang retriable)
        if retriable_indices:
            logging.info(f"!!! MEMULAI PASS KEDUA (RETRY) UNTUK {len(retriable_indices)} DATA !!!")
            run_process_loop(retriable_indices, is_retry_pass=True)

    except KeyboardInterrupt:
        logging.warning("\n!!! PROSES DIHENTIKAN OLEH PENGGUNA (Ctrl+C) !!!")
        logging.info("Menyimpan data terakhir sebelum keluar...")
        try:
            df.to_excel(file_path, index=False)
            logging.info("Data berhasil disimpan.")
        except Exception as e:
            logging.error(f"Gagal menyimpan data saat exit: {e}")
        sys.exit(0)
        
    return gc_token

def main():
    """Fungsi utama untuk menjalankan scraper."""
    print("\n" + "="*50)
    print("   MatchaIn GC (Matcha Input Gak Culun)")
    print("="*50 + "\n")
    logging.info("Aplikasi dimulai.")
    
    print_validation_rules()
    
    # Bersihkan sesi lama jika cache dimatikan
    if not USE_SESSION_CACHE and os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
            logging.info("Sesi lama dihapus karena USE_SESSION_CACHE=false.")
        except:
            pass

    input_files = get_input_files()
    if not input_files:
        logging.warning(f"Tidak ada file Excel (.xlsx/.xls) ditemukan di folder '{INPUT_DIR}'.")
        return

    # Inisialisasi variabel
    session_data = load_session_from_file()
    gc_token = None

    if not session_data:
        session_data, gc_token = get_authenticated_session_selenium()
    else:
        logging.info("Sesi dimuat dari file, mengambil gc_token awal via Selenium...")
        session_data, gc_token = refresh_gc_token_selenium()

    if not session_data:
        logging.critical("Gagal mendapatkan sesi otentikasi. Proses dihentikan.")
        return

    if not gc_token:
        logging.critical("Gagal mendapatkan gc_token awal. Proses dihentikan.")
        return

    csrf_token = session_data['csrf_token']
    session = requests.Session()
    for cookie in session_data['cookies']:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

    post_headers = {
        'Accept': '*/*', 'Origin': 'https://matchapro.web.bps.go.id', 'Referer': DIR_URL,
        'User-Agent': CUSTOM_USER_AGENT, 'X-Requested-With': 'XMLHttpRequest'
    }

    # Proses setiap file
    for file_path in input_files:
        gc_token = process_file(file_path, session, post_headers, gc_token, csrf_token)

    logging.info("Semua proses selesai.")

if __name__ == "__main__":
    main()
