class FilterException(Exception):
    def __init__(self):
        super().__init__("Current content triggered filter exception.")
