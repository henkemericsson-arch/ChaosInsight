import requests


class HttpClient:

    def get(self, url, headers=None, params=None):

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def get_text(self, url, headers=None, params=None):

        #
        # Anvands for kallor som inte returnerar JSON,
        # t.ex. HTML-sidor som ska skrapas.
        #

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        return response.text
