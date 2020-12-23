from etsy2 import Etsy
from etsy2.oauth import EtsyOAuthClient, EtsyOAuthHelper

import logging
import webbrowser
import urllib.parse as urlparse
from urllib.parse import parse_qs

import PySimpleGUI as sg


class EtsyHelper():
    def __init__(self):
        self.etsy = self.init_etsy()
        sg.theme('dark grey 9')

        self.shipping_templates = self.read_shipping_templates()
        self.listing_templates = self.read_listing_templates()
        layout = self.generate_layout(
            list(self.shipping_templates.keys()),
            list(self.listing_templates.keys()))

        self.window = sg.Window(self.__class__.__name__, layout)

    def init_etsy(self):
        logging.info('Getting keys...')
        keys = self.get_api_key('key.txt')
        more_keys = self.oAuthHelper(keys['key'], keys['shared_secret'])
        keys.update(more_keys)

        logging.info('Creating API object...')
        etsy_oauth = EtsyOAuthClient(
            client_key=keys['key'],
            client_secret=keys['shared_secret'],
            resource_owner_key=keys['oauth_token'],
            resource_owner_secret=keys['oauth_secret']
        )
        etsy = Etsy(etsy_oauth_client=etsy_oauth)
        return etsy

    def get_api_key(self, f_name):
        with open(f_name) as f:
            key = f.readline()[:-1]  # Trim newline
            shared_secret = f.readline()[:-1]
            return {
                'key': key,
                'shared_secret': shared_secret,
            }

    def oAuthHelper(self, api_key, shared_secret):
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

        # ver = input('enter your verification code from Etsy: ')
        msg = 'enter your verification code from Etsy: '
        ver = sg.popup_get_text(msg)
        if not ver:
            raise ValueError('Need verification code')

        oauth_token, oauth_token_secret = EtsyOAuthHelper.get_oauth_token_via_verifier(
            api_key, shared_secret, temp_oauth_token,
            temp_oauth_token_secret, ver)

        return {
            'oauth_token': oauth_token,
            'oauth_secret': oauth_token_secret,
        }

    def generate_layout(self, shipping_templates, listing_templates):
        layout = [
            [sg.Text('Choose a shipping template')],
            [sg.InputCombo(values=shipping_templates,
                           key='--ShippingTemplate--')],
            [sg.Text('Choose a listing template')],
            [sg.InputCombo(values=listing_templates,
                           key='--ListingTemplate--')],
            [sg.Text('Choose a number of coppies: '),
             sg.Spin([i for i in range(10)],
                     key='--NumListings--')],
            [sg.Text(size=(80, 1), key='--OUTPUT--')],
            [sg.Button('Create'), sg.Button('Quit')],
        ]
        return layout

    def read_shipping_templates(self):
        uid = get_uid()
        res = self.etsy.findAllUserShippingProfiles(user_id=uid)
        shipping_templates = {}
        for template in res:
            shipping_templates[template['title']] = template

        return shipping_templates

    def read_listing_templates(self):
        return {}

    def create_listings(self, values):
        template = values['--ShippingTemplate--']
        ship_id = self.shipping_templates[template]

        template = values['--ListingTemplate--']
        config = self.shipping_templates[template]

        num_listings = values['--NumListings--']
        logging.error('Num listings not yet used')

        print("Creating listing...")

        result = self.etsy.createListing(
            state=config.state,
            description=config.description,
            title=config.title,
            price=config.price,
            taxonomy_id=config.taxonomy_id,
            quantity=config.quantity,
            who_made=config.who_made,
            is_supply=config.is_supply,
            when_made=config.when_made,
            shipping_template_id=ship_id,
        )
        listing_id = result[0]['listing_id']
        print("Created listing with listing id %d" % listing_id)

    def run(self):
        while True:
            event, values = self.window.read()
            if event == sg.WINDOW_CLOSED or event == 'Quit':
                break

            if event == 'Create':
                self.create_listings(values)
                out = 'UNF - will create listing here'
                self.window['--OUTPUT--'].update(out)

        self.window.close()


def get_uid():
    with open('uid.txt') as f:
        user_id = f.readline()[:-1]
    return user_id


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
    shipping_template_id = create_shipping_template(etsy)
    # result = etsy.getShippingTemplate(
    #     shipping_template_id=shipping_template_id)
    # print(result)

    config = Config()
    create_listing(etsy, config, shipping_template_id)


def create_shipping_template(etsy):
    try:
        shipping_template = etsy.createShippingTemplate(
            title='ShippingTemplateTest',
            origin_country_id=209,  # US country code
            primary_cost=1.00,
            secondary_cost=0.00,
        )
        shipping_template_id = shipping_template[0]['shipping_template_id']
        with open('shipping_template.txt', 'w') as f:
            f.write(shipping_template_id)
    except ValueError:
        with open('shipping_template.txt') as f:
            shipping_template_id = int(f.readline()[:-1])  # Template id
            # shipping_template_id = f.readline()[:-1]  # Entry id

    return shipping_template_id


class Config():
    def __init__(self):
        self.state = 'inactive'
        self.description = 'Test listing description'
        self.title = 'Test listing title'
        self.quantity = 1
        self.price = 0.20
        self.taxonomy_id = 2350  # Dice tag maybe??
        self.who_made = ['i_did', 'collective', 'someone_else'][0]
        self.is_supply = True
        self.when_made = 'made_to_order'


def create_listing(etsy, config, shipping_template_id):
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
        shipping_template_id=shipping_template_id,
    )
    listing_id = result[0]['listing_id']
    print("Created listing with listing id %d" % listing_id)
    # result = etsy.uploadListingImage(listing_id=listing_id, image=config.image_file)
    # print("Result of uploading image: %r" % result)


if __name__ == '__main__':
    app = EtsyHelper()
    app.run()
