#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Convert XML subtitles to SRT format."""

from bs4 import BeautifulSoup


def convert(xml_text):
    """Convert XML subtitles to SRT format.

    Args:
        xml_text (str): subtitles in XML format.

    Returns:
        str: subtitles in SRT format.
    """
    soup = BeautifulSoup(xml_text, 'html.parser')
    captions = soup.find_all('text')

    lines = []
    for i, caption in enumerate(captions):
        start_time = float(caption['start'])
        end_time = start_time + float(caption['dur'])
        lines.append(str(i + 1))
        lines.append(_format_time(start_time) + ' --> ' + _format_time(end_time))
        lines.append(caption.text)
        lines.append('')

    return '\n'.join(lines)


def _format_time(seconds):
    """Format time to SRT standart.

    SRT standart looks like this: 00:00:00,000.

    Args:
        seconds (float): seconds after beginning of the video.

    Returns:
        str: formatted time.
    """
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    seconds, millisecs = divmod(seconds, 1)

    hours = int(round(hours))
    minutes = int(round(minutes))
    seconds = int(round(seconds))
    millisecs = int(round(millisecs * 1000))

    return '{hours:02d}:{minutes:02d}:{seconds:02d},{millisecs:03d}'.format(**locals())
