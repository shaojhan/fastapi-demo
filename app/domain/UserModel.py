from dataclasses import dataclass

@dataclass(frozen=True)
class Name:
    first_name: str
    sur_name: str

@dataclass
class Session:
    uuid: str

@dataclass
class HashedPassword:
    password: str

class UserModel:
    def __init__(self):
        self.name = Name()