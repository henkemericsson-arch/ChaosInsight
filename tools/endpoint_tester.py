import requests

from config.atg import BASE_URL, HEADERS


ENDPOINTS = [

    "/calendar/day/2026-08-22",

    "/games",

    "/game",

    "/products",

    "/product",

    "/races",

    "/race",

    "/v85",

    "/v65",

    "/v75",

    "/v64",

    "/v5",

    "/v4",

    "/v3",

    "/dd",

    "/ld",

]


print("=" * 70)
print("ATG ENDPOINT TESTER")
print("=" * 70)

for endpoint in ENDPOINTS:

    url = BASE_URL + endpoint

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        print()
        print(endpoint)
        print("Status:", response.status_code)

        try:
            data = response.json()

            if isinstance(data, dict):
                print("Nycklar:", list(data.keys())[:10])

            elif isinstance(data, list):
                print("Lista:", len(data))

        except Exception:
            print("Ej JSON")

    except Exception as e:

        print(endpoint)
        print(e)