# Copyright (c) 2024 ServiceNow, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from pysnc import ServiceNowClient
import re
import time
import traceback
import requests
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.common.exceptions import TimeoutException

def get_instance_url(instance:str):
    """
    Return a instance URL

    :param instance (str): A string representing a instance name or URL
    :return: The full instance URL
    :rtype: str
    """
    if '://' in instance:
        return instance.rstrip('/')
    return f"https://{instance}.service-now.com"

def get_instance_name(instance:str):
    """
    Return a instance name

    :param instance (str): A string representing a instance name or URL
    :return: The instance name
    :rtype: str
    """
    if '://' in instance:
        return re.sub(r"^[^:]+://", "", instance).split('.')[0]
    return instance

def get_new_snc_args(instance:str, snc_args:dict):
    if 'instance' in snc_args:
        del snc_args['instance']
    snc_args['instance'] = instance
    snc = ServiceNowClient(**snc_args)
    return snc

def get_new_snc_basic_auth(instance:str, username:str, password:str, snc_args:dict = None):
    if username is None or password is None:
        raise ValueError("username and password cannot be null.")
    if not isinstance(username, str) or not isinstance(password, str):
        raise TypeError("username and password must be a string.")
    if len(username) == 0 or len(password) == 0:
        raise ValueError("username and password must be non-empty.")
    
    if snc_args is None:
        snc_args = {}
    
    if 'auth' in snc_args:
        del snc_args['auth']
    
    if 'cert' in snc_args:
        del snc_args['cert']
        
    if 'instance' in snc_args:
        del snc_args['instance']
        
    snc_args['instance'] = instance
    snc_args['auth'] = (username, password)
    
    ret = ServiceNowClient(**snc_args)
    
    return ret

def get_new_snc(instance:str, creds:tuple = None, snc_args:dict = None, use_hihop:bool = False, use_sso:bool = True):
    """
    Creates a new ServiceNowClient for a given instance. This takes two optional arguments creds and snc_args. The
    snc_args is a dict of arguments that will be passed to ServiceNowClient constructor. If the dict does not contain
    the entry 'auth' then the method will attempt to login to the instance via selenium to create a new session. The
    optional creds argument is used during the session creation process to automate the login procedure. If no creds
    are given then the login procedure must be conducted manually. All options in snc_args will be passed directly to
    ServiceNowClient except 'cert' and 'instance', where 'cert' is deleted because it conflicts with 'auth' and 'instance'
    is overwritten with the instance string passed to this method. Note usage of pysnc requires a user to have the
    snc_platform_rest_api_access role.

    :param instance (str): A string representing a instance name or URL
    :param creds (tuple): A string pair containing the username and password for authentication (default=None)
    :param snc_args (dict): A dictionary of arguments to be passed to the ServiceNowClient constructor (default=None)
    :param use_hihop (bool): If True and a new session is created, the method will authenticate and access an instance through hihop (i.e. as a maint user) (default=False)
    :param use_sso (bool): If True then the login is treated as an sso login which allows hihop and requires different cookies. If False, then it assume basic auth but through selenium to allow for mfa. (default=True)
    :returns:
        - instance_client (ServiceNowClient): A new snc client object or None if an exception occurs
        - msg (str): A message indicating an exception occured or None
    """
    if snc_args is None:
        snc_args = {}

    if 'cert' in snc_args:
        del snc_args['cert']

    if 'instance' in snc_args:
        del snc_args['instance']

    snc_args['instance'] = instance

    if 'auth' not in snc_args:
        wanted_cookies = None
        liked_cookies = None
        start_url = None
        if use_sso:
            wanted_cookies = ['JSESSIONID','glide_user_route','glide_user_activity','glide_sso_id']
            liked_cookies = ['glide_session_store', 'BIGipServerpool_']
            if use_hihop:
                instance_name = get_instance_name(instance)
                start_url = f"https://hihop.service-now.com/hop.do?mode=readwrite&sysparm_instance={instance_name}"
        session, msg = get_new_session(instance, creds, wanted_cookies, liked_cookies, start_url=start_url)
        if msg is not None:
            return None, msg
        snc_args['auth'] = session

    ret = ServiceNowClient(**snc_args)

    return ret, None

class cookie_exists(object):
    def __init__(self, cookie_name):
        self.cookie_name = cookie_name

    def __call__(self, driver):
        for cookie in driver.get_cookies():
            if cookie['name'] == self.cookie_name:
                return True
        return False

class js_value_available:
    """Expected condition to check if a JavaScript value is truthy"""
    def __init__(self, script):
        self.script = script

    def __call__(self, driver):
        try:
            result = driver.execute_script(self.script)
            return result if result else False
        except:
            return False

