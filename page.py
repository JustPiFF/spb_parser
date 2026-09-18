import requests

class PageAPI:
    def __init__(self, config):
        self.url = "https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/1222/specialties"
        self.use_proxy = config.get("use_proxy", False)

        if self.use_proxy:
            self.proxy = {
                "http": f"http://{config['proxy_user']}:{config['proxy_password']}@{config['proxy']}",
                "https": f"http://{config['proxy_user']}:{config['proxy_password']}@{config['proxy']}"
            }
        else:
            self.proxy = None

    def fetch_data(self):
        """Возвращает JSON со списком специальностей или None при ошибке."""
        try:
            response = requests.get(self.url, proxies=self.proxy, timeout=10)
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка запроса: {e}")
        return None
