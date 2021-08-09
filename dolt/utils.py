def author_from_user(usr):
    if usr and usr.username and usr.email:
        return f"{usr.username} <{usr.email}>"
    # default to generic user
    return "nautobot <nautobot@ntc.com>"
