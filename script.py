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

import json
from apiclient.discovery import build
from apiclient.errors import HttpError
from selenium.webdriver.common.keys import Keys
from selenium import webdriver


TEST_WITHOUT_SIGNING = True


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

        if TEST_WITHOUT_SIGNING:
            print 'No signing to LinguaLeo.'
        else:
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
                new_videos = self._get_new_videos_ids(channel)
            except HttpError:
                continue

            self._download_video_subtitles(new_videos[0]['id'])

    def add_extra_videos(self):
        """Upload videos that were not uploaded in previous attempt."""
        pass

    def save_config(self):
        """Save updated config to file."""
        pass

    def _get_new_videos_ids(self, channel):
        """Return IDs of new videos from channel.

        Args:
            channel (dict): object with 'id' and 'last_refresh' keys.

        Returns:
            list: dicts with 'id' and 'published_at'.

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
                     published_at=item['snippet']['publishedAt'])
                for item in search_response['items']]

    def _get_video_name(self, video_id):
        """Return name of the video.

        Raises:
            apiclient.errors.HttpError: if request cannot be sent.
        """
        videos_response = self.youtube.videos().list(
            part='snippet',
            id=video_id
        ).execute()
        return videos_response['items'][0]['snippet']['title']

    def _download_video_subtitles(self, video_id):
        """Download English subtitles from video.

        Raises:
            AttributeError: if English caption not found.
        """
        captions_response = self.youtube.captions().list(
            part='id, snippet',
            videoId=video_id,
        ).execute()

        try:
            caption_id = next(caption['id']
                       for caption in captions_response['items']
                       if caption['snippet']['language'] == 'en'
            )
        except StopIteration:
            raise AttributeError('English captions not found')


    def _sign_in(self, email, password):
        """Authorize to LinguaLeo site."""
        self.driver.get('http://www.lingualeo.com/ru/login')
        self.driver.find_element_by_name('email').send_keys(email)
        self.driver.find_element_by_name('password').send_keys(password)
        self.driver.find_element_by_name('password').send_keys(Keys.RETURN)
        self.driver.get('http://lingualeo.com/ru/jungle/add')


def main():
    """Main function that launches automatically from command line."""
    leo_uploader = LeoUploader('data.json')
    leo_uploader.add_new_videos()


if __name__ == '__main__':
    main()
