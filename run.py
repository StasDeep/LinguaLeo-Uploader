from os.path import dirname, abspath, join

from leo.leo_uploader import LeoUploader


def main():
    config_filename = join(dirname(abspath(__file__)), 'data.json')
    leo = LeoUploader(config_filename)
    leo.run()


if __name__ == '__main__':
    main()
