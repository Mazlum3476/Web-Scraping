import time
import random
import datetime
import logging

from logging.handlers import RotatingFileHandler
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
import pandas as pd
import os
from multiprocessing import Process
import multiprocessing  # multiprocessing modülünü içe aktar

# Rastgele User-Agent listesi
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
]

def get_total_pages(driver: webdriver.Chrome, city: str, logger: logging.Logger) -> int:
    """
    Belirli bir şehir için toplam sayfa sayısını çeker.

    Args:
        driver (webdriver.Chrome): Selenium WebDriver nesnesi.
        city (str): Şehir adı.
        logger (logging.Logger): Logger nesnesi.

    Returns:
        int: Toplam sayfa sayısı.
    """
    base_url = f"https://www.hepsiemlak.com/{city.lower()}-satilik"
    try:
        driver.get(base_url)
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        # Cloudflare doğrulamasını atlat
        check_and_handle_cloudflare(driver)

        # Pagination bölümünü bul
        try:
            pagination = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.he-pagination'))
            )
            # Tüm sayfa numaralarını al
            page_numbers = pagination.find_elements(By.CSS_SELECTOR, 'a.he-pagination__link')
            
            # En son sayfa numarasını bul
            if page_numbers:
                last_page_number = page_numbers[-1].text.strip()
                if last_page_number.isdigit():
                    total_pages = int(last_page_number)
                    logger.info(f"{city} için toplam sayfa sayısı bulundu: {total_pages}")
                    return total_pages
                else:
                    logger.warning(f"{city} için son sayfa numarası geçersiz: {last_page_number}")
                    return 1  # Varsayılan değer
            else:
                logger.warning(f"{city} için sayfa numaraları bulunamadı.")
                return 1  # Varsayılan değer
        except Exception as e:
            logger.warning(f"{city} için pagination bulunamadı veya tıklanamadı: {e}")
            return 1  # Varsayılan değer
    except Exception as e:
        logger.error(f"{city} için sayfa sayısı çekme hatası: {e}", exc_info=True)
        return 1  # Hata durumunda varsayılan değer

def set_random_user_agent(chrome_options):
    """Rastgele bir user-agent seçer."""
    user_agent = random.choice(user_agents)
    chrome_options.add_argument(f"user-agent={user_agent}")

