import json
from copy import deepcopy

import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from leo.utils import get_videos_from_channel


class LeoUploader:

    def __init__(self, config_filename):
        """Initialize LeoUploader object.

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

        self.data = deepcopy(data)

        self.channels = data['channels']
        self.extra_videos = data['extra_videos']
        self.youtube = build('youtube', 'v3', developerKey=data['api_key'])

        self.cookies = None

    def signin(self):
        login_url = 'https://lingualeo.com/ru/uauth/dispatch'
        response = requests.post(login_url, {
            'email': self.data['email'],
            'password': self.data['password'],
            'type': 'login'
        })

        if response.status_code != requests.codes.ok:
            raise ValueError('Invalid credentials')

        self.cookies = response.cookies

    def load_new_videos(self):
        for channel in self.channels:
            try:
                channel['new_videos'] = get_videos_from_channel(self.youtube, channel['id'], channel['last_refresh'])
            except HttpError:
                print(f'Cannot get videos from channel "{channel["name"]}"')
                continue

    def upload_new_videos(self):
        for channel in self.channels:
            for video in sorted(channel['new_videos'], key=lambda x: x['published_at']):
                self.upload_video(video)

            if channel['new_videos']:
                c = next(c for c in self.data['channels'] if channel['id'] == c['id'])
                c['last_refresh']

    def upload_video(self, video):
        if self.cookies is None:
            self.signin()



    def run(self):
        self.load_new_videos()
        self.upload_new_videos()
