from dataclasses import dataclass, asdict
from typing import Union, List, Any, Dict
import json

@dataclass
class Item:
    description: str
    quantity: int
    price: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Item":
        return cls(
            description=str(data.get("description", "")),
            quantity=int(data.get("quantity", 0)),
            price=float(data.get("price", 0.0)),
        )

    @classmethod
    def from_json(cls, payload: Union[str, bytes]) -> "Item":
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode()
        data = json.loads(payload)
        return cls.from_dict(data)

def items_from_json(payload: Union[str, bytes]) -> List[Item]:
    """
    Deserialize a JSON object or a list of JSON objects into Item instances.
    - If JSON is an object, returns a list with one Item.
    - If JSON is a list, returns the list of Items.
    """
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode()
    data = json.loads(payload)
    if isinstance(data, list):
        return [Item.from_dict(d) for d in data]
    if isinstance(data, dict):
        return [Item.from_dict(data)]
    raise ValueError("JSON must be an object or array of objects")