def random_mouse_movement(driver):
    """Rastgele mouse hareketleri ekler."""
    try:
        start_time = time.time()
        # Tarayıcı penceresinin boyutunu al
        window_size = driver.get_window_size()
        width = window_size["width"]
        height = window_size["height"]

        actions = ActionChains(driver)

        # Başlangıç noktasını kaydet
        initial_position = driver.execute_script("return { x: window.scrollX, y: window.scrollY };")

        for _ in range(random.randint(3, 5)):  # 3-5 rastgele hareket
            # Mouse'u pencerenin sınırları içinde hareket ettir
            x_offset = random.randint(-width // 4, width // 4)  # X koordinatını pencere sınırları içinde tut
            y_offset = random.randint(-height // 4, height // 4)  # Y koordinatını pencere sınırları içinde tut

            # Hedef koordinatlarının sınırda olup olmadığını kontrol et
            new_x = min(max(initial_position["x"] + x_offset, 0), width)
            new_y = min(max(initial_position["y"] + y_offset, 0), height)

            actions.move_to_element_with_offset(driver.find_element("tag name", "body"), new_x, new_y).perform()
            time.sleep(random.uniform(0.5, 1.5))
        
        # Başlangıç noktasına geri git
        actions.move_to_element_with_offset(driver.find_element("tag name", "body"), initial_position["x"], initial_position["y"]).perform()

        elapsed_time = time.time() - start_time
        logging.info(f"Rastgele mouse hareketleri tamamlandı. Süre: {elapsed_time:.2f} saniye.")

    except Exception as e:
        logging.error(f"Mouse hareketleri sırasında hata oluştu: {e}", exc_info=True)

def random_sleep():
    """Rastgele bekleme süresi ekler."""
    sleep_time = random.uniform(2, 5)
    logging.info(f"Rastgele bekleme süresi: {sleep_time:.2f} saniye.")
    time.sleep(sleep_time)

def init_driver():
    """WebDriver'ı başlatır ve döndürür."""
    start_time = time.time()
    # ChromeDriver ayarları
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--headless")  
    set_random_user_agent(chrome_options)  # Rastgele user-agent ekle

    # ChromeDriver'ı yükle
    try:
        import chromedriver_autoinstaller
        chromedriver_path = chromedriver_autoinstaller.install()
        service = Service(chromedriver_path)
    except Exception as e:
        logging.error(f"ChromeDriver yükleme hatası: {e}", exc_info=True)
        raise SystemExit("ChromeDriver yüklenemedi.")

    # WebDriver'ı başlat
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Tarayıcı penceresinin boyutunu ayarla
    driver.set_window_size(1200, 800)  # Genişlik: 1200, Yükseklik: 800

    # Sayfa yükleme zaman aşımını artır
    driver.set_page_load_timeout(200)  # 300 saniye (5 dakika)
    driver.implicitly_wait(30)  # Element bulma zaman aşımını 30 saniye yap

    elapsed_time = time.time() - start_time
    logging.info(f"WebDriver başlatıldı. Süre: {elapsed_time:.2f} saniye.")
    return driver

def fetch_ilan_detay(driver, url, max_retries=50):
    """İlan detaylarını çeker. Doğru veriyi alana kadar belirli sayıda deneme yapar."""
    retries = 0
    while retries < max_retries:
        try:
            start_time = time.time()
            logging.info(f"İlan detayları çekiliyor: {url} (Deneme: {retries + 1}/{max_retries})")

            # Sayfa yükleme zaman aşımını artır
            driver.set_page_load_timeout(300)  # 300 saniye (5 dakika)
            driver.get(url)

            # Cloudflare doğrulama ekranını işle
            check_and_handle_cloudflare(driver)

            # Sayfanın tamamen yüklenmesini bekle
            WebDriverWait(driver, 30).until(  # Bekleme süresini 30 saniye yap
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Başlık için birden fazla selector dene
            try:
                baslik = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'h1'))
                ).text.strip()
                logging.info(f"Başlık başarıyla çekildi: {baslik}")
            except Exception as e:
                baslik = "Başlık bulunamadı"
                logging.warning(f"Başlık bulunamadı, yeniden deneme: {retries + 1}/{max_retries}. Hata: {e}")

            # Fiyat için birden fazla selector dene
            try:
                fiyat = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'p.price'))
                ).text.strip()
                logging.info(f"Fiyat başarıyla çekildi: {fiyat}")
            except Exception as e:
                fiyat = "Fiyat bulunamadı"
                logging.warning(f"Fiyat bulunamadı, yeniden deneme: {retries + 1}/{max_retries}. Hata: {e}")

            # Konum için birden fazla selector dene
            try:
                konum = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'ul.detail-info-location'))
                ).text.strip()
                logging.info(f"Konum başarıyla çekildi: {konum}")
            except Exception as e:
                konum = "Konum bulunamadı"
                logging.warning(f"Konum bulunamadı, yeniden deneme: {retries + 1}/{max_retries}. Hata: {e}")

            # Detay bilgilerini çek
            detaylar = {}
            try:
                spec_items = driver.find_elements(By.CSS_SELECTOR, 'li.spec-item')
                for item in spec_items:
                    label = item.find_element(By.CSS_SELECTOR, 'span.txt').text.strip()
                    value = item.find_element(By.CSS_SELECTOR, 'span.value-txt').text.strip() if item.find_elements(By.CSS_SELECTOR, 'span.value-txt') else item.text.strip()
                    detaylar[label] = value
                logging.info(f"Detay bilgileri başarıyla çekildi: {detaylar}")
            except Exception as e:
                logging.warning(f"Detay bilgileri bulunamadı. Hata: {e}")

            # Eğer tüm veriler doğru şekilde alındıysa döngüden çık
            if baslik != "Başlık bulunamadı" and fiyat != "Fiyat bulunamadı" and konum != "Konum bulunamadı":
                elapsed_time = time.time() - start_time
                logging.info(f"İlan detayları başarıyla çekildi. Süre: {elapsed_time:.2f} saniye.")
                return {
                    "Başlık": baslik,
                    "Fiyat": fiyat,
                    "Konum": konum,
                    **detaylar,
                    "URL": url
                }

            # Eğer veriler alınamadıysa, yeniden deneme yap
            retries += 1
            logging.info(f"Veri çekme başarısız, yeniden deneme: {retries}/{max_retries}")
            time.sleep(2)  # Yeniden denemeden önce kısa bir bekleme süresi ekle

        except Exception as e:
            logging.error(f"İlan detaylarını çekme hatası ({url}): {e}", exc_info=True)
            retries += 1
            time.sleep(2)  # Hata durumunda kısa bir bekleme süresi ekle

    # Maksimum deneme sayısına ulaşıldığında hata döndür
    logging.error(f"Maksimum deneme sayısına ulaşıldı, veri çekilemedi: {url}")
    return {
        "Başlık": "Başlık bulunamadı",
        "Fiyat": "Fiyat bulunamadı",
        "Konum": "Konum bulunamadı",
        "URL": url
    }

