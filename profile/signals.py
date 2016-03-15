from djangosaml2.signals import pre_user_save


def custom_update_user(sender, **kwargs):
    print sender
    print kwargs

    return True

pre_user_save.connect(custom_update_user)
