def get_videos_from_channel(yt_client, channel_id, after_date):
    search_response = yt_client.search().list(
        part='id, snippet',
        type='video',
        channelId=channel_id,
        publishedAfter=after_date,
        maxResults=50
    ).execute()

    return [{
        'id': item['id']['videoId'],
        'published_at': item['snippet']['publishedAt'],
        'title': item['snippet']['title']
    } for item in search_response['items']]
