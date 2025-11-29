from dataclasses import dataclass, asdict
from typing import Union, List, Any, Dict
import json

@dataclass
class Item:
    descripcion: str
    cantidad: int
    precio: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Item":
        return cls(
            descripcion=str(data.get("descripcion", "")),
            cantidad=int(data.get("cantidad", 0)),
            precio=float(data.get("precio", 0.0)),
        )

    @classmethod
    def from_json(cls, payload: Union[str, bytes]) -> "Item":
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode()
        data = json.loads(payload)
        return cls.from_dict(data)

def items_from_json(payload: Union[str, bytes]) -> List[Item]:
    """
    Deserializa un objeto JSON o una lista JSON de objetos Item.
    - Si el JSON es un objeto, devuelve una lista con un Item.
    - Si es una lista, devuelve la lista de Item.
    """
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode()
    data = json.loads(payload)
    if isinstance(data, list):
        return [Item.from_dict(d) for d in data]
    if isinstance(data, dict):
        return [Item.from_dict(data)]
    raise ValueError("JSON must be an object or array of objects")