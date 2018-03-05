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
  $ python script.py --extra https://youtube.com/watch?v=Akm7ik-H_7U
  $ python script.py --config data.json

"""

import datetime
from HTMLParser import HTMLParser
import json
import os
import re
import urllib2

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from httplib2 import ServerNotFoundError
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import argparser
import xml2srt


YT_PREFIX = 'https://www.youtube.com/watch?v='
ISO_8601_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class CredentialsError(Exception):
    """Error with email or password."""
    pass


class LeoUploader(object):
    """Uploads YouTube video to LinguaLeo."""

    INNER_CONFIG_NAME = os.path.join(os.path.expanduser('~'), '.leo.json')

    def __init__(self, config_filename):
        """Initialize LeoUploader object.
        Sign in to LinguaLeo.

        Args:
            config_filename (str): name of the config file.

        Raises:
            IOError: if file cannot be read.
            ValueError: if file content is not valid JSON.
            KeyError: if JSON does not have necessary fields.
        """
        self.config_filename = config_filename

        with open(self.config_filename, 'r') as infile:
            data = json.load(infile)

        self.email = data['email']
        self.password = data['password']
        self.api_key = data['api_key']

        self.channels = data['channels']
        self.extra_videos = data['extra_videos']
        self.erroneous_videos = []
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

        self.driver = webdriver.Chrome()
        self.driver.maximize_window()

    def load_new_videos(self):
        """Load information about new videos on the channels."""
        for channel in self.channels:
            try:
                channel['new_videos'] = self._get_new_videos(channel)
            except HttpError:
                print 'Cannot get videos from channel "{}"'.format(channel['name'])
                continue

    def any_videos_to_upload(self):
        """Check if there are any videos to upload.

        Returns:
            bool: True, if at least one video is going to be uploaded.
                  False, otherwise.
        """
        any_new_videos = any(channel['new_videos'] for channel in self.channels)
        return any_new_videos or self.extra_videos

    def add_new_videos(self):
        """Upload new videos from channels to LinguaLeo.

        IDs of new videos are extracted with API.
        Then these IDs are used for getting subtitles.
        """
        for i, channel in enumerate(self.channels):
            # Output blank line before every channel output except first.
            if i:
                print
            print "Checking {}...".format(channel['name'])

            if not channel['new_videos']:
                print '  No new videos'
            else:
                print '  Found {} new video(s)'.format(len(channel['new_videos']))

            for video in sorted(channel['new_videos'], key=lambda x: x['published_at']):
                try:
                    self._upload_video_wrapper(video, channel['name'])
                except AttributeError as exception:
                    print '  {}'.format(exception)

                # Strip milliseconds and add one second
                # to not upload a video twice.
                last_refresh = self._add_one_second(
                    video['published_at'][:-5] + 'Z'
                )
                channel['last_refresh'] = last_refresh

    def add_extra_videos(self):
        """Upload videos that were not uploaded in previous attempt."""
        print '\nChecking extra videos...'

        if not self.extra_videos:
            print '  No extra videos'
        else:
            print '  Found {} video(s)'.format(len(self.extra_videos))

        for video in self.extra_videos:
            try:
                self._upload_video_wrapper(video, video['channel_name'])
            except AttributeError as exception:
                print '  {}'.format(exception)

    def sign_in(self):
        """Authorize to LinguaLeo site.

        Raises:
            CredentialsError: if email and/or password is invalid.
        """
        print 'Signing in...'
        self.driver.get('http://lingualeo.com/ru/login')
        self.driver.find_element_by_name('email').send_keys(self.email)
        password_field = self.driver.find_element_by_name('password')
        password_field.send_keys(self.password)
        password_field.send_keys(Keys.RETURN)
        if self.driver.current_url == 'http://lingualeo.com/ru/login':
            raise CredentialsError('Invalid email and/or password')
        print 'Done\n'

    def save_config(self, extra_videos=None):
        """Save updated config to file."""
        # If extra videos are provided, than they're should be saved as well
        # as erroneous videos.
        if extra_videos is not None:
            self.erroneous_videos.extend(extra_videos)

        data = dict(
            api_key=self.api_key,
            email=self.email,
            password=self.password,
            channels=self.channels,
            extra_videos=self.erroneous_videos
        )

        with open(self.config_filename, 'w') as outfile:
            json_data = json.dumps(data, ensure_ascii=False, indent=4)
            outfile.write(json_data.encode('utf8'))

    def write_extra_videos(self, extra_videos):
        """Save config with extended extra videos.

        Args:
            extra_videos (list): list of URLs to videos.

        Raises:
            ValueError: if URLs' format is incorrect.
        """
        yt_video_id_pattern = r'(?:youtube\.com/watch\?v=|youtu\.be/)(.{11})'
        video_ids = [re.search(yt_video_id_pattern, link).group(1)
                     for link in extra_videos]

        extra_videos = []

        for video_id in video_ids:
            response = self.youtube.videos().list(
                part='snippet',
                id=video_id
            ).execute()

            video_title = response['items'][0]['snippet']['title']
            channel_id = response['items'][0]['snippet']['channelId']

            response = self.youtube.channels().list(
                part='snippet',
                id=channel_id
            ).execute()

            channel_name = response['items'][0]['snippet']['title']

            extra_videos.append(dict(
                id=video_id,
                title=video_title,
                channel_name=channel_name
            ))

        self.save_config(self.extra_videos + extra_videos)

    def write_new_channels(self, channel_urls):
        """Add new channels to config

        Args:
            channel_urls (list): list with URLs to channels.
        """
        for channel_url in channel_urls:
            match = re.search(r'youtube\.com/channel/(.{24})', channel_url)

            if not match:
                match = re.search(r'youtube\.com/user/(.*)', channel_url)

                if not match:
                    print 'Not valid channel URL: {}'.format(channel_url)
                    continue

                search_by_id = False
            else:
                search_by_id = True

            channel_search_param = match.group(1)

            search_kwargs = dict(part='snippet')
            if search_by_id:
                search_kwargs['id'] = channel_search_param
            else:
                search_kwargs['forUsername'] = channel_search_param

            response = self.youtube.channels().list(**search_kwargs).execute()

            self.channels.append(dict(
                channel_title=response['items'][0]['snippet']['title'],
                channel_id=response['items'][0]['id'],
                current_time=datetime.datetime.now().strftime(ISO_8601_FORMAT)
            ))

    def _upload_video_wrapper(self, video, channel_name):
        """Wrap _upload video function to catch exceptions.

        Args:
            video (dict): object with 'id' and 'title' keys.
                Represents the video to be uploaded.
            channel_name (str): name of the channel video is from.

        Raises:
            AttributeError: if cannot upload.
        """
        try:
            self._upload_video(video, channel_name)
        except AttributeError as exception:
            self.erroneous_videos.append(dict(
                channel_name=channel_name,
                id=video['id'],
                title=video['title']
            ))
            raise AttributeError('Unable to upload: {} ({})'.format(
                YT_PREFIX + video['id'],
                exception
            ))
        else:
            print '  Successfully uploaded: {}'.format(
                self.driver.current_url
            )

    def _upload_video(self, video, channel_name):
        """Download subtitles, fill LinguaLeo form and publish video.

        Args:
            video (dict): object with 'id' and 'title' keys.
                Represents the video to be uploaded.
            channel_name (str): name of the channel video is from.

        Raises:
            AttributeError: if English subtitles not found or name is incorrect.
        """
        subtitles_filename = self._download_video_subtitles(video['id'])

        self.driver.get('http://lingualeo.com/ru/jungle/add')

        # Insert video link.
        self.driver.find_element_by_name('content_embed').send_keys(
            YT_PREFIX + video['id']
        )

        # Insert video name.
        self.driver.find_element_by_name('content_name').send_keys(
            self._generate_video_title(channel_name, video['title'])
        )

        # Insert path to the subtitles.
        self.driver.find_element_by_name('content_srt').send_keys(
            os.path.abspath(subtitles_filename)
        )

        # Select 'Educational video' genre.
        self.driver.find_element_by_css_selector(
            '#genre_id > option[value="10"]'
        ).click()

        # Submit whole form, which will redirect to Publish page.
        self.driver.find_element_by_id('addContentForm').submit()

        # Remove subtitles, because they are not needed anymore.
        os.remove(subtitles_filename)

        # Publish video, which will redirect to final page with video.
        # If Publish button does not exist, there could be 2 reasons:
        # - invalid input (error);
        # - video is processing (try again in loop).
        while True:
            try:
                self.driver.find_element_by_id('publicContentBtn').click()
                break
            except NoSuchElementException:
                if self.driver.current_url == 'http://lingualeo.com/ru/jungle/add':
                    raise AttributeError('Cannot submit form. '
                                         'Probably name is incorrect')
                else:
                    print '  Trying to publish: {}'.format(self.driver.current_url)
                    self.driver.refresh()

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

    @staticmethod
    def _download_video_subtitles(video_id):
        """Download English subtitles from video and return name of the SRT file.

        Args:
            video_id (str): ID of the video of which subtitiles are downloaded.

        Raises:
            AttributeError: if English subtitles not found.

        Returns:
            str: name of the SRT file where subtitles are located.
        """
        response = urllib2.urlopen(
            'http://video.google.com/timedtext?lang=en&v={}'.format(video_id)
        )
        xml_text = response.read()

        if not xml_text:
            raise AttributeError('English subtitles not found')

        # Replace all escaped characters with unicode.
        xml_text = HTMLParser().unescape(xml_text.decode('utf-8'))

        srt_text = xml2srt.convert(xml_text)

        subtitles_filename = '{}.srt'.format(video_id)
        with open(subtitles_filename, 'w') as outfile:
            outfile.write(srt_text.encode('utf8'))

        return subtitles_filename

    @staticmethod
    def _add_one_second(timestamp):
        """Add a second to time.

        Args:
            timestamp (str): time in ISO 8601 format.

        Returns:
            str: new timestamp
        """
        old_datetime = datetime.datetime.strptime(timestamp, ISO_8601_FORMAT)
        old_datetime += datetime.timedelta(seconds=1)
        return old_datetime.strftime(ISO_8601_FORMAT)

    @staticmethod
    def _generate_video_title(channel_name, video_title):
        """Concat channel name and video title.
        Take into special cases.

        Args:
            channel_name (str): name of the channel.
                Omitted, if equals to '-'.
            video_title (str): title of the video.
        """
        video_title.encode('utf-8')

        if channel_name == 'TEDEd':
            video_title = video_title.rsplit(' - ', 1)[0]

        if channel_name == '-':
            return video_title

        return channel_name + ' - ' + video_title

    @staticmethod
    def create_config(filename):
        data = dict()
        data['email'] = raw_input('Enter LinguaLeo email: ')
        data['password'] = raw_input('Enter LinguaLeo password: ')
        data['api_key'] = raw_input('Enter YouTube API key: ')
        data['channels'] = []
        data['extra_videos'] = []
        with open(filename, 'w') as outfile:
            json.dump(data, outfile, indent=4)

    @staticmethod
    def set_default_config(filename):
        if not os.path.exists(LeoUploader.INNER_CONFIG_NAME):
            with open(LeoUploader.INNER_CONFIG_NAME, 'w+'):
                pass

        with open(LeoUploader.INNER_CONFIG_NAME, 'r+') as infile:
            try:
                data = json.load(infile)
            except ValueError:
                data = {}
        data['config'] = os.path.abspath(filename)

        with open(LeoUploader.INNER_CONFIG_NAME, 'w') as outfile:
            json.dump(data, outfile)

        print 'Set default config: {}'.format(data['config'])

    @staticmethod
    def clear_extra_videos(config_name):
        with open(config_name) as infile:
            data = json.load(infile)

        extra_videos_count = len(data['extra_videos'])
        data['extra_videos'] = []

        with open(config_name, 'w') as outfile:
            json.dump(data, outfile, indent=4)

        print 'Cleared {} video(s)'.format(extra_videos_count)

    @staticmethod
    def get_default_config():
        with open(LeoUploader.INNER_CONFIG_NAME) as infile:
            return json.load(infile)['config']


def main():
    """Main function that launches automatically from command line."""
    parser = argparser.get_parser()
    args = parser.parse_args()

    if args.new_config_name:
        LeoUploader.create_config(args.new_config_name)

    if args.default_config_name:
        LeoUploader.set_default_config(args.default_config_name)
        return

    config = args.config or LeoUploader.get_default_config()

    try:
        if args.clear_extra:
            LeoUploader.clear_extra_videos(config)
            return

        leo_uploader = LeoUploader(config)
    except (IOError, KeyError, ValueError) as exception:
        print exception
        return

    if args.extra_videos or args.new_channels:
        if args.extra_videos:
            leo_uploader.write_extra_videos(args.extra_videos)

        if args.new_channels:
            leo_uploader.write_new_channels(args.new_channels)

        leo_uploader.save_config()
        return

    leo_uploader.load_new_videos()

    if leo_uploader.any_videos_to_upload():
        try:
            leo_uploader.sign_in()
        except CredentialsError as exception:
            print exception
            return

    try:
        leo_uploader.add_new_videos()
        leo_uploader.add_extra_videos()
    except (TimeoutException, ServerNotFoundError) as exception:
        print 'Network error:', exception
    finally:
        leo_uploader.save_config()


if __name__ == '__main__':
    main()
