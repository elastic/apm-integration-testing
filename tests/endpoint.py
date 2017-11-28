class Endpoint:
    def __init__(self, base_url, endpoint, qu_str="q=1", text=None, status_code=200):
        self.url = "{}/{}".format(base_url, endpoint)
        if qu_str is not None and qu_str != "":
            self.url = "{}?{}".format(self.url, qu_str)
        self.text = text if text is not None else endpoint
        self.status_code = status_code