def scroll_page(driver):
    """Sayfayı kaydırarak tüm ilanların yüklenmesini sağlar."""
    start_time = time.time()
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    elapsed_time = time.time() - start_time
    logging.info(f"Sayfa kaydırma işlemi tamamlandı. Süre: {elapsed_time:.2f} saniye.")

def save_to_excel(data, filename):
    """Verileri Excel dosyasına kaydeder."""
    start_time = time.time()
    if os.path.exists(filename):
        # Eğer dosya varsa, mevcut verileri oku ve yeni verileri ekle
        existing_df = pd.read_excel(filename)
        updated_df = pd.concat([existing_df, pd.DataFrame(data)], ignore_index=True)
        updated_df.to_excel(filename, index=False)
    else:
        # Dosya yoksa, yeni bir dosya oluştur
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False)
    elapsed_time = time.time() - start_time
    logging.info(f"Veriler {filename} dosyasına kaydedildi. Süre: {elapsed_time:.2f} saniye.")


def setup_logger(city: str) -> logging.Logger:
    """
    Her proses için ayrı bir log dosyası oluşturur ve logger'ı yapılandırır.

    Args:
        city (str): Şehir adı (log dosyasının adı için kullanılır).

    Returns:
        logging.Logger: Yapılandırılmış logger nesnesi.
    """
    log_file: str = f"{city}.log"
    log_format: str = "%(asctime)s - %(levelname)s - %(message)s"
    log_level: int = logging.INFO
    max_log_size: int = 5 * 1024 * 1024  # 5MB
    backup_count: int = 3

    # Logger'ı yapılandır
    logger = logging.getLogger(city)
    logger.setLevel(log_level)

    # Dosya handler'ı ekle
    file_handler = RotatingFileHandler(log_file, maxBytes=max_log_size, backupCount=backup_count)
    file_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(file_handler)

    # Konsol handler'ı ekle
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(console_handler)

    return logger

