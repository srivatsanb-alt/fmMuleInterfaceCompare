
import dataclasses
import json


class JsonMixin:
    @classmethod
    def from_dict(cls, obj_dict):
        fields = [f.name for f in dataclasses.fields(cls)]
        attribs = {k: v for (k, v) in obj_dict.items() if k in fields}
        return cls(**attribs)

    @classmethod
    def from_json(cls, obj_json):
        return cls.from_dict(json.loads(obj_json))

    def to_json(self):
        return json.dumps(dataclasses.asdict(self))