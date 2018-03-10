# LinguaLeo-Uploader
Automated content addition to LinguaLeo from favorite YouTube channels.

## Installation

Install dependencies:
```
$ python setup.py install
```

Install [chromedriver](https://sites.google.com/a/chromium.org/chromedriver/home).
Instructions can be found [here](https://developers.supportbee.com/blog/setting-up-cucumber-to-run-with-Chrome-on-Linux/).

## Configuration

Create config file for storing information about your profile and channels.
```
$ leo --create-config
```
You'll be prompted to enter your LinguaLeo email, password and YouTubeAPI key.

Get API key from [Developers Console](https://console.developers.google.com).

Then you can add your favorite channels to the config. Use `--channel` flag for this:
```
$ leo --channel https://www.youtube.com/channel/UCLXo7UDZvByw2ixzpQCufnA
```
Or:
```
$ leo --channel https://www.youtube.com/user/voxdotcom
```

## Usage

After that, you can start using the application for its initial purpose.

```
$ leo
```

Note that only those videos that were published **after** adding channel will be uploaded.

You can manually edit last_refresh attribute in your config file or load videos you want with this interface:
```
$ leo --extra https://www.youtube.com/watch?v=BXmyPsqkP44 https://www.youtube.com/watch?v=LVWTQcZbLgY
```

For other options, check out help message:
```
$ leo --help
```
