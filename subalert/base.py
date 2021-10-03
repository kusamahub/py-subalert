import json
import uuid, random
import urllib.request
from urllib.request import urlopen

import tweepy
import yaml
from PIL import Image, ImageDraw, ImageFont
from substrateinterface import SubstrateInterface


class Configuration:
    def __init__(self):
        self.yaml_file = yaml.safe_load(open("config.local.yaml", "r"))
        self.substrate = SubstrateInterface(
            url=self.yaml_file['chain']['url'],
            ss58_format=self.yaml_file['chain']['ss58_format'],
            type_registry_preset=self.yaml_file['chain']['type_registry_preset']
        )

        # Authenticate to Twitter
        self.auth = tweepy.OAuthHandler(self.yaml_file['twitter']['OAuthHandler']['consumer_key'],
                                        self.yaml_file['twitter']['OAuthHandler']['consumer_secret'])
        self.auth.set_access_token(self.yaml_file['twitter']['access_token']['key'],
                                   self.yaml_file['twitter']['access_token']['secret'])

        # Create API object
        self.api = tweepy.API(self.auth)


config = Configuration()
hashtag = config.yaml_file['twitter']['hashtag']
substrate = config.substrate


class SubQuery:
    @staticmethod
    def check_super_of(address):
        """
        :param address:
        :return: The super-identity of an alternative 'sub' identity together with its name, within that
        """
        result = substrate.query(
            module='Identity',
            storage_function='SuperOf',
            params=[address])

        if result.value is not None:
            return result.value[0]
        else:
            return 0

    def check_identity(self, address):
        """
        :param address:
        :return: Information that is pertinent to identify the entity behind an account.
        """
        identification = ''
        result = substrate.query_map(
            module='Identity',
            storage_function='IdentityOf')

        super_of = self.check_super_of(address)
        if super_of:
            address = super_of

        for identity_address, information in result:
            # print(f">>> {identity_address.value}")
            if address == identity_address.value:
                for identity_type, values in information.value['info'].items():
                    if 'display' in identity_type or 'twitter' in identity_type:
                        for value_type, value in values.items():
                            if identity_type == 'display' and value_type == 'Raw':
                                identification += f"{value} "

                            if identity_type == 'twitter' and value_type == 'Raw':
                                identification += f"/ {value}"

        # Return address if no identity has been setup
        if identification == '':
            return address
        else:
            return identification


class Imagify:
    def __init__(self, title, text: str):
        self.title = title
        self.text = text.encode("ascii", errors="ignore").decode()

    def create(self):
        watermark = Image.open(f'logos/{hashtag}_White.png')
        new_watermark = watermark.resize((75, 75), Image.ANTIALIAS)
        guid = uuid.uuid4()
        imagify_path = f"logos/Imagify/{guid}.png"

        # background
        new_image = Image.new('RGBA', (400, 300), color='#36393f')
        new_image_draw = ImageDraw.Draw(new_image)

        # text font settings
        text_font = ImageFont.truetype(font="fonts/SourceCodePro-Regular.ttf", size=16)
        text_w, text_h = new_image_draw.textsize(self.text, text_font)

        # title font settings
        title_font = ImageFont.truetype(font="fonts/SourceCodePro-Bold.ttf", size=22)
        title_w, title_h = new_image_draw.textsize(self.title, title_font)

        # resize if title_width is larger than text_width
        if title_w > text_w:
            modified_image = new_image.resize(size=(title_w + 75, text_h + 75))
            modified_image_draw = ImageDraw.Draw(modified_image)
        else:
            modified_image = new_image.resize(size=(text_w + 75, text_h + 75))
            modified_image_draw = ImageDraw.Draw(modified_image)

        modified_image.paste(new_watermark, (modified_image.width - 75, text_h), mask=new_watermark)
        modified_image_draw.text(xy=((modified_image.width - title_w) / 2, 10), text=self.title,
                                 fill='#d1d0b0', font=title_font)
        modified_image_draw.text(xy=(10, 75), text=self.text,
                                 fill='#d1d0b0', font=text_font)
        modified_image.save(imagify_path)
        return imagify_path


class Numbers:
    def __init__(self, number):
        self.number = number
        self.magnitude = int()

    def human_format(self):
        magnitude = 0
        while abs(self.number) >= 1000:
            magnitude += 1
            self.number /= 1000.0
        # add more suffixes if you need them
        return '%.2f%s' % (self.number, ['', 'K', 'M', 'B', 'T', 'P'][magnitude])

    def large_to_dec(self):
        magnitude = 0
        while abs(self.number) >= 1000:
            magnitude += 1
            self.number /= 1000.0
        return '%.2f' % self.number


class Queue:
    def __init__(self):
        self.items = []

    def is_empty(self):
        return self.items == []

    def enqueue(self, item):
        self.items.insert(0, item)

    def dequeue(self):
        return self.items.pop()

    def size(self):
        return len(self.items)


class Utils:
    @staticmethod
    def cache_data(filename, data):
        with open(f"{filename}", 'w') as cache:
            cache.write(json.dumps(data, indent=4))
        cache.close()

    @staticmethod
    def open_cache(filename):
        with open(filename, 'r') as cache:
            cached_file = json.loads(cache.read())
            cache.close()
        return cached_file

    @staticmethod
    def get_1kv_candidates():
        candidates = []
        header = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'}
        request = urllib.request.Request(config.yaml_file['validator_programme_url'], headers=header)
        response = json.loads(urlopen(request).read())

        for candidate in response:
            candidates.append(candidate['stash'])

        return candidates


class CoinGecko:
    def __init__(self, coin: str, currency):
        self.coin = coin.lower()
        self.currency = currency
        self.url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd&C{currency}"

    def price(self):
        api_response = json.loads(urlopen(url=self.url, timeout=60).read())
        return '${:,.2f}'.format(api_response[self.coin][self.currency])


class Tweet:
    @staticmethod
    def tweet_media(filename, message):
        try:
            config.api.update_with_media(filename, f"{message} #{hashtag}")
            print("🐤 tweet successfully sent!")
        except Exception as err:
            print(err)

    @staticmethod
    def alert(message):
        try:
            config.api.update_status(f"{message} #{hashtag}")
            print("🐤 tweet successfully sent!")
        except tweepy.error.TweepError as error:
            if error == "[{'code': 187, 'message': 'Status is a duplicate.'}]":
                print("Disregarding duplicate tweet")
                pass
            else:
                raise error


class GitWatch:
    @staticmethod
    def latest_release():
        with urllib.request.urlopen(config.yaml_file['github']['repository']) as repository:
            data = json.loads(repository.read().decode())
            return data

    @staticmethod
    def cache_release(data):
        with open('git-release.cache', 'w') as cache:
            cache.write(json.dumps(data, indent=4))
        cache.close()

    @staticmethod
    def has_updated(data, cache):
        if data['tag_name'] != cache['tag_name']:
            print("🔧 new release found!")
            return True
        else:
            print("🔧 no releases found")
            return False
