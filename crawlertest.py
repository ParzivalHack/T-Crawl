import logging
import threading
import os
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import scrapy
from scrapy.crawler import CrawlerProcess
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class MyCrawler(scrapy.Spider):
    name = 'mycrawler'
    allowed_domains = []
    start_urls = []

    def __init__(self, *args, **kwargs):
        super(MyCrawler, self).__init__(*args, **kwargs)
        self.allowed_domains.append(urlparse(kwargs.get('url')).netloc)
        self.start_urls.append(kwargs.get('url'))

    def parse(self, response):
        # Save HTML content
        url = response.url
        content = response.body.decode('utf-8')
        self.save_to_file(url, content)

        # Save other files (e.g., images)
        for img_url in response.css('img::attr(src)').extract():
            self.download_file(img_url)

        # Follow links
        for link in response.css('a::attr(href)').extract():
            if self.allowed_domain(link):
                yield response.follow(link, callback=self.parse)

    def allowed_domain(self, link):
        domain = urlparse(link).netloc
        return domain in self.allowed_domains

    def save_to_file(self, url, content):
        filename = self.get_filename(url)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

    def download_file(self, url):
        response = requests.get(url)
        filename = self.get_filename(url)
        with open(filename, "wb") as f:
            f.write(response.content)

    def get_filename(self, url):
        return os.path.join("output", urlparse(url).path.lstrip('/'))

class Crawler:

    def __init__(self, urls=[], max_depth=3, max_threads=5):
        self.visited_urls = set()
        self.urls_to_visit = urls
        self.max_depth = max_depth
        self.max_threads = max_threads
        self.lock = threading.Lock()

    def download_url(self, url):
        headers = {"User-Agent": "Your User Agent Here"}
        response = requests.get(url, headers=headers)
        return response.text

    def get_linked_urls(self, url, html):
        soup = BeautifulSoup(html, 'html.parser')
        for link in soup.find_all('a'):
            path = link.get('href')
            if path and path.startswith('/'):
                path = urljoin(url, path)
            yield path

    def add_url_to_visit(self, url):
        with self.lock:
            if url not in self.visited_urls and url not in self.urls_to_visit:
                self.urls_to_visit.append(url)

    def crawl(self, url, depth):
        if depth > self.max_depth:
            return

        # Scrape using MyCrawler
        process = CrawlerProcess()
        process.crawl(MyCrawler, url=url)
        process.start()

        html = self.download_url(url)
        for linked_url in self.get_linked_urls(url, html):
            self.add_url_to_visit(linked_url)

    def worker(self):
        while True:
            if not self.urls_to_visit:
                break
            url = self.urls_to_visit.pop(0)
            logging.info(f'Collected: {url}')
            try:
                self.crawl(url, depth=1)
            except Exception:
                logging.exception(f'Failed to crawl: {url}')
            finally:
                self.visited_urls.add(url)

    def run(self):
        threads = []
        for _ in range(self.max_threads):
            thread = threading.Thread(target=self.worker)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

os.system("toilet T-Crawl")

if __name__ == '__main__':
    starting_url = input("Insert URL to crawl: ")
    max_depth = int(input("Set maximum depth: "))
    max_threads = int(input("Set maximum threads: "))
    
    Crawler(urls=[starting_url], max_depth=max_depth, max_threads=max_threads).run()
