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

import argparse
import datetime
from HTMLParser import HTMLParser
import json
import os
import urllib2

from apiclient.discovery import build
from apiclient.errors import HttpError
from httplib2 import ServerNotFoundError
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import xml2srt


YT_PREFIX = 'https://www.youtube.com/watch?v='


class CredentialsError(Exception):
    """Error with email or password."""
    pass


class LeoUploader(object):
    """Uploads YouTube video to LinguaLeo."""

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

            try:
                new_videos = self._get_new_videos(channel)
            except HttpError as exception:
                print 'Cannot get videos from channel "{}"'.format(channel['name'])
                continue

            if not new_videos:
                print '  No new videos'

            for video in sorted(new_videos, key=lambda x: x['published_at']):
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
        self.driver.get('http://lingualeo.com/ru/login')
        self.driver.find_element_by_name('email').send_keys(self.email)
        password_field = self.driver.find_element_by_name('password')
        password_field.send_keys(self.password)
        password_field.send_keys(Keys.RETURN)
        if self.driver.current_url == 'http://lingualeo.com/ru/login':
            raise CredentialsError('Invalid email and/or password')

    def save_config(self):
        """Save updated config to file."""
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
        pass

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
        except UserWarning as warning:
            print '  {}'.format(warning)
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
            channel_name + ' - ' + video['title']
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
        try:
            self.driver.find_element_by_id('addContentForm').submit()
        finally:
            os.remove(subtitles_filename)

        # Publish video, which will redirect to final page with video.
        # If Publish button does not exist, there could be 2 reasons:
        # - invalid input (error);
        # - video is processing (warn user, that video needs to be published).
        try:
            self.driver.find_element_by_id('publicContentBtn').click()
        except NoSuchElementException:
            if self.driver.current_url == 'http://lingualeo.com/ru/jungle/add':
                raise AttributeError('Cannot submit form. '
                                     'Probably name is incorrect')
            else:
                raise UserWarning('Need to publish: {}'.format(
                    self.driver.current_url
                ))
        finally:
            # Remove subtitles, because they are not needed anymore.
            os.remove(subtitles_filename)

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
        iso_8601_format = '%Y-%m-%dT%H:%M:%SZ'
        old_datetime = datetime.datetime.strptime(timestamp, iso_8601_format)
        old_datetime += datetime.timedelta(seconds=1)
        return old_datetime.strftime(iso_8601_format)


def main():
    """Main function that launches automatically from command line."""
    parser = argparse.ArgumentParser(
        description='Work with LinguaLeo video adding mechanism.'
    )

    parser.add_argument(
        '--extra',
        dest='extra_videos',
        metavar='VIDEO_URL',
        nargs='+',
        default=[],
        help='URLs to YouTube videos'
    )

    parser.add_argument(
        '--config',
        default='data.json',
        help='Name of the config file'
    )

    args = parser.parse_args()

    try:
        leo_uploader = LeoUploader(args.config)
    except (IOError, KeyError, ValueError) as exception:
        print exception
        return

    if args.extra_videos:
        leo_uploader.write_extra_videos(args.extra_videos)
        return

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