def load_page_with_retry(driver: webdriver.Chrome, url: str, logger: logging.Logger, max_retries: int = 10) -> bool:
    """
    Sayfayı yükler ve zaman aşımı durumunda belirli sayıda yeniden dener.

    Args:
        driver (webdriver.Chrome): Selenium WebDriver nesnesi.
        url (str): Yüklenecek sayfanın URL'si.
        logger (logging.Logger): Logger nesnesi.
        max_retries (int): Maksimum yeniden deneme sayısı.

    Returns:
        bool: Sayfa başarıyla yüklendiyse True, aksi takdirde False.
    """
    retries: int = 0
    while retries < max_retries:
        try:
            driver.get(url)
            # Sayfanın tamamen yüklenmesini bekleyin
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            logger.info(f"Sayfa başarıyla yüklendi: {url}")
            return True
        except TimeoutException:
            retries += 1
            logger.warning(f"Sayfa yükleme zaman aşımı ({url}). Yeniden deneme: {retries}/{max_retries}")
            driver.refresh()  # Sayfayı yenile
        except Exception as e:
            logger.error(f"Sayfa yükleme hatası ({url}): {e}", exc_info=True)
            return False
    logger.error(f"Sayfa yükleme başarısız: {url} (Maksimum deneme sayısına ulaşıldı)")
    return False

def scrape_city(city: str) -> None:
    """Belirli bir şehir için ilanları çeker."""
    logger = setup_logger(city)  # Şehir için logger'ı başlat
    driver = init_driver()  # Her proses için ayrı bir WebDriver başlat
    logger.info(f"\n{city} için WebDriver başlatıldı.")
    try:
        base_url = f"https://www.hepsiemlak.com/{city.lower()}-satilik"
        ilan_verileri = []

        # Dosya adını başlangıçta bir kez oluştur
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M")
        excel_filename = f"FORK_ilanlar_{city}_{timestamp}.xlsx"

        logger.info(f"{city} için scraping işlemi başlatıldı. Excel dosyası: {excel_filename}")

        # Toplam sayfa sayısını al
        total_pages = get_total_pages(driver, city, logger)
        logger.info(f"{city} için toplam sayfa sayısı: {total_pages}")

        for page in range(1, total_pages + 1):  # Sayfa sayısını dinamik olarak kullan
            url = f"{base_url}?page={page}"
            logger.info(f"{city} - {page}. sayfa çekiliyor: {url}")

            #! Sayfayı yükle ve zaman aşımı durumunda yeniden dene
            if not load_page_with_retry(driver, url, logger):
                logger.error(f"{city} - {page}. sayfa yüklenemedi, atlanıyor.")
                continue  #! Sayfa yüklenemediyse bir sonraki sayfaya geç

            # Sayfa başarıyla yüklendiyse devam et
            logger.info(f"{city} - {page}. sayfa başarıyla yüklendi.")

            # Rastgele mouse hareketleri ekle
            random_mouse_movement(driver)
            logger.info(f"{city} - Rastgele mouse hareketleri eklendi.")

            # Sayfayı kaydır
            scroll_page(driver)
            logger.info(f"{city} - Sayfa kaydırma işlemi tamamlandı.")

            # Rastgele bekleme süresi ekle
            random_sleep()
            logger.info(f"{city} - Rastgele bekleme süresi eklendi.")

            try:
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.querySelectorAll('a.card-link').length") > 0
                )
                ilan_linkleri = [ilan.get_attribute('href') for ilan in driver.find_elements(By.CSS_SELECTOR, 'a.card-link') if ilan.get_attribute('href')]
                logger.info(f"{city} - {page}. sayfada {len(ilan_linkleri)} ilan bulundu.")
            except Exception as e:
                screenshot_filename = f"FORK_screenshot_{city}_page_{page}.png"
                driver.save_screenshot(screenshot_filename)
                logger.error(f"{city} - {page}. sayfada ilan linkleri bulunamadı: {e}")
                logger.error(f"Ekran görüntüsü kaydedildi: {screenshot_filename}")
                continue    

            for ilan_url in ilan_linkleri:
                logger.info(f"{city} - İlan detayları çekiliyor: {ilan_url}")
                detaylar = fetch_ilan_detay(driver, ilan_url)
                if detaylar:
                    ilan_verileri.append(detaylar)
                    logger.info(f"{city} - İlan detayları başarıyla çekildi: {ilan_url}")
                else:
                    logger.warning(f"{city} - İlan detayları çekilemedi: {ilan_url}")

            # Her sayfadan sonra verileri Excel dosyasına kaydet
            if ilan_verileri:
                save_to_excel(ilan_verileri, excel_filename)
                ilan_verileri = []  # Verileri kaydettikten sonra listeyi temizle
                logger.info(f"{city} - {page}. sayfa verileri Excel dosyasına kaydedildi.")

    except Exception as e:
        logger.error(f"{city} - Hata oluştu: {e}", exc_info=True)
    finally:
        # Son olarak tüm verileri kaydet
        if ilan_verileri:
            save_to_excel(ilan_verileri, excel_filename)
            logger.info(f"{city} - Son veriler Excel dosyasına kaydedildi.")
        driver.quit()
        logger.info(f"{city} - WebDriver kapatıldı.")