def get_new_session(instance:str, creds:tuple = None, wanted_cookies:list[str] = None, liked_cookies:list[str] = None, login_targets:list[str] = None, options:Options = None, profile:FirefoxProfile = None, start_url = None):
    """
    Creates a new session that is logged into the given instance via selenium and cookie capture. If credentials are given
    it will attempt to automate the login process through either okta or basic auth. The type of authentication being used
    is detected automatically based on the format of the page that is loaded. If okta is being used it may still
    require manual input to get past 2-factor auth. If the login automation fails the user can still input required login
    information normally to obtain an active session. This method also accepts optional arguments to configure the firefox
    brower and profile used by selenium.

    :param instance (str): A string representing a instance name or URL
    :param creds (tuple): A string pair containing the username and password for authentication (default=None)
    :param wanted_cookies (list): A list of cookie names for cookies that need to be captured to indicate a session is authorized or None if using the default list
    :param liked_cookies (list): A list of cookie names for cookies that it would be nice to capture or None if using the default list
    :param login_targets (list): A list of login targets that when loaded indicate a successful login and end to the session capture process or None if using the default list
    :param options (Options): A selenium options object for Firefox (default=Options())
    :param profile (FirefoxProfile): A selenium FirefoxProfile (default=FirefoxProfile())
    :param start_url (str): A string URL representing the first webpage to load or None if using the url derived from the instance argument (default=None)
    :returns:
        - session (requests.Session): A active login session to the given instance or None on error
        - msg (str): A message indicating why the login session failed to be created or None on success
    """
    # These wanted/liked cookies are tuned towards and active gui session and do not work for pysnc
    # pysnc requires a subset of these cookies or auth fails (see get_new_snc)
    if wanted_cookies is None:
        wanted_cookies = ['JSESSIONID','glide_user_route','glide_user_activity']
    if liked_cookies is None:
        liked_cookies = ['glide_sso_id', 'glide_session_store', 'BIGipServerpool_']
    if login_targets is None:
        login_targets = ['/nav_to.do?', '/now/nav/ui/classic/params/target/home.do', '/now/nav/ui/classic/params/target/', '/now/nav/ui/home', '/now/bt1/home']
    driver = None
    instance_url = get_instance_url(instance)
    if start_url is None:
        start_url = instance_url
    try:
        session = requests.session()
        if options is None:
            options = Options()
        if profile is None:
            profile = FirefoxProfile()
        options.profile = profile
        driver = webdriver.Firefox(options=options)
        driver.switch_to.window(driver.current_window_handle)
        driver.get(start_url)

        ec_targets = []
        for target in login_targets:
            ec_targets.append(EC.url_contains(f"{instance_url}{target}"))

        # Add logout button as an additional success indicator
        ec_targets.append(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-id='logout']")))

        if creds is not None and type(creds) is tuple and len(creds) == 2:
            # If this fails you can always login manually still
            try:
                WebDriverWait(driver, 60*2).until(EC.any_of(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[aria-label='Select Okta FastPass.']")), # Okta verify exists and fastpass can be used
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[aria-label='Select Password.']")), # Okta verify exists but no fastpass
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[value='Next']")), # Okta verify does not exist
                    EC.element_to_be_clickable((By.ID, "sysverb_login")), # Basic auth
                    *ec_targets # Sometimes it just defaults to okta fastpass and logs you in before loading a page with any selectable options
                ))

                # ensure the page gets fully loaded
                time.sleep(2)

                okta_fastpass_button_test = driver.find_elements(By.CSS_SELECTOR, "[aria-label='Select Okta FastPass.']")
                okta_password_button_test = driver.find_elements(By.CSS_SELECTOR, "[aria-label='Select Password.']")
                next_button_test = driver.find_elements(By.CSS_SELECTOR, "[value='Next']")
                submit_button_test = driver.find_elements(By.ID, "sysverb_login")

                if len(okta_fastpass_button_test) > 0: # Username, password, and 2-factor provided by okta verify app
                    okta_fastpass_button_test[0].click()
                    # The rest is handled by okta verify on the desktop
                    print("Continue through Okta Verify on your desktop or phone...")
                elif len(okta_password_button_test) > 0: # Username provided by okta verify app
                    okta_password_button_test[0].click()
                    # Wait for password field to load
                    WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[value='Verify']")))
                    passw_field = driver.find_element(By.NAME, "credentials.passcode")
                    passw_field.send_keys(creds[1])
                    verify_button = driver.find_element(By.CSS_SELECTOR, "[value='Verify']")
                    verify_button.click()
                    # The rest is handled by okta verify on the desktop
                    print("Continue through Okta Verify on your desktop or phone...")
                elif len(next_button_test) > 0: # Okta standard login with no pre-populated data
                    # Fill in user name
                    user_field = driver.find_element(By.NAME, "identifier")
                    user_field.send_keys(creds[0])
                    next_button_test[0].click()
                    # Fill in password
                    WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[value='Verify']")))
                    passw_field = driver.find_element(By.NAME, "credentials.passcode")
                    passw_field.send_keys(creds[1])
                    verify_button = driver.find_element(By.CSS_SELECTOR, "[value='Verify']")
                    verify_button.click()
                    # Attempt to select a 2-factor auth method
                    try:
                        WebDriverWait(driver, 30).until(EC.any_of(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "[aria-label='Select to enter a code from the Okta Verify app.']")),
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "[aria-label='Select to get a push notification to the Okta Verify app.']")),
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "[aria-label='Select Okta FastPass.']"))
                        ))
                        okta_code_button_test = driver.find_elements(By.CSS_SELECTOR, "[aria-label='Select to enter a code from the Okta Verify app.']")
                        okta_push_button_test = driver.find_elements(By.CSS_SELECTOR, "[aria-label='Select to get a push notification to the Okta Verify app.']")
                        okta_fastpass_button_test = driver.find_elements(By.CSS_SELECTOR, "[aria-label='Select Okta FastPass.']")
                        if len(okta_fastpass_button_test) > 0:
                            okta_fastpass_button_test[0].click()
                        elif len(okta_push_button_test) > 0:
                            okta_push_button_test[0].click()
                        elif len(okta_code_button_test) > 0:
                            okta_code_button_test[0].click()
                    except TimeoutException as e:
                        print("Manual input on the desktop or browser may be required to continue...")
                    # At this point the instance should be logged in or some manual interaction is required for the 2-factor auth
                elif len(submit_button_test) > 0: # Direct instance login using basic auth
                    user_field = driver.find_element("id", "user_name")
                    user_field.send_keys(creds[0])
                    passw_field = driver.find_element("id", "user_password")
                    passw_field.send_keys(creds[1])
                    submit_button_test[0].click()
                    # Check if MFA is required after login
                    try:
                        WebDriverWait(driver, 10).until(EC.any_of(
                            EC.url_contains(f"{instance_url}/validate_multifactor_auth_code.do"),
                            *ec_targets  # Or we went straight to a login target
                        ))

                        # If MFA page is detected, wait for user to complete it
                        if "/validate_multifactor_auth_code.do" in driver.current_url:
                            print("MFA required, please complete multi-factor authentication in the browser window to continue...")
                    except TimeoutException as e:
                        pass
                    # Should be logged in at this point
            except Exception as e:
                print(f"Warning: Could not to automate logging into {instance_url} because of the following exception. The login can still be completed manually.\n\n{traceback.format_exc()}")

        # wait 2 minutes or until a known page appears
        # You may need to manually navigate to the URL after login
        WebDriverWait(driver, 60*2).until(EC.any_of(*ec_targets))

        # ensure the page gets fully loaded
        time.sleep(2)

        # wait on the cookies we want
        for want_cookie in wanted_cookies:
            WebDriverWait(driver, 10).until(cookie_exists(want_cookie))

        # Add the X-UserToken and User-Agent
        try:
            WebDriverWait(driver, 5).until(js_value_available("return navigator.userAgent;"))
            user_agent = driver.execute_script("return navigator.userAgent;")
            if user_agent:
                session.headers.update({'User-Agent': user_agent})
        except:
            pass

        x_user_token = None
        try:
            WebDriverWait(driver, 5).until(js_value_available("return window.g_ck;"))
            x_user_token = driver.execute_script("return window.g_ck;")
        except:
            pass

        if x_user_token is None:
            try:
                meta_tag = driver.find_element(By.CSS_SELECTOR, "meta[name='X-UserToken']")
                x_user_token = meta_tag.get_attribute("content")
            except:
                pass

        if x_user_token is None:
            try:
                hidden_input = driver.find_element(By.CSS_SELECTOR, "input[name='sysparm_ck']")
                x_user_token = hidden_input.get_attribute("value")
            except:
                pass

        if x_user_token:
            session.headers.update({'X-UserToken': x_user_token})

        # store all cookies wanted and liked
        for cookie in driver.get_cookies():
            if cookie['name'] in wanted_cookies or cookie['name'] in liked_cookies or (cookie['name'].startswith('BIGipServerpool_') and 'BIGipServerpool_' in liked_cookies):
                session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'], path=cookie['path'])

        return session, None
    except Exception as e:
        return None, f"Unexpected error when logging into {instance_url}.\n\n{traceback.format_exc()}"
    finally:
        if driver is not None:
            driver.quit()
