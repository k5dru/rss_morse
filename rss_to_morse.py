#!/usr/bin/python3 

from bs4 import BeautifulSoup
import time
import requests
import re
from morse_to_audio import morse_to_audio

# init morse_to_audio with the parameters you like. 
# declick_cycles is the number of full sine-wave cycles to ramp from zero to full volume and back down at the end; 1.5 to 2.0 sounds good to me
# NOTE! Some speed and freuqency combinations cause an off-by-one error.  Change the frequency a bit up or down to get a good one.
m=morse_to_audio(wpm=25, amplitude=0.15, frequency=500, Farnsworth=True, doubleFarnsworth=False, declick_cycles=2.0)

# url = requests.get('https://press.coop/@NPR.rss')
url = requests.get('https://press.coop/@AJEnglish.rss')

soup = BeautifulSoup(url.content, 'xml')

items = soup.find_all('item')
  
for i in items:
    raw_html = i.description.text
    raw_html = re.sub(re.compile('</p>'), '\n\n', raw_html)
    raw_html = re.sub(re.compile('#press'), '', raw_html)
    raw_html = re.sub(re.compile('http.*'), '', raw_html)

    description = BeautifulSoup(raw_html, "lxml").text

    print(f'{description}')

    m.play_text(description)
    print ('\n\n------------------------\n')
    time.sleep(30)
