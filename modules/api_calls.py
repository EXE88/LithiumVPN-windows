import requests
from modules.database import ManageDatabase

class ApiCalls:
    def __init__(self, base_url):
        self.base_url = base_url
        self.managedb = ManageDatabase()

    def _get_tokens(self):
        tokens = self.managedb.get_auth()
        return tokens or {}

    def _save_new_access(self, access_token):
        if not access_token:
            return False
        try:
            self.managedb.execute_database(f"UPDATE Auth SET access='{access_token}';")
            return True
        except Exception:
            return False

    def _refresh_access_token(self):
        tokens = self._get_tokens()
        refresh = tokens.get('refresh')
        if not refresh:
            return False
        try:
            r = requests.post(self.base_url + "/api/token/refresh/", json={"refresh": refresh})
        except requests.exceptions.RequestException:
            return False
        if r.status_code == 200:
            new_access = r.json().get('access')
            return self._save_new_access(new_access)
        return False

    def _request(self, method, endpoint, retry_on_401=True, **kwargs):
        """Centralized request helper.

        Returns a tuple: (ok: bool, response_or_message, status_code or None)

        - On success: (True, response_obj, response.status_code)
        - On failure: (False, 'human message', status_code_or_None)

        It will try to attach Authorization header if access token exists and
        on 401 will attempt a single refresh-and-retry using `_refresh_access_token()`.
        """
        tokens = self._get_tokens()
        headers = kwargs.pop('headers', {}) or {}
        access = tokens.get('access')
        if access:
            headers['Authorization'] = f"Bearer {access}"

        url = self.base_url + endpoint
        try:
            resp = requests.request(method, url, headers=headers, **kwargs)
        except requests.exceptions.RequestException:
            return False, "Network error.", None

        if resp.status_code == 401 and retry_on_401:
            refreshed = self._refresh_access_token()
            if not refreshed:
                return False, "Unauthorized. Please log in again.", 401

            tokens = self._get_tokens()
            new_access = tokens.get('access')
            if not new_access:
                return False, "Unauthorized. Please log in again.", 401

            headers['Authorization'] = f"Bearer {new_access}"
            try:
                resp2 = requests.request(method, url, headers=headers, **kwargs)
            except requests.exceptions.RequestException:
                return False, "Network error.", None

            if resp2.status_code == 401:
                return False, "Unauthorized. Please log in again.", 401
            return True, resp2, resp2.status_code

        return True, resp, resp.status_code

    def login_needed(self):
        tokens = self.managedb.get_auth()
        if tokens:
            if tokens.get('access') and tokens.get('refresh'):
                try:
                    access_validate = requests.post(
                        self.base_url + "/api/token/verify/",
                        json={"token": tokens['access']}
                    ).status_code

                    refresh_validate = requests.post(
                        self.base_url + "/api/token/verify/",
                        json={"token": tokens['refresh']}
                    ).status_code
                except requests.exceptions.RequestException:
                    return True

                if access_validate == 401:
                    if refresh_validate == 200:
                        try:
                            refresh_request = requests.post(
                                self.base_url + "/api/token/refresh/",
                                json={"refresh": tokens['refresh']}
                            )
                            if refresh_request.status_code == 200:
                                new_access_token = refresh_request.json().get('access')
                                if new_access_token:
                                    self.managedb.execute_database(f"UPDATE Auth SET access='{new_access_token}';")
                                    return False
                                else:
                                    return True
                            return True
                        except requests.exceptions.RequestException:
                            return True
                    else:
                        return True
                elif access_validate == 200:
                    return False
                else:
                    return True
            return True
        return True

    def login(self, username, password):
        if not username or not password:
            return False, "Missing required values."

        try:
            response = requests.post(
                self.base_url + "/api/token/",
                json={"username": username, "password": password}
            )
        except requests.exceptions.RequestException:
            return False, "Network error."

        if response.status_code == 200:
            data = response.json()
            access = data.get('access')
            refresh = data.get('refresh')

            if access and refresh:
                if self.managedb.get_auth() is None:
                    self.managedb.save_tokens_first_time(access, refresh)
                else:
                    self.managedb.execute_database(f"UPDATE Auth SET access='{access}', refresh='{refresh}';")
                return True, "Logged in successfully."
            else:
                return False, "Unexpected error."

        elif response.status_code == 401:
            return False, response.json().get('detail', "Unauthorized")

        else:
            return False, "Server error."

    def register(self, username, password, email):
        if not username or not password or not email:
            return False, "Missing required values."

        ok, resp, code = self._request("POST", "/accounts/register/", json={"username": username, "password": password, "email": email})
        if not ok:
            return False, resp
        if code == 201:
            return True, resp.json().get("info")
        return False, resp.json().get("error")

    def send_verifycation_code(self, email, code):
        if not email or not code:
            return False, "Missing required values."

        ok, resp, code = self._request("POST", "/accounts/verify-email/", json={"email": email, "code": code})
        if not ok:
            return False, resp
        if code == 200:
            return True, resp.json().get("info")
        return False, resp.json().get("error")

    def resend_verification_code(self, email):
        if not email:
            return False, "Missing required values."

        ok, resp, code = self._request("POST", "/accounts/resend-verification/", json={"email": email})
        if not ok:
            return False, resp

        if code == 200:
            return True, resp.json().get("info")

        if code == 429:
            data = resp.json()
            if "seconds_until_next_send" in data:
                secs = data["seconds_until_next_send"]
                minutes, seconds = divmod(secs, 60)
                return False, f"Please wait {minutes} minute(s) and {seconds} second(s) before requesting another code."
            elif "time_remaining_seconds" in data:
                secs = data["time_remaining_seconds"]
                minutes, seconds = divmod(secs, 60)
                message = data.get("message", "")
                return False, message or f"Verification code still valid. Time remaining: {minutes}m {seconds}s."
            else:
                return False, data.get("error", "Too many requests.")

        return False, resp.json().get("error", "Server error.")

    def get_user(self):
        ok, resp, code = self._request("GET", "/accounts/status/")
        if not ok:
            if code == 401:
                return False, "Unauthorized. Please log in again."
            return False, resp
        if code == 200:
            return True, resp.json()
        elif code == 401:
            return False, "Unauthorized. Please log in again."
        else:
            return False, "Server error."

    def get_plans(self):
        ok, resp, code = self._request("GET", "/plans/")
        if not ok:
            if code == 401:
                return False, "Unauthorized. Please log in again."
            return False, resp
        if code == 200:
            return True, resp.json()
        elif code == 401:
            return False, "Unauthorized. Please log in again."
        else:
            return False, "Server error."

    def buy_plan(self, plan_id):
        data = {"plan_id": plan_id}
        ok, resp, code = self._request("POST", "/plans/buy/", data=data)
        if not ok:
            if code == 401:
                return False, "Unauthorized. Please log in again."
            return False, resp

        if code == 200:
            return True, resp.json()
        elif code == 401:
            return False, "Unauthorized. Please log in again."
        elif code == 400:
            return False, resp.json().get('error')
        else:
            return False, "Server error."

        