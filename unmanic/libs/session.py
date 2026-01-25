#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.session.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     10 Mar 2021, (5:20 PM)

    Copyright:
           Copyright (C) Josh Sunnex - All Rights Reserved

           Permission is hereby granted, free of charge, to any person obtaining a copy
           of this software and associated documentation files (the "Software"), to deal
           in the Software without restriction, including without limitation the rights
           to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
           copies of the Software, and to permit persons to whom the Software is
           furnished to do so, subject to the following conditions:

           The above copyright notice and this permission notice shall be included in all
           copies or substantial portions of the Software.

           THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
           IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
           DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
           OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
           OR OTHER DEALINGS IN THE SOFTWARE.

"""
import base64
import datetime
import pickle
import random
import time

import requests

from unmanic import config
from unmanic.libs import common, unlogger
from unmanic.libs.singleton import SingletonType
from unmanic.libs.unmodels import Installation


class RemoteApiException(Exception):
    """
    RemoteApiException
    Custom exception for errors contacting the remote Unmanic API
    """

    def __init__(self, message, status_code):
        super().__init__(f"Session Error - Remote API [CODE: {status_code}]: {message}")


class Session(object, metaclass=SingletonType):
    """
    Session

    Manages the Unmanic applications session for unlocking
    features and fetching data from the Unmanic site API.

    """

    """
    picture_uri - The user avatar
    """
    picture_uri = ''

    """
    name - The user's name
    """
    name = ''

    """
    email - The user's email
    """
    email = ''

    """
    created - The timestamp when the session was created
    """
    created = None

    """
    last_check - The timestamp when the session was last checked
    """
    last_check = None

    """
    uuid - This installation's UUID
    """
    uuid = None

    """
    session_cookies - A stored copy of the session cookies to persist between restarts
    """
    session_cookies = None

    def __init__(self, *args, **kwargs):
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        self.logger = unmanic_logging.get_logger(__class__.__name__)
        self.timeout = 30
        self.dev_api = kwargs.get('dev_api', None)
        self.requests_session = requests.Session()
        self.logger.info('Initialising new session object')

    def __update_created_timestamp(self):
        """
        Update the session "created" timestamp.

        :return:
        """
        # Get the time now in seconds
        seconds = time.time()
        # Create a seconds offset of some random number between 300 (5 mins) and 900 (15 mins)
        seconds_offset = random.randint(300, 900 - 1)
        # Set the created flag with the seconds variable plus a random offset to avoid people joining
        #   together to register if the site goes down
        self.created = (seconds + seconds_offset)
        # Print only the accurate update time in debug log
        created = datetime.datetime.fromtimestamp(seconds)
        self.logger.debug('Updated session at %s', str(created))

    def __fetch_installation_data(self):
        """
        Fetch installation data from DB

        :return:
        """
        # Fetch installation
        db_installation = Installation()
        try:
            # Fetch a single row (get() will raise DoesNotExist exception if no results are found)
            current_installation = db_installation.select().order_by(Installation.id.asc()).limit(1).get()
        except Exception:
            # Create settings (defaults will be applied)
            self.logger.debug('Unmanic session does not yet exist... Creating.')
            db_installation.delete().execute()
            current_installation = db_installation.create()

        self.uuid = str(current_installation.uuid)
        self.level = int(current_installation.level)
        self.picture_uri = str(current_installation.picture_uri)
        self.name = str(current_installation.name)
        self.email = str(current_installation.email)
        self.created = current_installation.created if current_installation.created else None
        if isinstance(self.created, datetime.datetime):
            self.created = self.created.timestamp()

        self.__update_session_auth(access_token=current_installation.user_access_token,
                                   session_cookies=current_installation.session_cookies)

    def __store_installation_data(self, force_save_access_token=False):
        """
        Store installation data in DB to persist reboot

        :return:
        """
        if self.uuid:
            db_installation = Installation.get_or_none(uuid=self.uuid)
            db_installation.level = self.level
            db_installation.picture_uri = self.picture_uri
            db_installation.name = self.name
            db_installation.email = self.email
            db_installation.created = self.created
            if self.user_access_token or force_save_access_token:
                db_installation.user_access_token = self.user_access_token
            if self.user_refresh_token or force_save_access_token:
                db_installation.user_refresh_token = self.user_refresh_token
            if self.session_cookies or force_save_access_token:
                db_installation.session_cookies = self.session_cookies
            db_installation.save()

    def __reset_session_installation_data(self):
        """
        Reset stored session data

        :return:
        """
        self.logger.debug('Resetting session installation data.')
        self.level = 0
        self.picture_uri = ''
        self.name = ''
        self.email = ''
        self.created = time.time()
        self.user_access_token = None
        self.user_refresh_token = None
        self.__store_installation_data(force_save_access_token=True)
        self.__clear_session_auth()

    def __update_session_auth(self, access_token=None, session_cookies=None):
        # Update session headers
        if access_token:
            self.user_access_token = access_token
            self.requests_session.headers.update({'Authorization': self.user_access_token})
        # Update session cookies
        if session_cookies:
            self.session_cookies = session_cookies
            try:
                self.requests_session.cookies = pickle.loads(base64.b64decode(session_cookies))
            except Exception as e:
                self.logger.error('Error trying to reload session cookies - %s', str(e))

    def __clear_session_auth(self):
        self.requests_session.cookies.clear()
        self.requests_session.headers.update({'Authorization': ''})

    def get_installation_uuid(self):
        """
        Returns the installation UUID as a string.
        If it does not yet exist, it will create one.

        :return:
        """
        if not self.uuid:
            self.__fetch_installation_data()
        return self.uuid

    def sign_out(self):
        """
        Remove any user auth

        :return:
        """

        self.__reset_session_installation_data()
        return True