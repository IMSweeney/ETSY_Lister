from etsy2 import Etsy
from etsy2.oauth import EtsyOAuthClient, EtsyOAuthHelper

import logging
import webbrowser
import urllib.parse as urlparse
from urllib.parse import parse_qs


def get_api_key(f_name):
    with open(f_name) as f:
        key = f.readline()[:-1]
        shared_secret = f.readline()[:-1]
        oauth_token = f.readline()[:-1]
        oauth_secret = f.readline()[:-1]
        return {
            'key': key,  # Trim newline
            'shared_secret': shared_secret,
            # 'oauth_token': oauth_token,
            # 'oauth_secret': oauth_secret,
        }


def get_uid():
    with open('uid.txt') as f:
        user_id = f.readline()[:-1]
    return user_id


def oAuthHelper(api_key, shared_secret):
    # define permissions scopes as defined in the 'OAuth Authentication'
    #   section of the docs:
    #   https://www.etsy.com/developers/documentation/getting_started/oauth#section_permission_scopes
    permission_scopes = ['listings_r', 'listings_w']

    # In this case, user will be redirected to page on etsy that shows
    #   the verification code.
    login_url, temp_oauth_token_secret = EtsyOAuthHelper.get_request_url_and_token_secret(
        api_key, shared_secret, permission_scopes)

    query = urlparse.urlparse(login_url).query
    temp_oauth_token = parse_qs(query)['oauth_token'][0]

    webbrowser.open(login_url)

    ver = input('enter your verification code from Etsy: ')

    oauth_token, oauth_token_secret = EtsyOAuthHelper.get_oauth_token_via_verifier(
        api_key, shared_secret, temp_oauth_token,
        temp_oauth_token_secret, ver)

    return {
        'oauth_token': oauth_token,
        'oauth_secret': oauth_token_secret,
    }


def test():
    logging.info('Getting keys...')
    keys = get_api_key('key.txt')
    more_keys = oAuthHelper(keys['key'], keys['shared_secret'])
    keys.update(more_keys)

    logging.info('Creating API object...')
    etsy_oauth = EtsyOAuthClient(
        client_key=keys['key'],
        client_secret=keys['shared_secret'],
        resource_owner_key=keys['oauth_token'],
        resource_owner_secret=keys['oauth_secret']
    )
    etsy = Etsy(etsy_oauth_client=etsy_oauth)

    # TODO
    # etsy.createShippingTemplate()

    config = Config()
    create_listing(etsy, config)


class Config():
    def __init__(self):
        self.state = 'draft'
        self.description = 'Test listing description'
        self.title = 'Test listing title'
        self.quantity = 1
        self.price = 0.20
        self.taxonomy_id = 2350  # Dice tag maybe??
        self.who_made = ['i_did', 'collective', 'someone_else'][0]
        self.is_supply = True
        self.when_made = 'made_to_order'


def create_listing(etsy, config):
    print("Creating listing...")

    result = etsy.createListing(
        state=config.state,
        description=config.description,
        title=config.title,
        price=config.price,
        taxonomy_id=config.taxonomy_id,
        quantity=config.quantity,
        who_made=config.who_made,
        is_supply=config.is_supply,
        when_made=config.when_made,
    )
    listing_id = result[0]['listing_id']
    print("Created listing with listing id %d" % listing_id)
    # result = etsy.uploadListingImage(listing_id=listing_id, image=config.image_file)
    # print("Result of uploading image: %r" % result)


if __name__ == '__main__':
    test()
