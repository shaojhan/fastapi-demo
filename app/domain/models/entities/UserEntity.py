from ..object_values.UserRole import UserRole

class EmailAdress():
    email: str

class HashedPassword():
    pwd: str

class User:
    def __init__(self, uid: str, password: str, name: str, age: int, email:str, role: UserRole):
        self.uid = uid
        self.pwd_hash = password
        self.name = name
        self.age = age
        self.email = email
        self.role = role

    def create_user(self):
        pass

    def hash_password(self, pwd: HashedPassword):
        pass
    
    def update_password(self):
        pass


