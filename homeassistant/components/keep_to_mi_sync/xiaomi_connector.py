"""Connector."""

import base64
import hashlib
import hmac
import json
import os
import random
from urllib.parse import parse_qsl, urlparse

import requests


class XiaomiCloudConnector:
    """Cloud connector."""

    def __init__(self, username, password):
        """Init."""
        self._username = username
        self._password = password
        self._agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"
        # self._device_id = self.generate_device_id()
        self._device_id = "wb_12a8dc1b-4680-4877-9bc3-65c9431be567"
        self.session = requests.session()
        self._sign = None
        self._ssecurity = None
        self._userId = None
        self._cUserId = None
        self._passToken = None
        self._location = None
        self._code = None
        self._serviceToken = None
        self.cookies = None
        self._loginUrl = None
        self.params = None

    def login_step_1(self):
        """First login step."""
        url = "https://us.i.mi.com/api/user/login?ts=%d&followUp=https://us.i.mi.com/&_locale=en_US"
        headers = {
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://i.mi.com/",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "sec-ch-ua": '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
        }
        response = self.session.get(url, headers=headers)
        valid = (
            response.status_code == 200
            and "data" in self.to_json(response.text)
            and "loginUrl" in self.to_json(response.text)["data"]
        )
        if valid:
            self._loginUrl = self.to_json(response.text)["data"]["loginUrl"]
        else:
            return False
        r = self.session.get(self._loginUrl, headers=headers)
        u = urlparse(r.url)
        valid = r.status_code == 200 and u
        if valid:
            self.params = dict(parse_qsl(u.query))
        return valid

    def login_step_2(self):
        """Second login step."""
        url = "https://account.xiaomi.com/pass/serviceLoginAuth2"
        headers = {
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        fields = {
            "hash": hashlib.md5(str.encode(self._password)).hexdigest().upper(),
            "serviceParam": self.params.get("serviceParam"),
            "callback": self.params.get("callback"),
            "qs": self.params.get("qs"),
            "sid": self.params.get("sid"),
            "user": self._username,
            "_sign": self._sign,
            "_json": "true",
            "policyName": "globalmiaccount",
        }
        # response = self._session.post(url, headers=headers, params=fields,verify=False)
        response = self.session.post(url, headers=headers, data=fields)
        valid = response.status_code == 200 and "ssecurity" in self.to_json(
            response.text
        )
        if valid:
            json_resp = self.to_json(response.text)
            self._ssecurity = json_resp["ssecurity"]
            self._userId = json_resp["userId"]
            self._cUserId = json_resp["cUserId"]
            self._passToken = json_resp["passToken"]
            self._location = json_resp["location"]
            self._code = json_resp["code"]
        return valid

    def login_step_3(self):
        """Third login step."""
        headers = {
            "User-Agent": self._agent,
            "Referer": "https://us.i.mi.com/",
            "Upgrade-Insecure-Requests": "1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "sec-ch-ua": '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
        }
        # cookie = {
        #    "iplocale": "zh_CN",
        #    "uLocale": "zh_CN",
        # }
        response = self.session.get(self._location, headers=headers)
        if response.status_code == 200:
            self._serviceToken = self.session.cookies.get("serviceToken")
        return response.status_code == 200

    def login(self):
        """Login."""
        self.session.cookies.set("deviceId", self._device_id, domain="mi.com")
        self.session.cookies.set("deviceId", self._device_id, domain="xiaomi.com")
        if self.login_step_1():
            if self.login_step_2():
                if self.login_step_3():
                    return True
        #        else:
        #            print("Unable to get service token.")
        #    else:
        #        print("Invalid login or password.")
        # else:
        #    print("Invalid username.")
        return False

    def updateRecord(self, record):
        """Update Record."""
        record_id = record["id"]
        formData = {
            "previousETag": record["eTag"],
            "serviceToken": self.session.cookies.get("serviceToken"),
            "record": json.dumps(record),
        }
        headers = {"User-Agent": self._agent}
        url = "https://us.i.mi.com/todo/v1/user/records/" + record_id + "/update"
        response = self.session.post(url, headers=headers, data=formData)
        return response

    def signed_nonce(self, nonce):
        """Signed nonce."""
        hash_object = hashlib.sha256(
            base64.b64decode(self._ssecurity) + base64.b64decode(nonce)
        )
        return base64.b64encode(hash_object.digest()).decode("utf-8")

    @staticmethod
    def generate_nonce(millis):
        """Generate nonce."""
        nonce_bytes = os.urandom(8) + (int(millis / 60000)).to_bytes(4, byteorder="big")
        return base64.b64encode(nonce_bytes).decode()

    @staticmethod
    def generate_agent():
        """Generate user agent."""
        agent_id = "".join(chr(i) for i in [random.randint(65, 69) for _ in range(13)])
        return f"Android-7.1.1-1.0.0-ONEPLUS A3010-136-{agent_id} APP/xiaomi.smarthome APPV/62830"

    @staticmethod
    def generate_device_id():
        """Generate device id."""
        # return "".join(map(lambda i: chr(i), [random.randint(97, 122) for _ in range(6)]))
        hex_vars = [
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "a",
            "b",
            "c",
            "d",
            "e",
            "f",
        ]
        return (
            "wb_"
            + "".join(random.sample(hex_vars, 8))
            + "-"
            + "".join(random.sample(hex_vars, 4))
            + "-"
            + "".join(random.sample(hex_vars, 4))
            + "-"
            + "".join(random.sample(hex_vars, 4))
            + "-"
            + "".join(random.sample(hex_vars, 12))
        )
        # 类似： 'wb_a325c1b8-60ba-975f-fea1-2ae734581fb0'

    @staticmethod
    def generate_signature(url, signed_nonce, nonce, params):
        """Generate signature."""
        signature_params = [url.split("com")[1], signed_nonce, nonce]
        for k, v in params.items():
            signature_params.append(f"{k}={v}")
        signature_string = "&".join(signature_params)
        signature = hmac.new(
            base64.b64decode(signed_nonce),
            msg=signature_string.encode(),
            digestmod=hashlib.sha256,
        )
        return base64.b64encode(signature.digest()).decode()

    @staticmethod
    def to_json(response_text):
        """Convert to json."""
        try:
            return json.loads(response_text.replace("&&&START&&&", ""))
        except TypeError:
            # print(e)
            # print(response_text)
            return response_text
