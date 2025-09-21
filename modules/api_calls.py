import requests
from database import ManageDatabase

class ApiCalls:
    def __init__(self, base_url):
        self.base_url = base_url
        self.managedb = ManageDatabase()

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
                                    self.managedb.execute_database(f"UPDATE auth SET access = {new_access_token};")
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
                self.managedb.execute_database(
                    f"UPDATE auth SET access = '{access}', refresh = '{refresh}';"
                )
                return True, "Logged in successfully."
            else:
                return False, "Unexpected error."

        elif response.status_code == 401:
            return False, response.json().get('detail', "Unauthorized")

        else:
            return False, "Server error."
        
    def register(self,username,password,email):
        if not username or not password or not email:
            return False, "Missing required values."
        
        try:
            register_request = requests.post(
                self.base_url + "/accounts/register/",
                json={"username":username,"password":password,"email":email}
            )
        except requests.exceptions.RequestException:
            return False, "Network error."
        
        if register_request.status_code==201:
            return True, register_request.json().get("info")
        return False, register_request.json().get("error")
    
    def send_verifycation_code(self,email,code):
        if not email or not code:
            return False, "Missing required values."
        
        try:
            verify_request = requests.post(
                self.base_url + "/accounts/verify-email/",
                json={"email":email,"code":code}
            )
        except requests.exceptions.RequestException:
            return False, "Network error."
        
        if verify_request.status_code==200:
            return True, verify_request.json().get("info")
        return False, verify_request.json().get("error")
    
    def resend_verification_code(self, email):
        if not email:
            return False, "Missing required values."

        try:
            resend_code_request = requests.post(
                self.base_url + "/accounts/resend-verification/",
                json={"email": email}
            )
        except requests.exceptions.RequestException:
            return False, "Network error."

        if resend_code_request.status_code == 200:
            return True, resend_code_request.json().get("info")

        elif resend_code_request.status_code == 429:
            data = resend_code_request.json()

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

        else:
            return False, resend_code_request.json().get("error", "Server error.")

        