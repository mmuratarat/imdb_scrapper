from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

# ChromeDriver'ı otomatik olarak kur ve ayarla
service = Service(ChromeDriverManager().install())

# Chrome tarayıcısını başlat
driver = webdriver.Chrome(service=service)
driver.maximize_window()

url = "https://www.imdb.com/search/title/?title_type=feature&release_date=2024-05-01,2024-05-15&sort=num_votes,desc"
driver.get(url)

driver.implicitly_wait(10)

driver.find_element(By.XPATH, value = '//*[@id="__next"]/div/div/div[2]/div/button[2]').click()

driver.implicitly_wait(10)

# get number of movies
num_movies = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'sc-e3ac1175-3'))).text
#'1-50 of 1,232'
num_movies = int(num_movies.split("of")[1].replace(",", "").strip())

def parse_movie(movie_tag):
    movie_h3 = movie_tag.find('h3', class_='ipc-title__text')
    movie_name = movie_h3.get_text(strip=True).split(' ', 1)[1] if movie_h3 else 'N/A'
    
    href_tag = movie_tag.find('a', class_='ipc-lockup-overlay ipc-focusable')
    href = "https://www.imdb.com" + href_tag['href'] if href_tag else 'N/A'
    
    imdb_id = re.search(r'tt\d+', href).group()
    
    metadata = [span.get_text(strip=True) for span in movie_tag.find_all('span', class_='sc-b189961a-8 kLaxqf dli-title-metadata-item')]
    year_of_release = metadata[0] if len(metadata) > 0 else 'N/A'
    duration = metadata[1] if len(metadata) > 1 else 'N/A'
    rating = metadata[2] if len(metadata) > 2 else 'N/A'
    
    rating_span = movie_tag.find('span', class_='ipc-rating-star ipc-rating-star--base ipc-rating-star--imdb ratingGroup--imdb-rating')
    rating_number = rating_span.get_text(strip=True)[:3] if rating_span else 'N/A'
    vote_count = rating_span.find('span', class_='ipc-rating-star--voteCount').get_text(strip=True).strip('()') if rating_span else 'N/A'
    
    metascore_span = movie_tag.find('span', class_='sc-b0901df4-0 bcQdDJ metacritic-score-box')
    metascore= int(metascore_span.get_text(strip=True)) if metascore_span else 'N/A'
    
    summary_div = movie_tag.find('div', class_='ipc-html-content-inner-div')
    summary = summary_div.get_text(strip=True) if summary_div else 'N/A'
    return {'IMDB ID': imdb_id,
            'Movie Name': movie_name,
            'Link': href,
            'Year of Release': year_of_release,
            'Duration': duration,
            'Rating': rating,
            'IMDB Rating': rating_number,
            'Votes': vote_count,
            'Metascore': metascore,
            'Summary': summary
           }

# Function to scrape the current page
def scrape_current_page():
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    movie_tags = soup.find_all('div', class_='ipc-metadata-list-summary-item__tc')
    return [parse_movie(movie_tag) for movie_tag in movie_tags]

all_movies = []
seen_movies = set()

while True:
    # Scrape the current page
    current_movies = scrape_current_page()

    # Filter out duplicates
    new_movies = [movie for movie in current_movies if (movie['Movie Name'], movie['IMDB ID']) not in seen_movies]
    
    # Add new movies to the list and update the seen_movies set
    all_movies.extend(new_movies)
    seen_movies.update((movie['Movie Name'], movie['IMDB ID']) for movie in new_movies)
    
    try:
        # Click the "50 more" button to go to the next page
        next_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="__next"]/main/div[2]/div[3]/section/section/div/section/section/div[2]/div/section/div[2]/div[2]/div[2]/div/span/button')))
        driver.execute_script("arguments[0].click();", next_button)
        
        # Wait for the next page to load
        time.sleep(3)
    except Exception as e:
        print("No more pages to scrape.")
        break

# Close the WebDriver
driver.quit()