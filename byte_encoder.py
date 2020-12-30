import json

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (bytes, bytearray)):
            try:
                return obj.decode('raw_unicode_escape') # <- or any other encoding of your choice
            except:
                print("err")
                return str(obj)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)