def check_and_handle_cloudflare(driver):
    """Cloudflare doğrulama ekranını kontrol eder ve işler."""
    try:
        # Cloudflare doğrulama ekranını kontrol et
        verification_checkbox = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='checkbox']"))
        )
        logging.info("Cloudflare doğrulama ekranı bulundu, doğrulama yapılıyor...")
        verification_checkbox.click()
        logging.info("Doğrulama kutusu tıklandı.")

        # Doğrulama işleminin tamamlanmasını bekleyin
        time.sleep(random.uniform(5, 8))  # Cloudflare'in doğrulama işlemini tamamlaması için bekleyin

        # Sayfanın yeniden yüklenmesini bekleyin
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        logging.info("Doğrulama işlemi tamamlandı ve sayfa yeniden yüklendi.")
    except:
        # Doğrulama ekranı yoksa, hiçbir şey yapma
        pass

def main():
    cities = [
    "Afyonkarahisar", "Kutahya", "Usak", "Mugla", "Denizli", "Aydin", "Manisa", "Izmir",
    "Burdur", "Isparta", "Osmaniye", "Kahramanmaras", "Antalya", "Hatay", "Adana", "Mersin",
    "Bilecik", "Kirklareli", "Canakkale", "Edirne", "Balikesir", "Tekirdag", "Sakarya", "Yalova", "Bursa", "Kocaeli", "Istanbul",
    "Bayburt", "Artvin", "Gumushane", "Kastamonu", "Sinop", "Corum", "Amasya", "Bolu", "Tokat", "Giresun", "Ordu", "Duzce", "Karabuk", "Rize", "Samsun", "Trabzon", "Zonguldak",
    "Cankiri", "Yozgat", "Sivas", "Kirsehir", "Karaman", "Nigde", "Aksaray", "Nevsehir", "Konya", "Kirikkale", "Eskisehir", "Kayseri", "Ankara",
    "Ardahan", "Tunceli", "Kars", "Hakkari", "Erzincan", "Agri", "Bitlis", "Mus", "Bingol", "Erzurum", "Igdir", "Van", "Elazig", "Malatya",
    "Siirt", "Sirnak", "Adiyaman", "Mardin", "Kilis", "Sanliurfa", "Batman", "Diyarbakir", "Gaziantep"]
    # Aynı anda çalışacak maksimum işlem sayısı
    max_processes = 3
    processes = []

    for city in cities:
        # Eger aktif işlem sayısı maksimuma ulaştıysa, bir işlemin bitmesini bekle
        if len(processes) >= max_processes:
            for process in processes:
                process.join()  # Bir işlemin bitmesini bekle
            processes = []  # İşlem listesini temizle

        # Yeni bir işlem başlat
        process = multiprocessing.Process(target=scrape_city, args=(city,))
        processes.append(process)
        process.start()
        logging.info(f"{city} için işlem başlatıldı.")

    # Kalan tüm işlemlerin bitmesini bekle
    for process in processes:
        process.join()

    logging.info("Tüm şehirler için işlem tamamlandı.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    main()
