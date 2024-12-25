import pytest
import logging
import os
import re
from collections import Counter
from typing import List, Dict, Optional
import requests
from deep_translator import GoogleTranslator
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from time import sleep

 # Types
Article = Dict[str, Optional[str]]

def test_scraper(selenium):
  # Setup logger
  logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
  logger = logging.getLogger(__name__)

  # Initialize WebDriver
  logger.info("Initializing WebDriver")
  driver: WebDriver = selenium if selenium is not None else webdriver.Chrome()
  wait: WebDriverWait = WebDriverWait(driver, 20)

  # Navigate to Opinion Page
  try:
      logger.info("Navigating to the El Pais Opinion page")
      driver.get("https://elpais.com/opinion/")
      
      # Accept cookies if present
      try:
          sleep(5)
          cookie_button = wait.until(
              EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
          )
          logger.info("Cookie popup was found")
          cookie_button.click()
          logger.info("Accepted cookies")
      except TimeoutException:
          logger.info("No cookie popup found")
  except Exception as e:
      logger.error(f"Navigation error: {str(e)}")
      driver.quit()
      exit()

  # Scrape articles
  articles: List[Article] = []
  try:
      logger.info("Fetching articles")
      article_elements = wait.until(
          EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.c.c-o.c-d"))
      )[:5]

      for idx, article in enumerate(article_elements):
          try:
              title = article.find_element(By.CLASS_NAME, "c_t").text
          except Exception:
              title = "Title not available"

          try:
              content = article.find_element(By.CLASS_NAME, "c_d").text
          except Exception:
              content = "Content not available"

          try:
              img_element = article.find_element(By.TAG_NAME, "img")
              img_url = img_element.get_attribute("srcset").split(" ")[0]
          except Exception:
              img_url = None

          articles.append({"title": title, "content": content, "image_url": img_url})
          logger.info(f"Scraped article {idx + 1}: {title}")
  except Exception as e:
      logger.error(f"Error fetching articles: {str(e)}")

  # Download images
  if not os.path.exists("article_images"):
      os.makedirs("article_images")
      logger.info("Created directory for article images")

  for idx, article in enumerate(articles):
      if article["image_url"]:
          try:
              response = requests.get(article["image_url"])
              if response.status_code == 200:
                  image_path = f"article_images/article_{idx+1}.jpg"
                  with open(image_path, "wb") as f:
                      f.write(response.content)
                  logger.info(f"Downloaded image for article {idx + 1}")
              else:
                  logger.warning(f"Failed to download image for article {idx + 1}")
          except Exception as e:
              logger.error(f"Error downloading image {idx + 1}: {str(e)}")

  # Translate headers
  translator = GoogleTranslator(source='es', target='en')
  translated_headers: List[str] = []

  logger.info("Translating article titles")
  for idx, article in enumerate(articles):
      try:
          translated_title = translator.translate(article.get("title", ""))
          translated_headers.append(translated_title)
          logger.info(f"Article {idx + 1} - Original: {article['title']}, Translated: {translated_title}")
      except Exception as e:
          logger.error(f"Translation error for article {idx + 1}: {str(e)}")

  # Analyze headers
  logger.info("Analyzing translated headers for word frequency")
  all_words = ' '.join(translated_headers).lower()
  words = re.findall(r'\b\w+\b', all_words)
  word_counts = Counter(words)

  repeated_words = {word: count for word, count in word_counts.items() if count > 2}
  if repeated_words:
      logger.info("Words that appear more than twice:")
      for word, count in repeated_words.items():
          logger.info(f"'{word}' appears {count} times")
  else:
      logger.info("No words appear more than twice in the headers")

  driver.quit()
  logger.info("Web scraping completed and browser closed")

  assert len(article) > 0, "Fatal: No articles were found"


if __name__ == "__main__":
    test_scraper(None)