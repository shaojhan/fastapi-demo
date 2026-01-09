import bcrypt

class PasswordHasher():
    def hash(self, raw_password: str) -> str:
        pass
    def verify(self, raw_password: str) -> str:
        pass

class BcryptHasher(PasswordHasher):
    def hash(self, raw_password: str) -> str:
        return bcrypt.hashpw(raw_password.encode(), bcrypt.gensalt().decode())
    def verify(self):
        return