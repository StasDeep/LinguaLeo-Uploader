#!/usr/bin/env python
# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------
# Name:     LinguaLeo Uploader
# Purpose:  Automated content addition to LinguaLeo from favorite channels.
#
# Created:  9th of July 2017
# Author:   StasDeep
#------------------------------------------------------------------------------

"""Work with LinguaLeo "Add content" interface and YouTube API.

Usage:
  $ python script.py data.json

"""

from HTMLParser import HTMLParser
import json
import re
import time

import caption_convert

from apiclient.discovery import build
from apiclient.errors import HttpError
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup


YT_PREFIX = 'https://www.youtube.com/watch?v='


class LeoUploader(object):
    """Uploads YouTube video to LinguaLeo."""

    def __init__(self, filename):
        """Initialize LeoUploader object.
        Sign in to LinguaLeo.

        Args:
            filename (str): name of the config file.

        Raises:
            IOError: if file cannot be read.
            ValueError: if file content is not valid JSON.
            KeyError: if JSON does not have necessary fields.
        """
        self.filename = filename

        with open(self.filename, 'r') as infile:
            data = json.load(infile)

        email = data['email']
        password = data['password']
        api_key = data['api_key']

        self.channels = data['channels']
        self.extra_videos = data['extra_videos']
        self.youtube = build('youtube', 'v3', developerKey=api_key)

        self.driver = webdriver.Chrome()
        self._sign_in(email, password)

    def add_new_videos(self):
        """Upload new videos from channels to LinguaLeo.

        IDs of new videos are extracted with API.
        Then these IDs are used for getting subtitles.

        Raises:
            HttpError: if request cannot be sent.
        """
        for channel in self.channels[:1]:
            try:
                new_videos = self._get_new_videos(channel)
            except HttpError:
                continue

            for video in sorted(new_videos, key=lambda x: x['published_at'])[:1]:
                self._upload_video(video['id'])

    def add_extra_videos(self):
        """Upload videos that were not uploaded in previous attempt."""
        pass

    def save_config(self):
        """Save updated config to file."""
        pass

    def _upload_video(self, video_id):
        """Download subtitles, fill LinguaLeo form and publish video."""
        self._download_video_subtitles(video_id)

    def _get_new_videos(self, channel):
        """Return new videos from channel (ID, title and publish datetime).

        Args:
            channel (dict): object with channel 'id' and 'last_refresh' keys.

        Returns:
            list: dicts with 'id', 'title' and 'published_at'.

        Raises:
            HttpError: if request cannot be sent.
        """
        search_response = self.youtube.search().list(
            part='id, snippet',
            type='video',
            channelId=channel['id'],
            publishedAfter=channel['last_refresh'],
            maxResults=50
        ).execute()

        return [dict(id=item['id']['videoId'],
                     published_at=item['snippet']['publishedAt'],
                     title=item['snippet']['title'])
                for item in search_response['items']]

    def _download_video_subtitles(self, video_id):
        """Download English subtitles from video.

        Args:
            video_id (str): ID of the video of which subtitiles are downloaded.

        Raises:
            AttributeError: if English caption not found.
        """
        # Open new tab.
        video_id = 'A-QgGXbDyR0'
        self.driver.execute_script(
            'window.open("")'
        )

        # Switch to new tab.
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.driver.get('http://video.google.com/timedtext?lang=en&v={}'.format(
            video_id
        ))

        try:
            xml_block = self.driver.find_element_by_css_selector(
                'div.pretty-print > .collapsible > .expanded > .collapsible-content'
            ).get_attribute('innerHTML')
        except NoSuchElementException:
            raise AttributeError('English caption not found')

        # Get XML from parsed HTML. BeautifulSoup is used, because
        # it saves linefeeds.
        xml_captions = BeautifulSoup(xml_block, 'html.parser').get_text()
        # Replace all escaped characters with unicode.
        xml_captions = HTMLParser().unescape(xml_captions)

        srt_captions = caption_convert.xml_to_srt(xml_captions)

        # caption_filename = '{}.srt'.format(video_id)
        # with open(caption_filename, 'w') as outfile:
        #     outfile.write(srt_captions.encode('utf8'))

    def _sign_in(self, email, password):
        """Authorize to LinguaLeo site.

        Args:
            email (str): LinguaLeo account email.
            password (str): LinguaLeo account password corresponding to email.
        """
        self.driver.get('http://www.lingualeo.com/ru/login')
        if 0:
            self.driver.find_element_by_name('email').send_keys(email)
            password_field = self.driver.find_element_by_name('password')
            password_field.send_keys(password)
            password_field.send_keys(Keys.RETURN)
            self.driver.get('http://lingualeo.com/ru/jungle/add')


def main():
    """Main function that launches automatically from command line."""
    leo_uploader = LeoUploader('data.json')
    leo_uploader.add_new_videos()


if __name__ == '__main__':
    main()
