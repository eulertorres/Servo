import threading
from icrawler.builtin import GoogleImageCrawler

# Função para baixar imagens
def download_image(query, num, output_dir):
    crawler = GoogleImageCrawler(storage={'root_dir': output_dir})
    crawler.crawl(keyword=query, max_num=num)

# Lista das imagens a baixar
imagens = [
    ("X20-7512", 2, "Servo_X20-7512"),
    ("Servo motor Beckhoff AM8000", 2, "Servo_AM8000"),
    ("Servo motor Beckhoff AX5000", 2, "Servo_AX5000"),
]

threads = []

# Criar e iniciar uma thread para cada imagem
for query, num, folder in imagens:
    thread = threading.Thread(target=download_image, args=(query, num, folder))
    thread.start()
    threads.append(thread)

# Esperar todas as threads concluírem
for thread in threads:
    thread.join()

print("Todas as imagens foram baixadas!")
