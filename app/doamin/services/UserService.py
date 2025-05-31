from app.doamin.models.entities.UserEntity import User, HashedPassword, EmailAdress, UserRegistrationInput

def create_user(user: UserRegistrationInput):
    email_vo = EmailAdress(user.email)
    password_vo = HashedPassword(user.password)
    return User(user.uid, email_vo, password_vo)
