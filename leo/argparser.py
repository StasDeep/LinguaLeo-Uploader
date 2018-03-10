# -*- coding: utf-8 -*-
import argparse


def get_parser():
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
        help='Name of the config file'
    )

    parser.add_argument(
        '--channel',
        dest='new_channels',
        metavar='CHANNEL',
        nargs='+',
        default=[],
        help='URLs to YouTube channels'
    )

    parser.add_argument(
        '--create-config',
        dest='new_config_name',
        nargs='?',
        const='data.json',
        help='Create new config file (data.json is default name)'
    )

    parser.add_argument(
        '--set-default-config',
        dest='default_config_name',
        help='Set config file as a default config'
    )

    parser.add_argument(
        '--clear-extra',
        action='store_true',
        help='Clear extra videos from config'
    )

    return parser
