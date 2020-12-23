from etsy2 import Etsy
from etsy2.oauth import EtsyOAuthClient, EtsyOAuthHelper

import logging
import os
import webbrowser
import json
import urllib.parse as urlparse
from urllib.parse import parse_qs

import PySimpleGUI as sg


class EtsyHelper():
    def __init__(self):
        sg.theme('dark grey 9')

        self.data = r'data'
        create_dir(self.data)
        self.templates = os.path.join(self.data, 'templates')
        create_dir(self.templates)

        self.etsy = self.init_etsy()

        self.shipping_templates = self.read_shipping_templates()
        self.listing_templates = self.read_listing_templates()
        # self.shipping_templates = {}
        # self.listing_templates = {}
        layout = self.generate_layout(
            list(self.shipping_templates.keys()),
            list(self.listing_templates.keys()))

        self.window = sg.Window(self.__class__.__name__, layout)

    def init_etsy(self):
        logging.info('Getting keys...')
        key_file = os.path.join(self.data, 'keys.txt')
        keys = self.get_api_key(key_file)
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
        try:
            with open(f_name, 'r') as f:
                keys = json.load(f)
                logging.info('read {} from {}'.format(keys, f_name))
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            keys = {}
            msg = 'Enter your api key: '
            keys['key'] = sg.popup_get_text(msg)
            if not keys['key']:
                raise ValueError('Need api key: https://www.etsy.com/developers/your-apps')

            msg = 'Enter your shared secret: '
            keys['shared_secret'] = sg.popup_get_text(msg)
            if not keys['shared_secret']:
                raise ValueError('Need api key: https://www.etsy.com/developers/your-apps')

            with open(f_name, 'w') as f:
                json.dump(keys, f)

        return keys

    def get_uid(self, f_name):
        try:
            with open(f_name) as f:
                user_id = json.load(f)
                logging.info('read {} from {}'.format(user_id, f_name))
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            msg = 'enter your user id: '
            user_id = sg.popup_get_text(msg)
            if not user_id:
                raise ValueError('Need user id')

            with open(f_name, 'w') as f:
                json.dump(user_id, f)

        return user_id

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
                           key='--ListingTemplate--'),
             sg.Button('New Template')],
            [sg.Text('Choose a number of coppies: '),
             sg.Spin([i for i in range(10)],
                     key='--NumListings--')],
            [sg.Text(size=(80, 1), key='--OUTPUT--')],
            [sg.Button('Create'), sg.Button('Quit')],
        ]
        return layout

    def read_shipping_templates(self):
        uid_file = os.path.join(self.data, 'uid.txt')
        uid = self.get_uid(uid_file)
        res = self.etsy.findAllUserShippingProfiles(user_id=uid)
        shipping_templates = {}
        for template in res:
            shipping_templates[template['title']] = template

        return shipping_templates

    def read_listing_templates(self):
        listing_templates = {}
        logging.info('Reading templates from {}'.format(self.templates))
        for file in os.listdir(self.templates):
            f_name = os.path.join(self.templates, file)
            with open(f_name, 'r') as f:
                template = json.load(f)
                title = template['title']
                listing_templates[title] = template
        return listing_templates

    def create_listing_template(self):
        params = [
            ('title', 'str', True),
            ('description', 'str', True),
            ('quantity', 'int', True),
            ('price', 'float', True),
            ('taxonomy_id', 'int', True),
            ('who_made', ['i_did', 'collective', 'someone_else'], True),
            ('is_supply', 'bool', True),
            ('when_made', ['made_to_order'], True),
        ]
        layout = []
        for param, type_str, required in params:
            label = sg.Text('{}: '.format(param))
            if type_str in ['str', 'int', 'float']:
                block = sg.InputText(key=param)
            elif type_str == 'bool':
                block = sg.Checkbox('', key=param)
            elif isinstance(type_str, list):
                block = sg.Combo(type_str, key=param)
            else:
                logging.error('{} not supported'.format(type_str))
            layout.append([label, block])

        layout.append(
            [sg.Button('Save')]
        )

        window = sg.Window('New Template', layout)

        while True:
            event, values = window.read()
            if event == sg.WINDOW_CLOSED or event == 'Quit':
                break
            elif event == 'Save':
                try:
                    self.save_listing_template(params, values)
                    break
                except (KeyError, TypeError) as e:
                    logging.error(e)
                    sg.Popup(title='Error: {}'.format(e))

        window.close()

    def save_listing_template(self, params, values):
        template = {}
        for param, type_str, required in params:
            if required and not values[param]:
                raise KeyError('{} not specified'.format(param))
            elif param in values:
                if type_str == 'int':
                    template[param] = int(values[param])
                elif type_str == 'float':
                    template[param] = float(values[param])
                else:
                    template[param] = (values[param])

        f_name = os.path.join(self.templates, values['title'])
        with open(f_name, 'w') as f:
            json.dump(template, f)

    def create_listings(self, values):
        template = values['--ShippingTemplate--']
        ship_id = self.shipping_templates[template]['shipping_template_id']

        template = values['--ListingTemplate--']
        config = self.listing_templates[template]

        num_listings = values['--NumListings--']

        logging.info("Creating listing...")

        kwargs = config.copy()
        kwargs.update({
            'state': 'draft',
            'shipping_template_id': ship_id
        })

        base_title = kwargs['title']
        for i in range(num_listings):
            kwargs['title'] = base_title + '_{}'.format(i)
            result = self.etsy.createListing(**kwargs)

        listing_id = result[0]['listing_id']
        return listing_id

    def run(self):
        while True:
            event, values = self.window.read()
            if event == sg.WINDOW_CLOSED or event == 'Quit':
                break

            elif event == 'Create':
                try:
                    list_id = self.create_listings(values)
                    logging.info('created listing {} from {}'.format(
                        list_id, values))
                except FileNotFoundError as e:
                    logging.error(e)

            elif event == 'New Template':
                self.create_listing_template()

                logging.info('Regenerating window with new template')
                self.listing_templates = self.read_listing_templates()
                layout = self.generate_layout(
                    list(self.shipping_templates.keys()),
                    list(self.listing_templates.keys()))

                self.window = sg.Window(self.__class__.__name__, layout)

        self.window.close()


def create_dir(path):
    try:
        os.mkdir(path)
    except OSError:
        pass


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


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = EtsyHelper()
    app.run()
